from PyQt6.QtCore import (
    Qt,
    QCoreApplication,
)

from PyQt6.QtGui import (
    QAction,
    QKeySequence,
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QPushButton,
    QWidget,
    QVBoxLayout,
)

import logging

from aipacenotes.tab_pacenotes import PacenotesTabWidget
from aipacenotes.tab_network import NetworkTabWidget
from aipacenotes.tab_transcribe import TranscribeTabWidget

from aipacenotes.settings import SettingsManager, SettingsDialog
from aipacenotes.status_bar import StatusBarWidget
import aipacenotes.util

APP_NAME = "AI Pacenotes"

QCoreApplication.setApplicationName(APP_NAME)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1200, 800)
        self.setWindowTitle(APP_NAME)

        # Create a menu bar
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu("&File")
        self.edit_menu = self.menu_bar.addMenu("&Edit")

        settings_action = QAction("Settings", self)
        # settings_action.setShortcut(QKeySequence("Ctrl+q"))
        settings_action.triggered.connect(self.close)
        self.edit_menu.addAction(settings_action)

        # Add action to the file menu
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+q"))
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.status_bar = StatusBarWidget()

        # Managers live for the lifetime of the program so they can detect changes across pacenote file scans.
        self.settings_manager = SettingsManager(self.status_bar)
        if aipacenotes.util.is_windows():
            self.settings_manager.load()
            logging.info(f"BeamNG user dir: {self.settings_manager.get_beam_user_home()}")

        if aipacenotes.util.is_windows():
            self.pacenotes_tab = PacenotesTabWidget(self.settings_manager)
            self.transcribe_tab = TranscribeTabWidget(self.settings_manager, self.network_tab)
        self.network_tab = NetworkTabWidget(self.settings_manager)


        self.tab_widget = QTabWidget()
        if aipacenotes.util.is_windows():
            self.tab_widget.addTab(self.pacenotes_tab, "Pacenotes")
        self.tab_widget.addTab(self.network_tab, "Network")
        if aipacenotes.util.is_windows():
            self.tab_widget.addTab(self.transcribe_tab, "Voice")

        self.top_lvl_widget = QWidget()
        self.top_lvl_layout = QVBoxLayout()
        self.top_lvl_widget.setLayout(self.top_lvl_layout)

        if aipacenotes.util.is_mac():
            settings_button = QPushButton("Open Settings")
            settings_button.clicked.connect(self.open_settings_dialog)
            self.top_lvl_layout.addWidget(settings_button)
        self.top_lvl_layout.addWidget(self.tab_widget)
        self.top_lvl_layout.addWidget(self.status_bar)

        self.setCentralWidget(self.top_lvl_widget)

    def things_to_stop(self):
        if aipacenotes.util.is_windows():
            return [
                # self.pacenotes_tab.timer_thread.stop,
                # self.pacenotes_tab.task_manager.shutdown,
                self.transcribe_tab.stop_recording_thread,
            ]
        else:
            return []

    def open_settings_dialog(self):
        dialog = SettingsDialog()
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)  # Dialog will stay on top of the main window
        dialog.exec()
