import pathlib
import os
import re
import time
import fnmatch
import itertools

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtGui import (
    # QAction,
    # QKeySequence,
    QColor,
)

from PyQt6.QtWidgets import (
    # QMainWindow,
    # QTabWidget,
    QTableWidget,
    QPushButton,
    QSplitter,
    QLabel,
    QHeaderView,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

# from aipacenotes.tab_pacenotes import (
from . import (
    ContextMenuTreeWidget,
    TimerThread,
    HealthcheckThread,
    TaskManager,
    PacenotesManager,
    PacenotesTreeWidgetItem,
)

# from aipacenotes.tab_pacenotes import (
from . import (
    statuses,
    # Pacenote,
)
from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager

import time

pacenotes_file_pattern = '*.pacenotes.json'
rally_file_pattern = '*.rally.json'

class Benchmark:
    def __init__(self):
        self.start_time = time.time()

    def stop(self, message):
        elapsed_time = time.time() - self.start_time
        ms = int(elapsed_time * 1000)
        print(f"{message}: {ms}ms")

# class MainWindow(QMainWindow):

class PacenotesTabWidget(QWidget):
    
    pacenote_updated = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()

        self.controls_pane = QWidget()
        stylesheet = """
        QWidget#ControlsPane {
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        self.controls_pane.setStyleSheet(stylesheet)
        self.controls_pane.setObjectName('ControlsPane')
        self.controls_pane.setFixedHeight(75)
        self.controls_layout = QHBoxLayout()
        self.controls_pane.setLayout(self.controls_layout)

        self.on_off_button = QPushButton()
        self.on_off_button.setCheckable(True)
        self.on_off_button.setChecked(True)
        self.on_off_button.setFixedHeight(50)
        self.on_off_button.setFixedWidth(50)
        self.on_off_button.toggled.connect(self.on_toggle)
        self.controls_layout.addWidget(self.on_off_button)

        self.controls_label = QLabel("", self.controls_pane)
        self.controls_layout.addWidget(self.controls_label)

        # Create a splitter to divide the tab into two panes
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Add a QTreeWidget to the left pane
        self.tree = ContextMenuTreeWidget()
        self.tree.setFixedWidth(500)
        self.tree.setHeaderLabel("Pacenotes Files")
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.splitter.addWidget(self.tree)

        # Add a blank widget to the right pane
        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout(self.right_pane)
        self.splitter.addWidget(self.right_pane)

        self.pacenotes_info_label = QLabel("This is a label\nFoobar", self.right_pane)
        self.right_layout.addWidget(self.pacenotes_info_label)

        self.table = QTableWidget(0, 10)  
        self.table.setHorizontalHeaderLabels(['Status', 'Updated At', 'Pacenote', 'Voice', 'Audio File', 'Pacenote Name', 'Version Name', 'Version ID', 'Mission ID', 'Location']) 
        # Set table header to stretch to the size of the window

        header = self.table.horizontalHeader()       
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        stylesheet = """
        QHeaderView::section::horizontal{
            Background-color:rgb(240,240,240);
            border-radius:14px;
            border-right: 1px solid rgb(130, 136, 144);
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        header.setStyleSheet(stylesheet)

        self.table.setColumnWidth(0, 75)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)
        self.right_layout.addWidget(self.table)

        # Create a widget for the first tab
        # self.tab_contents = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(self.controls_pane)
        vbox.addWidget(self.splitter)
        self.setLayout(vbox)

        self.timeout_ms = 1000
        self.timeout_sec = self.timeout_ms / 1000

        self.healthcheck_thread = HealthcheckThread(60)
        self.healthcheck_thread.healthcheck_started.connect(self.on_healthcheck_started)
        self.healthcheck_thread.healthcheck_passed.connect(self.on_healthcheck_passed)
        self.healthcheck_thread.healthcheck_failed.connect(self.on_healthcheck_failed)
        self.healthcheck_thread.start()
        self.set_controls_label_startup_healthcheck_message()

        self.timer_thread = TimerThread(self.timeout_sec)
        self.timer_thread.timeout.connect(self.on_timer_timeout)
        self.timer_thread.start()

        self.task_manager = TaskManager(10)
        self.update_pacenotes_info_label()

        self.settings_manager = settings_manager
        self.pacenotes_manager = PacenotesManager(self.settings_manager)

        self.pacenote_updated.connect(self.on_pacenote_updated)

        self.is_toggled = True
        self.on_toggle(True)
    
    def update_pacenotes_info_label(self):
        self.pacenotes_info_label.setText(f"""
        Updating pacenotes: {self.task_manager.get_future_count()}
        """)
    
    def set_controls_label_enabled_message(self):
        self.controls_label.setText(f"Pacenotes are being updated every {self.timeout_ms / 1000} seconds.")
    
    def set_controls_label_disabled_message(self):
        self.controls_label.setText("Pacenotes are not being updated.")
    
    def set_controls_label_hc_failed_message(self):
        self.controls_label.setText("Healthcheck failed. Disabled auto-update.")
    
    def set_controls_label_startup_healthcheck_message(self):
        self.controls_label.setText("Connecting to pacenotes server. May take about 10 seconds if the server has to boot up.")

    def on_toggle(self, checked):
        if checked:
            self.is_toggled = True
            self.set_controls_label_enabled_message()
            self.on_off_button.setText("On")

            # only re-load settings when enabling the timer, not every cycle.
            self.settings_manager.load()

            self.on_timer_timeout()
            # self.timer_thread.enable()

            # self.on_off_button.setStyleSheet("""
            # QPushButton { background-color: green; }
            # QPushButton:pressed { background-color: green; }
            # QPushButton:checked { background-color: green; }
            # QPushButton:disabled { background-color: green; }
            # """)

        else:
            self.is_toggled = True
            self.set_controls_label_disabled_message()
            self.on_off_button.setText("Off")
            # self.timer_thread.disable()
            # self.on_off_button.setStyleSheet("background-color: red;")
    
    def on_timer_timeout(self):
        # print(f"-- on_timer_timeout ------------------------------")
        # TODO call the healthcheck in a background thread.
        # if not aip_client.get_healthcheck_rate_limited():
            # raise RuntimeError("healthcheck error")
        # self.set_controls_label_enabled_message()
        self.populate_tree()

        files, rally_files = self.get_selected_pacenotes_files()
        self.pacenotes_manager.scan_pacenotes_files(files, rally_files)
        files += rally_files

        filtered_pacenotes = self.get_filtered_pacenotes(files)
        # filtered_rally = self.get_filtered_pacenotes(rally_files)

        sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)
        # sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)

        self.update_table(sorted_pacenotes)
        if self.is_toggled:
            self.update_pacenotes_audio(filtered_pacenotes)

        self.pacenotes_manager.clean_up_orphaned_audio()

    def on_healthcheck_started(self):
        # print('healthcheck_started')
        pass

    def on_healthcheck_passed(self):
        print('healthcheck_passed')

    def on_healthcheck_failed(self):
        print('healthcheck_failed')
        self.set_controls_label_startup_healthcheck_message()
        self.on_off_button.setChecked(False)
    
    def get_filtered_pacenotes(self, pacenotes_files_filter):
        return [d for d in self.pacenotes_manager.db.pacenotes if d.pacenotes_fname in pacenotes_files_filter]

    # def get_filtered_rally(self, rally_files_filter):
    #     return [d for d in self.pacenotes_manager.db.pacenotes if d.pacenotes_fname in rally_files_filter]
    
    def sorted_pacenotes_for_table(self, pacenotes):
        def sort_fn(pacenote):
            st = pacenote.status
            status_n = -1
            if st == statuses.PN_STATUS_ERROR:
                status_n = 0
            if st == statuses.PN_STATUS_UNKNOWN:
                status_n = 1
            elif st == statuses.PN_STATUS_UPDATING:
                status_n = 2
            elif st == statuses.PN_STATUS_NEEDS_SYNC:
                status_n = 3
            elif st == statuses.PN_STATUS_OK:
                status_n = 4
            else:
                status_n = 5

            return (status_n, -pacenote.updated_at)

        return sorted(pacenotes, key=sort_fn)
    
    # If anything is selected in the tree, only include those pacenotes files.
    def get_selected_pacenotes_files(self):
        # return ['C:\\Users\\bird\\AppData\\Local\\BeamNG.drive\\0.29\\gameplay\\missions\\jungle_rock_island\\timeTrial\\jri_road_race-procedural\\pacenotes.pacenotes.json']
        # return ['C:\\Users\\bird\\AppData\\Local\\BeamNG.drive\\0.29\\gameplay\\missions\\jungle_rock_island\\timeTrial\\aip-island-loop\\pacenotes.pacenotes.json']
        selected_items = self.tree.selectedItems()
        selected_item_path = None

        search_paths = []

        if len(selected_items) > 1:
            print(f"tree widget multi-select is not supported yet")
        elif len(selected_items) == 1:
            selected_item_path = selected_items[0].full_path
            search_paths.append(selected_item_path)
        else:
            search_paths = self.settings_manager.get_search_paths()

        pacenotes_files = []
        rally_files = []
        for search_path in search_paths:
            if os.path.isfile(search_path):
                if fnmatch.fnmatch(search_path, pacenotes_file_pattern):
                    pacenotes_files.append(search_path)
                elif fnmatch.fnmatch(search_path, rally_file_pattern):
                    rally_files.append(search_path)
            else:
                paths = pathlib.Path(search_path).rglob(pacenotes_file_pattern)
                for e in paths:
                    pacenotes_files.append(str(e))

                paths = pathlib.Path(search_path).rglob(rally_file_pattern)
                for e in paths:
                    rally_files.append(str(e))
        
        return pacenotes_files, rally_files


    def update_pacenotes_audio(self, pacenotes):
        def submit_for_update(pn):
            pn.network_status = statuses.PN_STATUS_UPDATING
            pn.touch()
            self.task_manager.submit(self.update_pacenote, pn.id)

        for pn in pacenotes:
            if pn.status == statuses.PN_STATUS_NEEDS_SYNC:
                print(f"submitting for update: pacenote '{pn.note_text}' is in NEEDS_SYNC")
                submit_for_update(pn)
            elif pn.dirty:
                print(f"submitting for update: pacenote '{pn.note_text}' is dirty")
                submit_for_update(pn)

    def update_pacenote(self, pnid):
        pacenote = self.pacenotes_manager.db.select(pnid)
        print(f"update_pacenote '{pacenote.note_text}'")

        response = aip_client.post_create_pacenotes_audio(pacenote)

        if response.status_code == 200:
            audio_path = pacenote.audio_path

            version_path = os.path.dirname(audio_path)
            if not os.path.exists(version_path):
                pacenotes_path = os.path.dirname(version_path)
                if not os.path.exists(pacenotes_path):
                    os.mkdir(pacenotes_path)
                os.mkdir(version_path)

            with open(audio_path, 'wb') as f:
                f.write(response.content)

            pacenote.clear_dirty()
            pacenote.touch()
            pacenote.network_status = None
            pacenote.filesystem_status = statuses.PN_STATUS_OK
            print(f"wrote audio file for '{pacenote.note_text}': {audio_path}")
        else:
            pacenote.clear_dirty()
            pacenote.touch()
            pacenote.network_status = statuses.PN_STATUS_ERROR
            print(f"request failed with status code {response.status_code}")

        res = f"pacenote updated '{pacenote.note_text}'"
        print(res)

        self.pacenote_updated.emit()
        return res

    def on_tree_item_clicked(self, item, column):
        print(f'Item clicked: {item.full_path}')
    
    def on_pacenote_updated(self):
        # print("on_pacenote_updated:", threading.current_thread().name)
        print('pacenote updated!!!')
        self.task_manager.gc_finished()
        self.update_pacenotes_info_label()

        pacenotes_files, rally_files = self.get_selected_pacenotes_files()

        filtered_pacenotes = self.get_filtered_pacenotes(pacenotes_files)
        sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)

        # filtered_rally = self.get_filtered_rally(files)

        self.update_table(sorted_pacenotes)
    
    def update_table(self, data):
        self.table.setRowCount(0)
        
        for i, pacenote in enumerate(data):
            (status, updated_at, note, voice, audio, name, version, versionId, mission, location) = self.to_table_row(pacenote)
            self.table.insertRow(i)

            status_item = QTableWidgetItem(status)
            if status == statuses.PN_STATUS_ERROR:
                status_item.setBackground(QColor(255, 0, 0))
            elif status == statuses.PN_STATUS_UPDATING:
                status_item.setBackground(QColor(255, 255, 0))
            elif status == statuses.PN_STATUS_NEEDS_SYNC:
                status_item.setBackground(QColor(0, 255, 255))
            elif status == statuses.PN_STATUS_OK:
                status_item.setBackground(QColor(0, 255, 0))
            self.table.setItem(i, 0, status_item)

            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            updated_at = time.time() - updated_at
            updated_at = int(updated_at)
            updated_at = f"{updated_at}s ago"
            item = QTableWidgetItem(updated_at)
            # item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.table.setItem(i, 1, item)

            self.table.setItem(i, 2, QTableWidgetItem(note))
            self.table.setItem(i, 3, QTableWidgetItem(voice))
            self.table.setItem(i, 4, QTableWidgetItem(audio))
            self.table.setItem(i, 5, QTableWidgetItem(name))
            self.table.setItem(i, 6, QTableWidgetItem(version))
            self.table.setItem(i, 7, QTableWidgetItem(versionId))
            self.table.setItem(i, 8, QTableWidgetItem(mission))
            self.table.setItem(i, 9, QTableWidgetItem(location))

        # self.table.resizeColumnsToContents()

    def to_table_row(self, pacenote):
        row_fields = ['status', 'updated_at', 'note_text', 'voice', 'audio_fname',
                      'note_name', 'version_name', 'version_id',
                      'mission_id', 'mission_location']
        row_data = [pacenote.get_data(f) for f in row_fields]
        return row_data
    
    def populate_tree(self):
        bench = Benchmark()
        selected_items = self.tree.selectedItems()
        selected_item_path = None

        if len(selected_items) > 1:
            print(f"tree widget multi-select is not supported yet")
        elif len(selected_items) == 1:
            selected_item_path = selected_items[0].full_path
        
        # print(f"tree selected_item_path={selected_item_path}")

        self.tree.clear()

        def shorten_root_path(input_string):
            pattern = r".*\\(BeamNG\.drive)"
            match = re.search(pattern, input_string)
            if match:
                last_component = match.group(1)
                return re.sub(pattern, last_component, input_string)
            return input_string

        idx = {}

        for root_path in self.settings_manager.get_search_paths():
            # print(f"populating tree for {root_path}")
            root_item_name = shorten_root_path(root_path)
            root_item = PacenotesTreeWidgetItem(self.tree, [root_item_name], root_path)
            idx[root_path] = root_item
            search_path = pathlib.Path(root_path)
            paths = search_path.rglob(pacenotes_file_pattern)
            rally_paths = search_path.rglob(rally_file_pattern)
            paths = itertools.chain(paths, rally_paths)
            # pacenotes_files = []
            # rally_files = []
            for e in paths:
                # print(e)
                # pacenotes_files.append(str(e))
                rel_path = e.relative_to(root_path)
                parts = pathlib.PurePath(rel_path).parts
                dir_parts = parts[:-1]
                file_part = parts[-1]
                parent_node = self.get_nested_node(idx, root_path, dir_parts)
                full_path = os.path.join(root_path, rel_path)
                file_node = PacenotesTreeWidgetItem(parent_node, [file_part], full_path)
                idx[full_path] = file_node

        self.tree.expandAll()

        if selected_item_path is not None:
            selected_item = idx[selected_item_path]
            if selected_item is not None:
                selected_item.setSelected(True)

        # bench.stop('populate_tree')
  
    def get_nested_node(self, idx, root_path, names):
        node = self.get_node(idx, None, root_path, root_path)
        names_so_far = []
        for name in names:
            names_so_far.append(name)
            idx_key = self.make_idx_key(root_path, names_so_far)
            parent_key = self.make_idx_key(root_path, names_so_far[:-1])
            if parent_key is None:
                parent_key = root_path
            node = self.get_node(idx, parent_key, name, idx_key)
            parent_key = idx_key
        return node
    
    def make_idx_key(self, root_path, names):
        if len(names) > 0:
            return os.path.join(root_path, *names)
        else:
            return None
    
    def get_node(self, idx, parent_key, name, idx_key):
        if idx_key in idx:
            return idx[idx_key]
        elif parent_key is not None:
            idx[idx_key] = PacenotesTreeWidgetItem(idx[parent_key], [name], idx_key)
            return idx[idx_key]
        else:
            raise ValueError("parent_key is None")