from PyQt6.QtGui import (
    QAction,
    QKeySequence,
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
)

from aipacenotes.tab_pacenotes import PacenotesTabWidget
from aipacenotes.tab_network import NetworkTabWidget
from aipacenotes.tab_transcribe import TranscribeTabWidget

# from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager

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
        # self.transcribe_tab.recording_thread.update_transcription.connect(self.network_tab.server_thread.set_latest_transcript)
        # self.transcribe_tab.update_transcription.connect(self.network_tab.server_thread.set_latest_transcript)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.pacenotes_tab, "Pacenotes")
        self.tab_widget.addTab(self.network_tab, "Network")
        i = self.tab_widget.addTab(self.transcribe_tab, "Voice")
        self.setCentralWidget(self.tab_widget)
        # self.tab_widget.setCurrentIndex(i)
        self.tab_widget.setCurrentWidget(self.transcribe_tab)
    
    def things_to_stop(self):
        return [
            self.pacenotes_tab.timer_thread.stop,
            self.pacenotes_tab.task_manager.shutdown, 
            self.transcribe_tab.recording_thread.stop,
        ]