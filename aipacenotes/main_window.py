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
    QAction,
    QKeySequence,
    QColor,
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
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

from aipacenotes.tab_pacenotes import (
    ContextMenuTreeWidget,
    TimerThread,
    HealthcheckThread,
    TaskManager,
    PacenotesManager,
    PacenotesTreeWidgetItem,
)

from aipacenotes.tab_pacenotes import PacenotesTabWidget
from aipacenotes.tab_network import NetworkTabWidget
from aipacenotes.tab_transcribe import TranscribeTabWidget

from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager

import time

pacenotes_file_pattern = '*.pacenotes.json'
rally_file_pattern = '*.rally.json'

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

        # Managers live for the lifetime of the program so they can detect changes across pacenote file scans.
        self.settings_manager = SettingsManager()
        self.settings_manager.load()

        self.pacenotes_tab = PacenotesTabWidget(self.settings_manager)
        self.network_tab = NetworkTabWidget(self.settings_manager)
        self.transcribe_tab = TranscribeTabWidget(self.settings_manager, self.network_tab)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.pacenotes_tab, "Pacenotes")
        self.tab_widget.addTab(self.network_tab, "Network")
        self.tab_widget.addTab(self.transcribe_tab, "Transcriber")
        self.setCentralWidget(self.tab_widget)
    
    def things_to_stop(self):
        return [
            self.pacenotes_tab.timer_thread.stop,
            self.pacenotes_tab.task_manager.shutdown, 
        ]