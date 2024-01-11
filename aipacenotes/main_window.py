from PyQt6.QtGui import (
    QAction,
    QKeySequence,
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
)

import logging

from aipacenotes.tab_pacenotes import PacenotesTabWidget
from aipacenotes.tab_network import NetworkTabWidget
from aipacenotes.tab_transcribe import TranscribeTabWidget

from aipacenotes.settings import SettingsManager
from aipacenotes.status_bar import StatusBarWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1200, 800)

        self.setWindowTitle("AI Pacenotes")

        # Create a menu bar
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Add action to the file menu
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+q"))
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.status_bar = StatusBarWidget()

        # Managers live for the lifetime of the program so they can detect changes across pacenote file scans.
        self.settings_manager = SettingsManager(self.status_bar)
        # self.settings_manager.load()

        # logging.info(f"BeamNG user dir: {self.settings_manager.get_beam_user_home()}")

        # self.pacenotes_tab = PacenotesTabWidget(self.settings_manager)
        self.network_tab = NetworkTabWidget(self.settings_manager)
        # self.transcribe_tab = TranscribeTabWidget(self.settings_manager, self.network_tab)

        self.tab_widget = QTabWidget()
        # self.tab_widget.addTab(self.pacenotes_tab, "Pacenotes")
        self.tab_widget.addTab(self.network_tab, "Network")
        # self.tab_widget.addTab(self.transcribe_tab, "Voice")

        self.top_lvl_widget = QWidget()
        self.top_lvl_layout = QVBoxLayout()
        self.top_lvl_widget.setLayout(self.top_lvl_layout)

        self.top_lvl_layout.addWidget(self.tab_widget)
        self.top_lvl_layout.addWidget(self.status_bar)

        self.setCentralWidget(self.top_lvl_widget)

    def things_to_stop(self):
        return [
            # self.pacenotes_tab.timer_thread.stop,
            # self.pacenotes_tab.task_manager.shutdown,
            # self.transcribe_tab.stop_recording_thread,
        ]
