import os
import webbrowser
import pprint
import logging
import sounddevice as sd
import soundfile as sf

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtGui import QCursor

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import aipacenotes.util
from aipacenotes.concurrency import TaskManager, TimerThread
from aipacenotes import client as aip_client
from .pacenotes_table import NotebookTable, NotebookTableModel
from .pacenotes_tree_widget import PacenotesTreeWidget
from .update_jobs import (
    UpdateJobsStore,
    UpdateJob,
    UPDATE_JOB_STATUS_UPDATING,
    UPDATE_JOB_STATUS_SUCCESS,
    UPDATE_JOB_STATUS_ERROR,
)
from .update_jobs_table import UpdateJobsTable, UpdateJobsTableModel
from .vertical_progress_bar import VerticalColorSegmentProgressBar

class ClickableLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.url = url

        # Set the style to look like a hyperlink
        self.setStyleSheet("color: blue; text-decoration: underline;")

        # Set the cursor to a hand pointer
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        webbrowser.open(self.url)

class PacenotesTabWidget(QWidget):

    pacenote_updated = pyqtSignal()
    job_run_finished = pyqtSignal(UpdateJob)
    tree_refreshed = pyqtSignal()
    translate_finished = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()

        self.settings_manager = settings_manager

        self.translate_in_progress = False

        self.controls_pane = QWidget()
        # stylesheet = """
        # QWidget#ControlsPane {
        #     border-bottom: 1px solid rgb(130, 136, 144);
        # }
        # """
        self.controls_pane.setObjectName('ControlsPane')
        self.controls_pane.setFixedHeight(1)
        self.controls_layout = QHBoxLayout()
        self.controls_pane.setLayout(self.controls_layout)

        self.controls_label = QLabel("", self.controls_pane)
        self.controls_layout.addWidget(self.controls_label)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.task_manager = TaskManager(10)
        self.timer_thread = TimerThread(0.5)
        self.timer_thread.timeout.connect(self.on_timer_timeout)

        self.job_run_finished.connect(self.on_job_run_finished)
        self.tree_refreshed.connect(self.on_tree_refreshed)
        self.translate_finished.connect(self.on_translate_finished)

        self.tree = PacenotesTreeWidget(self.settings_manager)
        self.tree.notebookSelectionChanged.connect(self.on_tree_notebook_selection_changed)

        self.btn_refresh_notebook = QPushButton("Refresh Tree")
        self.btn_refresh_notebook.setFixedWidth(90)
        self.btn_refresh_notebook.clicked.connect(self.on_btn_refresh_notebook_pressed)
        # table_controls_layout.addWidget(self.btn_refresh_notebook)
        # table_controls_layout.setAlignment(self.btn_refresh_notebook, Qt.AlignmentFlag.AlignLeft)

        tree_wrapper = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.btn_refresh_notebook)
        layout.addWidget(self.tree)
        tree_wrapper.setLayout(layout)

        self.splitter.addWidget(tree_wrapper)


        layout2 = QHBoxLayout()
        # self.btn_save = QPushButton("Save Translation")
        # self.btn_save.setFixedWidth(110)
        # self.btn_save.clicked.connect(self.on_btn_save_clicked)
        # layout2.addWidget(self.btn_save)
        self.notebook_info_label = QLabel("# of pacenotes: 0")
        self.notebook_info_label.setFixedWidth(120)
        # layout2.setAlignment(self.notebook_info_label, Qt.AlignmentFlag.AlignLeft)
        layout2.addWidget(self.notebook_info_label)

        self.line_edit_lang_code = QLineEdit()
        self.line_edit_lang_code.setPlaceholderText('Language Code')
        self.line_edit_lang_code.setFixedWidth(100)
        layout2.addWidget(self.line_edit_lang_code)

        self.line_edit_lang_name = QLineEdit()
        self.line_edit_lang_name.setPlaceholderText('Language Name')
        self.line_edit_lang_name.setFixedWidth(100)
        layout2.addWidget(self.line_edit_lang_name)

        self.btn_translate = QPushButton("Translate")
        self.btn_translate.setFixedWidth(100)
        self.btn_translate.clicked.connect(self.on_btn_translate_clicked)
        # layout2.setAlignment(self.btn_translate, Qt.AlignmentFlag.AlignLeft)
        layout2.addWidget(self.btn_translate)

        self.lang_code_help = ClickableLabel("language codes help", "https://cloud.google.com/translate/docs/languages")
        layout2.addWidget(self.lang_code_help)

        layout2.addStretch()

        self.notebook_table = NotebookTable()

        self.notebook_table_model = NotebookTableModel()
        self.notebook_table.setModel(self.notebook_table_model)
        self.notebook_table.setColumnWidth(0, 50)
        self.notebook_table.setColumnWidth(1, 400)
        self.notebook_table.setColumnWidth(2, 150)
        self.notebook_table.setColumnWidth(3, 150)
        self.notebook_table.setColumnWidth(4, 150)
        self.notebook_table.setColumnWidth(5, 250)
        self.notebook_table.play_clicked.connect(self.play_audio)
        self.update_notebook_info_label()

        layout = QVBoxLayout()
        layout.addLayout(layout2)
        layout.addWidget(self.notebook_table)

        self.table_controls = QWidget()
        # table_controls_layout = QHBoxLayout(self.table_controls)
        # self.table_controls.setFixedHeight(50)

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        prog_layout = QHBoxLayout()
        # Create the vertical color segment progress bar
        header_height = self.notebook_table.horizontalHeader().height()
        self.pacenotes_progress_bar = VerticalColorSegmentProgressBar(header_height)
        prog_layout.addWidget(self.pacenotes_progress_bar)
        # prog_layout.addWidget(self.notebook_table)
        prog_layout.addLayout(layout)

        right_layout.addWidget(self.table_controls)
        right_layout.addLayout(prog_layout)
        self.splitter.addWidget(right_pane)

        self.update_jobs_store = UpdateJobsStore(self.settings_manager)


        layout = QVBoxLayout()

        self.jobs_model = UpdateJobsTableModel(self.update_jobs_store)
        jobs_table = UpdateJobsTable()
        jobs_table.setModel(self.jobs_model)
        jobs_table.setColumnWidth(0, 70)
        jobs_table.setColumnWidth(1, 70)
        jobs_table.setColumnWidth(2, 400)
        jobs_table.setColumnWidth(3, 250)
        jobs_table.setColumnWidth(4, 150)
        jobs_table.setColumnWidth(5, 500)

        prog_layout = QHBoxLayout()
        # Create the vertical color segment progress bar
        header_height = jobs_table.horizontalHeader().height()
        self.jobs_progress_bar = VerticalColorSegmentProgressBar(header_height)
        prog_layout.addWidget(self.jobs_progress_bar)

        layout = QVBoxLayout()
        self.jobs_info_label = QLabel("")
        layout.addWidget(self.jobs_info_label)
        layout.addWidget(jobs_table)

        # prog_layout.addWidget(jobs_table)
        prog_layout.addLayout(layout)
        bottom_widget = QWidget()
        bottom_widget.setLayout(prog_layout)

        self.splitter_v = QSplitter(Qt.Orientation.Vertical)
        self.splitter_v.addWidget(self.splitter)
        self.splitter_v.addWidget(bottom_widget)

        vbox = QVBoxLayout()
        vbox.addWidget(self.controls_pane)
        vbox.addWidget(self.splitter_v)
        self.setLayout(vbox)

        splitter_width = self.splitter.width()
        splitter_left_width = int(splitter_width / 4) + 10
        splitter_right_width = splitter_width - splitter_left_width
        self.splitter.setSizes([splitter_left_width, splitter_right_width])

        self.tree.populate()
        self.tree_refreshed.emit()
        # self.tree.select_default()
        self.timer_thread.start()

    def on_tree_notebook_selection_changed(self, notebook_file):
        self.notebook_table_model.setNotebookFile(notebook_file)
        self.notebook_table_model.layoutChanged.emit()
        self.update_notebook_info_label()
        self.refresh_pacenotes_table_progress()

    def update_notebook_info_label(self):
        self.notebook_info_label.setText(f"# of pacenotes: {self.notebook_table_model.rowCount()}")

    def update_jobs_info_label(self):
        counts = [[k,v] for k,v in self.update_jobs_store.count_by_status().items()]
        counts.sort(key=lambda pair: pair[0])
        count_str = [f"{cnt[0]}={cnt[1]}" for cnt in counts]
        self.jobs_info_label.setText(f"# of jobs: {' / '.join(count_str)}")

    def play_audio(self, row):
        def _play(fname):
            # self.settings_manager.update_status_left(f"played {fname}")
            data, samplerate = sf.read(fname)
            # volume_factor = 0.4 # ie have effect of lowering the gain.
            # data = data * volume_factor
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
            self.settings_manager.load()
            self.tree.clear()
            self.tree.populate()
            self.tree_refreshed.emit()
            self.notebook_table_model.setNotebookFile(None)
            self.notebook_table_model.layoutChanged.emit()
            self.update_notebook_info_label()

        self.task_manager.submit(_special_button_refresh)

    def refresh_pacenotes(self):
        # logging.debug('refreshing pacenotes')
        notebook_file = self.notebook_table_model.notebook_file
        if not notebook_file:
            return

        notebook_file.load()
        notebook = notebook_file.notebook()

        for pacenote in notebook.pacenotes():
            if pacenote.needs_update():
                job = self.update_jobs_store.add_job(pacenote)
                # self.update_jobs_store.print()
                self.jobs_model.layoutChanged.emit()
                self.update_jobs_info_label()

                def _run_job(job):
                    job.run(self.job_run_finished)

                if job:
                    self.task_manager.submit(_run_job, job)

        self.refresh_pacenotes_table_progress()
        self.refresh_jobs_table_progress()

        self.update_jobs_store.update_job_time_agos()
        self.update_jobs_store.prune()
        self.delete_orphaned_files(notebook_file)
        self.jobs_model.layoutChanged.emit()
        self.notebook_table_model.setNotebookFile(notebook_file)
        self.notebook_table_model.layoutChanged.emit()
        self.update_notebook_info_label()
        self.update_jobs_info_label()
        self.task_manager.gc_finished()

    def refresh_pacenotes_table_progress(self):
        segments = []

        def clr_fn(pacenote):
            return pacenote.note_file_exists() and Qt.GlobalColor.green or Qt.GlobalColor.red

        notebook_file = self.notebook_table_model.notebook_file
        notebook = notebook_file.notebook()
        if notebook:
            for pacenote in notebook.pacenotes():
                if len(segments) == 0:
                    segments.append([0, clr_fn(pacenote)])

                if segments[-1][1] == pacenote.note_file_exists():
                    segments[-1][0] += 1
                else:
                    segments.append([1, clr_fn(pacenote)])

        self.pacenotes_progress_bar.set_segments(segments)

    def refresh_jobs_table_progress(self):
        segments = []

        def clr_fn(job):
            if job.status() == UPDATE_JOB_STATUS_SUCCESS:
                return Qt.GlobalColor.green
            elif job.status() == UPDATE_JOB_STATUS_UPDATING:
                return Qt.GlobalColor.cyan
            elif job.status() == UPDATE_JOB_STATUS_ERROR:
                return Qt.GlobalColor.red
            else:
                return Qt.GlobalColor.gray

        for job in self.update_jobs_store.jobs:
            if len(segments) == 0:
                segments.append([0, clr_fn(job)])

            if segments[-1][1] == job.status():
                segments[-1][0] += 1
            else:
                segments.append([1, clr_fn(job)])

        self.jobs_progress_bar.set_segments(segments)

    def delete_orphaned_files(self, notebook_file):
        notebook = notebook_file.notebook()

        desired_files = set()

        for pacenote in notebook.pacenotes():
            desired_files.add(pacenote.note_abs_path())

        all_files = set()
        for root, dirs, files in os.walk(notebook.pacenotes_dir()):
            for file in files:
                if file.endswith('.ogg'):
                    full_path = os.path.join(root, file)
                    all_files.add(aipacenotes.util.normalize_path(os.path.abspath(full_path)))

        files_to_delete = all_files - desired_files

        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logging.info(f"Deleted: {file_path}")
            except OSError as e:
                logging.error(f"Error: {file_path} : {e.strerror}")


        # if self.jobs_model.rowCount() == 0:
        for root, dirs, files in os.walk(notebook.pacenotes_dir(), topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(dir_path):  # Check if the directory is empty
                    os.rmdir(dir_path)
                    logging.info(f"Deleted empty directory: {dir_path}")

    def on_job_run_finished(self, job):
        self.jobs_model.layoutChanged.emit()
        self.notebook_table_model.layoutChanged.emit()
        self.update_notebook_info_label()
        self.update_jobs_info_label()
        self.refresh_pacenotes_table_progress()
        self.refresh_jobs_table_progress()

    def on_tree_refreshed(self):
        self.tree.expandAll()

    def on_timer_timeout(self):
        if not self.translate_in_progress:
            self.task_manager.submit(self.refresh_pacenotes)

    def perform_translate(self):
        notebook_file = self.notebook_table_model.notebook_file
        if not notebook_file:
            return

        notebook_file.load()
        notebook = notebook_file.notebook()

        input_lang = 'english'
        target_lang_code = self.line_edit_lang_code.text()
        target_lang_name = self.line_edit_lang_name.text()

        skip_strings = {
            aipacenotes.util.AUTOFILL_BLOCKER: True,
            aipacenotes.util.AUTOFILL_BLOCKER_INTERNAL: True,
        }

        translation_input = {
            "input_language": input_lang,
            "target_language_code": target_lang_code,
            "target_language_name": target_lang_name,
            "skip_strings": skip_strings,
            "pacenotes": notebook.pacenotes_for_translation(input_lang),
        }

        response = aip_client.post_translate_all(translation_input)
        logging.info(response)
        if response['ok']:
            pacenotes = response['pacenotes']
            notebook_file.update_with_translation(pacenotes, target_lang_name)
            notebook.pacenotes(use_cache=False)
            pprint.pprint(notebook_file.data)
            notebook_file.save()
            print('translation done')
        else:
            logging.error(f"translation response error: {response['msg']}")

        self.translate_finished.emit()

    def on_translate_finished(self):
        dialog = QMessageBox()
        dialog.setWindowTitle("Translation")
        dialog.setText("Translation completed.\nThe notebook file was saved and a backup file was be created.\n(check logs/terminal for path).")
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        retval = dialog.exec()

        self.btn_translate.setEnabled(True)
        self.btn_translate.setText("Translate")
        self.translate_in_progress = False

    def on_btn_translate_clicked(self):
        if not self.notebook_table_model.notebook_file:
            return

        self.translate_in_progress = True

        self.btn_translate.setEnabled(False)
        self.btn_translate.setText("Translating...")

        # dialog = QMessageBox()
        # dialog.setWindowTitle("Translation")
        # dialog.setText("Translation in progress.")
        # dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        # retval = dialog.exec()

        self.task_manager.submit(self.perform_translate)

    # def on_btn_save_clicked(self):
    #     def _perform_save():
    #         notebook_file = self.notebook_table_model.notebook_file
    #         if notebook_file:
    #             notebook_file.save()
    #
    #     self.task_manager.submit(_perform_save)
