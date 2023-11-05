import pathlib
import os
import re
import time
import fnmatch

import sounddevice as sd
import soundfile as sf

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtGui import (
    QColor,
)

from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QSplitter,
    QLabel,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from aipacenotes.concurrency import TaskManager, TimerThread
from aipacenotes import client as aip_client
from .pacenotes_table import NotebookTable, NotebookTableModel
from .pacenotes_tree_widget import PacenotesTreeWidget
from .rally_file import Notebook, NotebookFile
from .rally_file_scanner import SearchPath
from .update_jobs import UpdateJobsStore, UpdateJob
from .update_jobs_table import UpdateJobsTable, UpdateJobsTableModel

# class Benchmark:
#     def __init__(self):
#         self.start_time = time.time()

#     def stop(self, message):
#         elapsed_time = time.time() - self.start_time
#         ms = int(elapsed_time * 1000)
#         print(f"{message}: {ms}ms")

class PacenotesTabWidget(QWidget):
    
    pacenote_updated = pyqtSignal()
    job_run_finished = pyqtSignal(UpdateJob)

    def __init__(self, settings_manager):
        super().__init__()

        self.settings_manager = settings_manager

        self.controls_pane = QWidget()
        stylesheet = """
        QWidget#ControlsPane {
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        self.controls_pane.setObjectName('ControlsPane')
        self.controls_pane.setFixedHeight(1)
        self.controls_layout = QHBoxLayout()
        self.controls_pane.setLayout(self.controls_layout)

        self.controls_label = QLabel("", self.controls_pane)
        self.controls_layout.addWidget(self.controls_label)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.task_manager = TaskManager(10)
        self.timer_thread = TimerThread(5)
        self.timer_thread.timeout.connect(self.on_timer_timeout)

        self.job_run_finished.connect(self.on_job_run_finished)

        self.tree = PacenotesTreeWidget(self.settings_manager)
        self.tree.notebookSelectionChanged.connect(self.on_tree_notebook_selection_changed)

        self.splitter.addWidget(self.tree)

        self.notebook_table = NotebookTable()

        self.notebook_table_model = NotebookTableModel()
        self.notebook_table.setModel(self.notebook_table_model)
        self.notebook_table.setColumnWidth(0, 50)
        self.notebook_table.setColumnWidth(1, 400)
        self.notebook_table.setColumnWidth(2, 150)
        self.notebook_table.setColumnWidth(3, 150)
        self.notebook_table.setColumnWidth(4, 250)
        self.notebook_table.play_clicked.connect(self.play_audio)

        self.table_controls = QWidget()
        table_controls_layout = QHBoxLayout(self.table_controls)
        self.table_controls.setFixedHeight(50)

        self.btn_refresh_notebook = QPushButton("Refresh")
        self.btn_refresh_notebook.setFixedWidth(50)
        self.btn_refresh_notebook.clicked.connect(self.on_btn_refresh_notebook_pressed)
        table_controls_layout.addWidget(self.btn_refresh_notebook)
        table_controls_layout.setAlignment(self.btn_refresh_notebook, Qt.AlignmentFlag.AlignLeft)

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.addWidget(self.table_controls)
        right_layout.addWidget(self.notebook_table)
        self.splitter.addWidget(right_pane)

        self.update_jobs_store = UpdateJobsStore(self.settings_manager)

        self.jobs_model = UpdateJobsTableModel(self.update_jobs_store)
        jobs_table = UpdateJobsTable()
        jobs_table.setModel(self.jobs_model)
        jobs_table.setColumnWidth(0, 70)
        jobs_table.setColumnWidth(1, 70)
        jobs_table.setColumnWidth(2, 400)
        jobs_table.setColumnWidth(3, 250)
        jobs_table.setColumnWidth(4, 150)
        jobs_table.setColumnWidth(5, 150)

        self.splitter_v = QSplitter(Qt.Orientation.Vertical)
        self.splitter_v.addWidget(self.splitter)
        self.splitter_v.addWidget(jobs_table)

        vbox = QVBoxLayout()
        vbox.addWidget(self.controls_pane)
        vbox.addWidget(self.splitter_v)
        self.setLayout(vbox)

        splitter_width = self.splitter.width()
        splitter_left_width = int(splitter_width / 4) + 10
        splitter_right_width = splitter_width - splitter_left_width
        self.splitter.setSizes([splitter_left_width, splitter_right_width])

        self.tree.populate()
        # self.tree.select_default()
        self.timer_thread.start()
    
    def on_tree_notebook_selection_changed(self, notebook_file):
        self.notebook_table_model.setNotebookFile(notebook_file)
        self.notebook_table_model.layoutChanged.emit()

    def play_audio(self, row):
        def _play(fname):
            self.settings_manager.update_status_left(f"played {fname}")
            data, samplerate = sf.read(fname)
            sd.play(data, samplerate)
            sd.wait()

        notebook_file = self.notebook_table_model.notebook_file
        notebook = notebook_file.notebook()
        if notebook:
            pacenote = notebook.pacenotes()[row]
            if pacenote.note_file_exists():
                self.task_manager.submit(_play, pacenote.note_abs_path())

    def on_btn_refresh_notebook_pressed(self):
        def _special_button_refresh():
            self.tree.clear()
            self.tree.populate()
            self.refresh_pacenotes()
        self.task_manager.submit(_special_button_refresh)
    
    def refresh_pacenotes(self):
        notebook_file = self.notebook_table_model.notebook_file
        if not notebook_file:
            return

        notebook_file.load()
        notebook = notebook_file.notebook()
        
        for pacenote in notebook.pacenotes():
            if pacenote.needs_update():
                job = self.update_jobs_store.add_job(pacenote)
                self.jobs_model.layoutChanged.emit()

                def _run_job(job):
                    job.run(self.job_run_finished)

                if job:
                    self.task_manager.submit(_run_job, job)
        
        self.update_jobs_store.update_job_time_agos()
        self.update_jobs_store.prune()
        self.jobs_model.layoutChanged.emit()
        self.notebook_table_model.setNotebookFile(notebook_file)
        self.notebook_table_model.layoutChanged.emit()
        self.task_manager.gc_finished()

    def on_job_run_finished(self, job):
        self.jobs_model.layoutChanged.emit()
        self.notebook_table_model.layoutChanged.emit()

    def on_timer_timeout(self):
        # pass
        self.task_manager.submit(self.refresh_pacenotes)





    
    # def update_pacenotes_info_label(self):
    #     self.pacenotes_info_label.setText(f"""
    #     Updating pacenotes: {self.task_manager.get_future_count()}
    #     """)
    
    # def set_controls_label_enabled_message(self):
    #     self.controls_label.setText(f"Pacenotes are being updated every {self.timeout_ms / 1000} seconds.")
    
    # def set_controls_label_disabled_message(self):
    #     self.controls_label.setText("Pacenotes are not being updated.")
    
    # def set_controls_label_hc_failed_message(self):
    #     self.controls_label.setText("Healthcheck failed. Disabled auto-update.")
    
    # def set_controls_label_startup_healthcheck_message(self):
    #     self.controls_label.setText("Connecting to pacenotes server. May take about 10 seconds if the server has to boot up.")

    # def on_toggle(self, checked):
    #     if checked:
    #         self.is_toggled = True
    #         self.set_controls_label_enabled_message()
    #         self.on_off_button.setText("On")

    #         # only re-load settings when enabling the timer, not every cycle.
    #         self.settings_manager.load()

    #         self.on_timer_timeout()
    #         # self.timer_thread.enable()

    #         # self.on_off_button.setStyleSheet("""
    #         # QPushButton { background-color: green; }
    #         # QPushButton:pressed { background-color: green; }
    #         # QPushButton:checked { background-color: green; }
    #         # QPushButton:disabled { background-color: green; }
    #         # """)

    #     else:
    #         self.is_toggled = True
    #         self.set_controls_label_disabled_message()
    #         self.on_off_button.setText("Off")
    #         # self.timer_thread.disable()
    #         # self.on_off_button.setStyleSheet("background-color: red;")
    
    # def on_timer_timeout(self):
    #     # print(f"-- on_timer_timeout ------------------------------")
    #     # TODO call the healthcheck in a background thread.
    #     # if not aip_client.get_healthcheck_rate_limited():
    #         # raise RuntimeError("healthcheck error")
    #     # self.set_controls_label_enabled_message()
    #     self.populate_tree()

    #     files, rally_files = self.get_selected_pacenotes_files()
    #     self.pacenotes_manager.scan_pacenotes_files(files, rally_files)
    #     files += rally_files

    #     filtered_pacenotes = self.get_filtered_pacenotes(files)
    #     # filtered_rally = self.get_filtered_pacenotes(rally_files)

    #     sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)
    #     # sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)

    #     self.update_table(sorted_pacenotes)
    #     if self.is_toggled:
    #         self.update_pacenotes_audio(filtered_pacenotes)

    #     self.pacenotes_manager.clean_up_orphaned_audio()

    # def on_healthcheck_started(self):
    #     # print('healthcheck_started')
    #     pass

    # def on_healthcheck_passed(self):
    #     # print('healthcheck_passed')
    #     pass

    # def on_healthcheck_failed(self):
    #     print('healthcheck_failed')
    #     self.set_controls_label_startup_healthcheck_message()
    #     self.on_off_button.setChecked(False)
    
    # def get_filtered_pacenotes(self, pacenotes_files_filter):
    #     return [d for d in self.pacenotes_manager.db.pacenotes if d.pacenotes_fname in pacenotes_files_filter]

    # def get_filtered_rally(self, rally_files_filter):
    #     return [d for d in self.pacenotes_manager.db.pacenotes if d.pacenotes_fname in rally_files_filter]
    
    # def sorted_pacenotes_for_table(self, pacenotes):
    #     def sort_fn(pacenote):
    #         st = pacenote.status
    #         status_n = -1
    #         if st == statuses.PN_STATUS_ERROR:
    #             status_n = 0
    #         if st == statuses.PN_STATUS_UNKNOWN:
    #             status_n = 1
    #         elif st == statuses.PN_STATUS_UPDATING:
    #             status_n = 2
    #         elif st == statuses.PN_STATUS_NEEDS_SYNC:
    #             status_n = 3
    #         elif st == statuses.PN_STATUS_OK:
    #             status_n = 4
    #         else:
    #             status_n = 5

    #         return (status_n, -pacenote.updated_at)

    #     return sorted(pacenotes, key=sort_fn)
    
    # If anything is selected in the tree, only include those pacenotes files.
    # def get_selected_pacenotes_files(self):
    #     # return ['C:\\Users\\bird\\AppData\\Local\\BeamNG.drive\\0.29\\gameplay\\missions\\jungle_rock_island\\timeTrial\\jri_road_race-procedural\\pacenotes.pacenotes.json']
    #     # return ['C:\\Users\\bird\\AppData\\Local\\BeamNG.drive\\0.29\\gameplay\\missions\\jungle_rock_island\\timeTrial\\aip-island-loop\\pacenotes.pacenotes.json']
    #     selected_items = self.tree.selectedItems()
    #     selected_item_path = None

    #     search_paths = []

    #     if len(selected_items) > 1:
    #         print(f"tree widget multi-select is not supported yet")
    #     elif len(selected_items) == 1:
    #         selected_item_path = selected_items[0].full_path
    #         search_paths.append(selected_item_path)
    #     else:
    #         search_paths = self.settings_manager.get_pacenotes_search_paths()

    #     pacenotes_files = []
    #     rally_files = []
    #     for search_path in search_paths:
    #         if os.path.isfile(search_path):
    #             if fnmatch.fnmatch(search_path, pacenotes_file_pattern):
    #                 pacenotes_files.append(search_path)
    #             elif fnmatch.fnmatch(search_path, rally_file_pattern):
    #                 rally_files.append(search_path)
    #         else:
    #             paths = pathlib.Path(search_path).rglob(pacenotes_file_pattern)
    #             for e in paths:
    #                 pacenotes_files.append(str(e))

    #             paths = pathlib.Path(search_path).rglob(rally_file_pattern)
    #             for e in paths:
    #                 rally_files.append(str(e))
        
    #     return pacenotes_files, rally_files


    # def update_pacenotes_audio(self, pacenotes):
    #     def submit_for_update(pn):
    #         pn.network_status = statuses.PN_STATUS_UPDATING
    #         pn.touch()
    #         self.task_manager.submit(self.update_pacenote, pn.id)

    #     for pn in pacenotes:
    #         if pn.status == statuses.PN_STATUS_NEEDS_SYNC:
    #             print(f"submitting for update: pacenote '{pn.note_text}' is in NEEDS_SYNC")
    #             submit_for_update(pn)
    #         elif pn.dirty:
    #             print(f"submitting for update: pacenote '{pn.note_text}' is dirty")
    #             submit_for_update(pn)

    # def update_pacenote(self, pnid):
    #     pacenote = self.pacenotes_manager.db.select(pnid)
    #     print(f"update_pacenote '{pacenote.note_text}'")

    #     response = aip_client.post_create_pacenotes_audio(pacenote)

    #     if response.status_code == 200:
    #         audio_path = pacenote.audio_path

    #         version_path = os.path.dirname(audio_path)
    #         if not os.path.exists(version_path):
    #             pacenotes_path = os.path.dirname(version_path)
    #             if not os.path.exists(pacenotes_path):
    #                 os.mkdir(pacenotes_path)
    #             os.mkdir(version_path)

    #         with open(audio_path, 'wb') as f:
    #             f.write(response.content)

    #         pacenote.clear_dirty()
    #         pacenote.touch()
    #         pacenote.network_status = None
    #         pacenote.filesystem_status = statuses.PN_STATUS_OK
    #         print(f"wrote audio file for '{pacenote.note_text}': {audio_path}")
    #     else:
    #         pacenote.clear_dirty()
    #         pacenote.touch()
    #         pacenote.network_status = statuses.PN_STATUS_ERROR
    #         print(f"request failed with status code {response.status_code}")

    #     res = f"pacenote updated '{pacenote.note_text}'"
    #     print(res)

    #     self.pacenote_updated.emit()
    #     return res
    
    # def on_pacenote_updated(self):
    #     # print("on_pacenote_updated:", threading.current_thread().name)
    #     print('pacenote updated!!!')
    #     self.task_manager.gc_finished()
    #     self.update_pacenotes_info_label()

    #     pacenotes_files, rally_files = self.get_selected_pacenotes_files()

    #     filtered_pacenotes = self.get_filtered_pacenotes(pacenotes_files)
    #     sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)

    #     # filtered_rally = self.get_filtered_rally(files)

    #     self.update_table(sorted_pacenotes)
    
    # def update_table(self, data):
    #     self.notebook_table.setRowCount(0)
        
    #     for i, pacenote in enumerate(data):
    #         (status, updated_at, note, voice, audio, name, version, versionId, mission, location) = self.to_table_row(pacenote)
    #         self.notebook_table.insertRow(i)

    #         status_item = QTableWidgetItem(status)
    #         if status == statuses.PN_STATUS_ERROR:
    #             status_item.setBackground(QColor(255, 0, 0))
    #         elif status == statuses.PN_STATUS_UPDATING:
    #             status_item.setBackground(QColor(255, 255, 0))
    #         elif status == statuses.PN_STATUS_NEEDS_SYNC:
    #             status_item.setBackground(QColor(0, 255, 255))
    #         elif status == statuses.PN_STATUS_OK:
    #             status_item.setBackground(QColor(0, 255, 0))
    #         self.notebook_table.setItem(i, 0, status_item)

    #         font = status_item.font()
    #         font.setBold(True)
    #         status_item.setFont(font)
    #         status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    #         updated_at = time.time() - updated_at
    #         updated_at = int(updated_at)
    #         updated_at = f"{updated_at}s ago"
    #         item = QTableWidgetItem(updated_at)
    #         # item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
    #         self.notebook_table.setItem(i, 1, item)

    #         self.notebook_table.setItem(i, 2, QTableWidgetItem(note))
    #         self.notebook_table.setItem(i, 3, QTableWidgetItem(voice))
    #         self.notebook_table.setItem(i, 4, QTableWidgetItem(audio))
    #         self.notebook_table.setItem(i, 5, QTableWidgetItem(name))
    #         self.notebook_table.setItem(i, 6, QTableWidgetItem(version))
    #         self.notebook_table.setItem(i, 7, QTableWidgetItem(versionId))
    #         self.notebook_table.setItem(i, 8, QTableWidgetItem(mission))
    #         self.notebook_table.setItem(i, 9, QTableWidgetItem(location))

    #     # self.table.resizeColumnsToContents()

    # def to_table_row(self, pacenote):
    #     row_fields = ['status', 'updated_at', 'note_text', 'voice', 'audio_fname',
    #                   'note_name', 'version_name', 'version_id',
    #                   'mission_id', 'mission_location']
    #     row_data = [pacenote.get_data(f) for f in row_fields]
    #     return row_data
    
    # def populate_tree(self):
    #     bench = Benchmark()
    #     selected_items = self.tree.selectedItems()
    #     selected_item_path = None

    #     if len(selected_items) > 1:
    #         print(f"tree widget multi-select is not supported yet")
    #     elif len(selected_items) == 1:
    #         selected_item_path = selected_items[0].full_path
        
    #     # print(f"tree selected_item_path={selected_item_path}")

    #     self.tree.clear()

    #     def shorten_root_path(input_string):
    #         pattern = r".*\\(BeamNG\.drive)"
    #         match = re.search(pattern, input_string)
    #         if match:
    #             last_component = match.group(1)
    #             return re.sub(pattern, last_component, input_string)
    #         return input_string

    #     idx = {}

    #     for root_path in self.settings_manager.get_pacenotes_search_paths():
    #         # print(f"populating tree for {root_path}")
    #         root_item_name = shorten_root_path(root_path)
    #         root_item = PacenotesTreeWidgetItem(self.tree, [root_item_name], root_path)
    #         idx[root_path] = root_item
    #         search_path = pathlib.Path(root_path)
    #         paths = search_path.rglob(pacenotes_file_pattern)
    #         rally_paths = search_path.rglob(rally_file_pattern)
    #         paths = itertools.chain(paths, rally_paths)
    #         # pacenotes_files = []
    #         # rally_files = []
    #         for e in paths:
    #             # print(e)
    #             # pacenotes_files.append(str(e))
    #             rel_path = e.relative_to(root_path)
    #             parts = pathlib.PurePath(rel_path).parts
    #             dir_parts = parts[:-1]
    #             file_part = parts[-1]
    #             parent_node = self.get_nested_node(idx, root_path, dir_parts)
    #             full_path = os.path.join(root_path, rel_path)
    #             file_node = PacenotesTreeWidgetItem(parent_node, [file_part], full_path)
    #             idx[full_path] = file_node

    #     self.tree.expandAll()

    #     if selected_item_path is not None:
    #         selected_item = idx[selected_item_path]
    #         if selected_item is not None:
    #             selected_item.setSelected(True)

        # bench.stop('populate_tree')
  
    # def get_nested_node(self, idx, root_path, names):
    #     node = self.get_node(idx, None, root_path, root_path)
    #     names_so_far = []
    #     for name in names:
    #         names_so_far.append(name)
    #         idx_key = self.make_idx_key(root_path, names_so_far)
    #         parent_key = self.make_idx_key(root_path, names_so_far[:-1])
    #         if parent_key is None:
    #             parent_key = root_path
    #         node = self.get_node(idx, parent_key, name, idx_key)
    #         parent_key = idx_key
    #     return node
    
    # def make_idx_key(self, root_path, names):
    #     if len(names) > 0:
    #         return os.path.join(root_path, *names)
    #     else:
    #         return None
    
    # def get_node(self, idx, parent_key, name, idx_key):
    #     if idx_key in idx:
    #         return idx[idx_key]
    #     elif parent_key is not None:
    #         idx[idx_key] = PacenotesTreeWidgetItem(idx[parent_key], [name], idx_key)
    #         return idx[idx_key]
    #     else:
    #         raise ValueError("parent_key is None")