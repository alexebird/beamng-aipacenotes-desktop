import os
import logging
import sounddevice as sd
import soundfile as sf

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtWidgets import (
    QSplitter,
    QLabel,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

import aipacenotes.util
from aipacenotes.concurrency import TaskManager, TimerThread
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

class PacenotesTabWidget(QWidget):

    pacenote_updated = pyqtSignal()
    job_run_finished = pyqtSignal(UpdateJob)
    tree_refreshed = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()

        self.settings_manager = settings_manager

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

        self.tree = PacenotesTreeWidget(self.settings_manager)
        self.tree.notebookSelectionChanged.connect(self.on_tree_notebook_selection_changed)

        tree_wrapper = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(self.tree)
        tree_wrapper.setLayout(layout)

        self.splitter.addWidget(tree_wrapper)

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

        self.table_controls = QWidget()
        table_controls_layout = QHBoxLayout(self.table_controls)
        self.table_controls.setFixedHeight(50)

        self.btn_refresh_notebook = QPushButton("Refresh Tree")
        self.btn_refresh_notebook.setFixedWidth(90)
        self.btn_refresh_notebook.clicked.connect(self.on_btn_refresh_notebook_pressed)
        table_controls_layout.addWidget(self.btn_refresh_notebook)
        table_controls_layout.setAlignment(self.btn_refresh_notebook, Qt.AlignmentFlag.AlignLeft)

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        prog_layout = QHBoxLayout()
        # Create the vertical color segment progress bar
        header_height = self.notebook_table.horizontalHeader().height()
        self.pacenotes_progress_bar = VerticalColorSegmentProgressBar(header_height)
        prog_layout.addWidget(self.pacenotes_progress_bar)
        prog_layout.addWidget(self.notebook_table)

        right_layout.addWidget(self.table_controls)
        right_layout.addLayout(prog_layout)
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
        jobs_table.setColumnWidth(5, 500)

        prog_layout = QHBoxLayout()
        # Create the vertical color segment progress bar
        header_height = jobs_table.horizontalHeader().height()
        self.jobs_progress_bar = VerticalColorSegmentProgressBar(header_height)
        prog_layout.addWidget(self.jobs_progress_bar)
        prog_layout.addWidget(jobs_table)
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
        self.refresh_pacenotes_table_progress()

    def play_audio(self, row):
        def _play(fname):
            # self.settings_manager.update_status_left(f"played {fname}")
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
            self.settings_manager.load()
            self.tree.clear()
            self.tree.populate()
            self.tree_refreshed.emit()
            # self.refresh_pacenotes()
            self.notebook_table_model.setNotebookFile(None)
            self.notebook_table_model.layoutChanged.emit()

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
                print(f"Deleted: {file_path}")
            except OSError as e:
                print(f"Error: {file_path} : {e.strerror}")


        # if self.jobs_model.rowCount() == 0:
        for root, dirs, files in os.walk(notebook.pacenotes_dir(), topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(dir_path):  # Check if the directory is empty
                    os.rmdir(dir_path)
                    print(f"Deleted empty directory: {dir_path}")

    def on_job_run_finished(self, job):
        self.jobs_model.layoutChanged.emit()
        self.notebook_table_model.layoutChanged.emit()
        self.refresh_pacenotes_table_progress()
        self.refresh_jobs_table_progress()

    def on_tree_refreshed(self):
        self.tree.expandAll()

    def on_timer_timeout(self):
        self.task_manager.submit(self.refresh_pacenotes)
