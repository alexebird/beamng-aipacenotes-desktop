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

# from . import (
    # ContextMenuTreeWidget,
    # TimerThread,
    # HealthcheckThread,
    # TaskManager,
    # PacenotesManager,
    # PacenotesTreeWidgetItem,
# )

# from . import (
    # statuses,
    # Pacenote,
# )

from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager
from . import ServerThread

class NetworkTabWidget(QWidget):
    
    # hello_world = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()

        self.settings_manager = settings_manager

        self.server_thread = ServerThread()
        self.server_thread.start()

        # proxy some signals to the tab's api.
        self.on_endpoint_recording_start = self.server_thread.on_recording_start
        self.on_endpoint_recording_stop = self.server_thread.on_recording_stop
        self.on_endpoint_recording_cut = self.server_thread.on_recording_cut