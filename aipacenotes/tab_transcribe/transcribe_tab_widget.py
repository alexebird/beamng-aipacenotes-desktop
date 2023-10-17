import pathlib
import json
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
    QComboBox,
    QSplitter,
    QLabel,
    QHeaderView,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from aipacenotes.voice import SpeechToText
from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager
from . import RecordingThread
from aipacenotes.tab_pacenotes import (
    TaskManager,
)

class TranscribeTabWidget(QWidget):
    
    # hello_world = pyqtSignal()

    update_transcription_txt = pyqtSignal()

    def __init__(self, settings_manager, network_tab):
        super().__init__()

        self.settings_manager = settings_manager
        self.network_tab = network_tab

        self.task_manager = TaskManager(10)
        # self.task_manager.get_future_count()
        # self.task_manager.gc_finished()

        self.network_tab.on_endpoint_recording_start.connect(self.on_endpoint_recording_start)
        self.network_tab.on_endpoint_recording_stop.connect(self.on_endpoint_recording_stop)
        self.network_tab.on_endpoint_recording_cut.connect(self.on_endpoint_recording_cut)

        # self.recording_thread = None
        self.fname_transcription = self.settings_manager.get_transcription_txt_fname()
        self.recording_thread = RecordingThread("USB Audio Device")
        # self.recording_thread.update_transcription.connect(self.update_transcription)
        self.recording_thread.recording_file_created.connect(self.recording_file_created)
        self.recording_thread.update_status.connect(self.update_status)
        self.recording_thread.start()
    
        self.update_transcription_txt.connect(self.update_transcription)

        layout = QVBoxLayout()

        button_layout = QVBoxLayout()
        # button_layout.setMaxWidth(300)  # Set maximum width of the layout

        self.device_combo = QComboBox()
        self.device_combo.setFixedWidth(400)
        devices = [f'[{d["index"]}] {d["name"]}' for d in self.recording_thread.get_default_audio_device()]
        self.device_combo.addItems(devices)
        button_layout.addWidget(self.device_combo)
        button_layout.setStretchFactor(self.device_combo, 1)
        button_layout.setAlignment(self.device_combo, Qt.AlignmentFlag.AlignLeft)

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

        self.clear_button = QPushButton('Clear')
        self.clear_button.setFixedWidth(100)
        self.clear_button.clicked.connect(self.clear_transcription_file)
        button_layout.addWidget(self.clear_button)
        button_layout.setStretchFactor(self.clear_button, 1)
        button_layout.setAlignment(self.clear_button, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(button_layout)

        self.status_label = QLabel('ready')
        layout.addWidget(self.status_label)

        self.transcription_output = QTextEdit()
        self.transcription_output.setReadOnly(True)
        layout.addWidget(self.transcription_output)

        self.setLayout(layout)
        self.update_transcription_txt.emit()
    
    def clear_transcription_file(self):
        with open(self.fname_transcription, 'w') as f:
            f.truncate(0)
        self.update_transcription_txt.emit()

    def start_recording(self, vehicle_pos=None):
        # if self.recording_thread is None:
            # self.recording_thread = RecordingThread(self.settings_manager.get_transcription_txt())
        fname = self.recording_thread.start_recording()
        if vehicle_pos:
            vehicle_pos['_src'] = 'start_recording'
            vehicle_pos['_file'] = fname
            self.append_vehicle_pos(vehicle_pos)

    def stop_recording(self, src='stop_recording', vehicle_pos=None):
        # if self.recording_thread:
            # self.recording_thread.stop()
            # self.recording_thread.wait()
            # self.recording_thread = None
        if not src:
            src = 'stop_recording'
        self.recording_thread.stop_recording(src, vehicle_pos)
    
    def cut_recording(self, vehicle_pos=None):
        self.stop_recording('cut_recording', vehicle_pos)
        # dont send the vehicle_pos because it will be really close to stop_recording's vehicle_pos.
        self.start_recording()
    
    def update_transcription(self):
        with open(self.fname_transcription, 'r') as f:
            self.transcription_output.setText(f.read())

    def recording_file_created(self, src, fname, vehicle_pos):
        # self.transcription_output.append(f"wrote recording to file: {fname}")
        self.task_manager.submit(self.do_transcription, src, fname, vehicle_pos)

    def do_transcription(self, src, fname, vehicle_pos):
        transcript = self.transcribe(fname)

        if vehicle_pos:
            vehicle_pos['_src'] = src
            vehicle_pos['_file'] = fname
            vehicle_pos['_transcript'] = transcript
            self.append_vehicle_pos(vehicle_pos, transcript + " || ")
        else:
            self.append_transcript(transcript)
        
        self.update_transcription_txt.emit()
    
    def update_status(self, text):
        self.status_label.setText(f"Status: {text}")
    
    def on_endpoint_recording_start(self, vehicle_pos):
        print("TranscribeTab recording start")
        self.start_recording(vehicle_pos)
    
    def on_endpoint_recording_stop(self, vehicle_pos):
        print("TranscribeTab recording stop")
        self.stop_recording('stop_recording', vehicle_pos)
    
    def on_endpoint_recording_cut(self, vehicle_pos):
        print("TranscribeTab recording cut")
        self.cut_recording(vehicle_pos)

    def transcribe(self, fname):
        speech = SpeechToText(fname)
        speech.trim_silence()
        txt = speech.transcribe() or ""
        return txt.lower()
    
    def append_transcript(self, text):
        if isinstance(text, str):
            with open(self.fname_transcription, 'a') as f:
                f.write(text + '\n')
    
    def append_vehicle_pos(self, vehicle_pos, prefix=""):
        self.append_transcript(prefix + json.dumps(vehicle_pos))