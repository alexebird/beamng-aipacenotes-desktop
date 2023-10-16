import pathlib
import os
import re
import time
import fnmatch
import itertools


from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel

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

from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager
from . import RecordingThread

class TranscribeTabWidget(QWidget):
    
    # hello_world = pyqtSignal()

    def __init__(self, network_tab):
        super().__init__()

        self.network_tab = network_tab

        self.network_tab.on_endpoint_recording_start.connect(self.on_endpoint_recording_start)
        self.network_tab.on_endpoint_recording_stop.connect(self.on_endpoint_recording_stop)
        self.network_tab.on_endpoint_recording_cut.connect(self.on_endpoint_recording_cut)

        self.thread = None

        layout = QVBoxLayout()

        button_layout = QVBoxLayout()
        # button_layout.setMaxWidth(300)  # Set maximum width of the layout

        self.start_button = QPushButton('Start')
        self.start_button.setFixedWidth(100)
        self.start_button.clicked.connect(self.start_recording)
        button_layout.addWidget(self.start_button)
        button_layout.setStretchFactor(self.start_button, 1)
        button_layout.setAlignment(self.start_button, Qt.AlignmentFlag.AlignLeft)

        self.stop_button = QPushButton('Stop')
        self.stop_button.setFixedWidth(100)
        self.stop_button.clicked.connect(self.stop_recording)
        button_layout.addWidget(self.stop_button)
        button_layout.setStretchFactor(self.stop_button, 1)
        button_layout.setAlignment(self.stop_button, Qt.AlignmentFlag.AlignLeft)

        self.cut_button = QPushButton('Cut')
        self.cut_button.setFixedWidth(100)
        self.cut_button.clicked.connect(self.cut_recording)
        button_layout.addWidget(self.cut_button)
        button_layout.setStretchFactor(self.cut_button, 1)
        button_layout.setAlignment(self.cut_button, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(button_layout)

        self.status_label = QLabel('Status: Idle')
        layout.addWidget(self.status_label)

        self.transcription_output = QTextEdit()
        self.transcription_output.setReadOnly(True)
        layout.addWidget(self.transcription_output)

        self.setLayout(layout)

    def start_recording(self):
        if self.thread is None:
            self.thread = RecordingThread()
            self.thread.update_transcription.connect(self.update_transcription)
            self.thread.update_status.connect(self.update_status)
            self.thread.start()

    def stop_recording(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait()
            self.thread = None

    def cut_recording(self):
        self.stop_recording()
        self.start_recording()

    def update_transcription(self, text):
        # self.transcription_output.append(text)
        self.transcription_output.setText(text)

    def update_status(self, text):
        self.status_label.setText(f"Status: {text}")
    
    def on_endpoint_recording_start(self):
        print("TranscribeTab recording start")
        self.start_recording()
    
    def on_endpoint_recording_stop(self):
        print("TranscribeTab recording stop")
        self.stop_recording()
    
    def on_endpoint_recording_cut(self):
        print("TranscribeTab recording cut")
        self.cut_recording()