import json
import logging
import os

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QAbstractTableModel,
    QRect,
    QPoint
)

from PyQt6.QtGui import QPainter, QMouseEvent, QPainterPath

from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QMessageBox,
    QPushButton,
    QComboBox,
    QTextEdit,
    QTableView,
    QLabel,
    QWidget,
    QVBoxLayout,
)

import sounddevice as sd
import soundfile as sf

from aipacenotes.voice import SpeechToText
# from aipacenotes import client as aip_client
# from aipacenotes.settings import SettingsManager
from aipacenotes.concurrency import TaskManager
from . import RecordingThread
from . import MonitorWidget, Transcript, TranscriptStore

from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QMouseEvent
from PyQt6.QtWidgets import QStyledItemDelegate, QTableWidget

class PlayButtonDelegate(QStyledItemDelegate):
    buttonClicked = pyqtSignal(int)

    def paint(self, painter: QPainter, option, index):
        tri_width = 20
        padding = 5
        rect = option.rect

        # Enable anti-aliasing
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Define square box dimensions
        square_side = tri_width-5
        square_x = rect.left() + 5
        square_y = rect.top() + (rect.height() - square_side) // 2

        # Draw the square box
        # painter.setBrush(Qt.GlobalColor.white)
        # square_rect = QRect(square_x, square_y, square_side, square_side)
        # painter.drawRect(square_rect)

        # Draw the sideways triangle within the square box
        painter.setBrush(Qt.GlobalColor.blue)
        path = QPainterPath()
        path.moveTo(square_x, square_y)
        path.lineTo(square_x + square_side, square_y + square_side // 2)
        path.lineTo(square_x, square_y + square_side)
        path.lineTo(square_x, square_y)
        painter.drawPath(path)

        option.rect.setLeft(option.rect.left() + tri_width + padding)

        super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if isinstance(event, QMouseEvent):
            if event.type() == QMouseEvent.Type.MouseButtonRelease:
                if option.rect.contains(event.pos()):
                    self.buttonClicked.emit(index.row())
                    return True
        return False

class CustomTable(QTableView):
    play_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setItemDelegateForColumn(2, PlayButtonDelegate())
        self.itemDelegateForColumn(2).buttonClicked.connect(self.playClicked)

    def playClicked(self, row):
        print(f"Play button clicked on row {row}")
        self.play_clicked.emit(row)

class TranscriptionStoreTableModel(QAbstractTableModel):
    def __init__(self, data):
        super(TranscriptionStoreTableModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.size()

    def columnCount(self, parent=None):
        return Transcript.col_count

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            row = self._data.transcripts[index.row()]
            return row.fieldAt(index.column())
    
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return Transcript.table_headers[section]
    
class TranscribeTabWidget(QWidget):
    transcribe_done = pyqtSignal()

    def __init__(self, settings_manager, network_tab):
        super().__init__()

        self.settings_manager = settings_manager
        self.network_tab = network_tab

        self.network_tab.on_endpoint_recording_start.connect(self.on_endpoint_recording_start)
        self.network_tab.on_endpoint_recording_stop.connect(self.on_endpoint_recording_stop)
        self.network_tab.on_endpoint_recording_cut.connect(self.on_endpoint_recording_cut)

        self.fname_transcription = self.settings_manager.get_transcription_txt_fname()
        self.recording_thread = RecordingThread(self.settings_manager)
        self.recording_thread.transcript_created.connect(self.on_transcript_created)
        self.recording_thread.update_status.connect(self.update_status)
        self.recording_thread.audio_signal_detected.connect(self.audio_signal_detected)
    
        self.transcribe_done.connect(self.on_transcribe_done)

        layout = QVBoxLayout()

        button_layout = QVBoxLayout()
        # button_layout.setMaxWidth(300)  # Set maximum width of the layout

        self.device_combo = QComboBox()
        self.device_combo.setFixedWidth(400)
        try:
            devices = [f'[{d["index"]}] {d["name"]}' for d in self.recording_thread.get_default_audio_device()]
        except sd.PortAudioError as e:
            print("startup error in RecordingThread")
            self.startup_error = True
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
        self.clear_button.clicked.connect(self.clear_transcription)
        button_layout.addWidget(self.clear_button)
        button_layout.setStretchFactor(self.clear_button, 1)
        button_layout.setAlignment(self.clear_button, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(button_layout)

        self.status_label = QLabel('ready')
        layout.addWidget(self.status_label)

        self.monitor = MonitorWidget()
        self.monitor.monitor_checkbox_changed.connect(self.monitor_checkbox_changed)
        layout.addWidget(self.monitor)

        # self.transcription_output = QTextEdit()
        # self.transcription_output.setReadOnly(True)
        # self.transcription_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # layout.addWidget(self.transcription_output)

        self.table = CustomTable()
        self.table.verticalHeader().setVisible(False)

        self.transcript_store = TranscriptStore()
        self.table_model = TranscriptionStoreTableModel(self.transcript_store)
        self.table.setModel(self.table_model)
        self.table.setColumnWidth(0, 400)
        self.table.setColumnWidth(1, 400)
        self.table.setColumnWidth(2, 400)
        self.table.play_clicked.connect(self.play_audio)

        layout.addWidget(self.table)

        self.setLayout(layout)
        # self.update_transcription_txt.emit()

        # self.table_model.layoutChanged.emit()

        # start threads after setting up connects
        self.task_manager = TaskManager(10)
        self.recording_thread.start()

        # in case you need a test row
        # tt = Transcript("test", 'tmp\\out_test.wav', {})
        # tt.txt = "test"
        # self.transcript_store.add(tt)
        # self.table_model.layoutChanged.emit()

        # self.task_manager.get_future_count()
        # self.task_manager.gc_finished()

    def play_audio(self, row):
        def _play(row):
            transcript = self.transcript_store[row]
            # Read the WAV file
            data, samplerate = sf.read(transcript.fname)
            # Play the WAV file
            sd.play(data, samplerate)
            # Wait until the file is done playing
            sd.wait()

        self.task_manager.submit(_play, row)
    
    def clear_transcription(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Icon.Question)
        msgBox.setText("Are you sure you want to clear all data?")
        msgBox.setWindowTitle("Confirmation")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        returnValue = msgBox.exec()
        if returnValue == QMessageBox.StandardButton.Yes:
            self.transcript_store.clear()
            with open(self.fname_transcription, 'w') as f:
                f.truncate(0)
            self.table_model.layoutChanged.emit()

    def write_transcription(self):
        self.transcript_store.write_to_file(self.fname_transcription)

    def start_recording(self, vehicle_pos=None):
        # if self.recording_thread is None:
            # self.recording_thread = RecordingThread(self.settings_manager.get_transcription_txt())
        fname = self.recording_thread.start_recording()
        if vehicle_pos:
            vehicle_pos['_src'] = 'start_recording'
            vehicle_pos['_file'] = fname
            self.append_vehicle_pos(vehicle_pos, '             ')

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
    
    # def update_transcription(self):
        # if os.path.isfile(self.fname_transcription):
            # with open(self.fname_transcription, 'r') as f:
                # self.transcription_output.setText(f.read())
        # else:
            # logging.warn(f"couldnt find transcription.txt at: {self.fname_transcription}")

    # def recording_file_created(self, src, fname, file_create_time, vehicle_pos):
    #     # self.transcription_output.append(f"wrote recording to file: {fname}")
    #     self.task_manager.submit(self.do_transcription, src, fname, vehicle_pos)

    def on_transcript_created(self, transcript):
        # self.transcription_output.append(f"wrote recording to file: {fname}")
        self.transcript_store.add(transcript)
        self.transcript_store.print()
        # self.refresh_table.emit()
        self.table_model.layoutChanged.emit()
        self.task_manager.submit(self.run_transcribe, transcript)
    
    def run_transcribe(self, transcript):
        transcript.transcribe()
        self.transcribe_done.emit()
    
    # def on_refresh_table(self):
        # from PyQt6.QtCore import QThread
        # print("Current QThread:", QThread.currentThread())
        # self.table_model.layoutChanged.emit()

    # def on_transcript_done(self, transcript):
        # self.table_model.layoutChanged.emit()

    # def do_transcription(self, src, fname, vehicle_pos):
    #     transcript = self.transcribe(fname)

    #     if vehicle_pos:
    #         vehicle_pos['_src'] = src
    #         vehicle_pos['_file'] = fname
    #         vehicle_pos['_transcript'] = transcript
    #         self.append_vehicle_pos(vehicle_pos, transcript + " || ")
    #     else:
    #         self.append_transcript(transcript)
        
    #     self.update_transcription_txt.emit()
    
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

    # def append_transcript(self, text):
    #     if isinstance(text, str):
    #         with open(self.fname_transcription, 'a') as f:
    #             f.write(text + '\n')
    
    # def append_vehicle_pos(self, vehicle_pos, prefix=""):
    #     self.append_transcript(prefix + json.dumps(vehicle_pos))

    def audio_signal_detected(self, above_threshold):
        self.monitor.setMonitorState(above_threshold)

    def monitor_checkbox_changed(self, should_monitor):
        self.recording_thread.shouldMonitor(should_monitor)

    def on_transcribe_done(self):
        print('transcribe_done')
        self.transcript_store.print()

        from PyQt6.QtCore import QThread
        print("Current QThread:", QThread.currentThread())

        self.table_model.layoutChanged.emit()
        self.write_transcription()