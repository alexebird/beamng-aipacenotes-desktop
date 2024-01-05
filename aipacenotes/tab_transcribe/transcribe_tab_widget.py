from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QAbstractTableModel,
    QThread,
)

from PyQt6.QtGui import QPainter, QMouseEvent, QPainterPath

from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QMessageBox,
    QPushButton,
    QTableView,
    QLabel,
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QHBoxLayout,
)

import logging
import sounddevice as sd
import soundfile as sf

from aipacenotes.concurrency import TaskManager
from . import RecordingThread
from . import DotWidget, Transcript, TranscriptStore

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QMouseEvent
from PyQt6.QtWidgets import QStyledItemDelegate

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

class TranscriptTable(QTableView):
    play_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setItemDelegateForColumn(1, PlayButtonDelegate())
        self.itemDelegateForColumn(1).buttonClicked.connect(self.playClicked)

    def playClicked(self, row):
        # print(f"Play button clicked on row {row}")
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
    device_refreshed = pyqtSignal(object)

    def __init__(self, settings_manager, network_tab):
        super().__init__()

        self.settings_manager = settings_manager
        self.network_tab = network_tab

        self.network_tab.on_endpoint_recording_start.connect(self.on_endpoint_recording_start)
        self.network_tab.on_endpoint_recording_stop.connect(self.on_endpoint_recording_stop)
        self.network_tab.on_endpoint_recording_cut.connect(self.on_endpoint_recording_cut)

        self.fname_transcript = self.settings_manager.get_transcript_fname()

        self.recording_thread = RecordingThread(self.settings_manager)
        self.recording_thread.transcript_created.connect(self.on_transcript_created)
        self.recording_thread.update_recording_status.connect(self.update_recording_status)
        self.recording_thread.audio_signal_detected.connect(self.audio_signal_detected)

        self.transcribe_done.connect(self.on_transcribe_done)
        self.device_refreshed.connect(self.on_device_refreshed)

        layout = QVBoxLayout()

        button_layout = QVBoxLayout()

        self.enable_voice_button = QPushButton()
        self.enable_voice_button.setText('Voice Recording OFF')
        self.enable_voice_button.setChecked(False)
        self.enable_voice_button.setFixedWidth(150)
        self.enable_voice_button.setCheckable(True)
        self.enable_voice_button.clicked.connect(self.on_enable_voice_toggled)
        button_layout.addWidget(self.enable_voice_button)

        group_box_max_w = 700
        group_box = QGroupBox("Input Audio Device")
        devices_h_layout = QHBoxLayout()
        devices_v_layout = QVBoxLayout()
        group_box.setLayout(devices_v_layout)
        group_box.setMaximumWidth(group_box_max_w)

        self.refresh_devices_button = QPushButton('Refresh')
        self.refresh_devices_button.setFixedWidth(60)
        self.refresh_devices_button.clicked.connect(self.on_refresh_devices)
        devices_h_layout.addWidget(self.refresh_devices_button)

        self.device_label = QLabel("Device:")
        devices_h_layout.addWidget(self.device_label)

        devices_v_layout.addLayout(devices_h_layout)

        self.monitor = DotWidget(Qt.GlobalColor.blue, "Monitor", "Monitor")
        devices_v_layout.addWidget(self.monitor)

        button_layout.addWidget(group_box)


        self.recording_group_box = QGroupBox("Recording Controls")
        self.recording_group_box.setEnabled(False)
        recording_btn_layout = QVBoxLayout()
        self.recording_group_box.setLayout(recording_btn_layout)
        self.recording_group_box.setMaximumWidth(group_box_max_w)

        self.start_button = QPushButton('Start')
        self.start_button.setFixedWidth(100)
        self.start_button.clicked.connect(self.start_recording)
        recording_btn_layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Stop')
        self.stop_button.setFixedWidth(100)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording)
        recording_btn_layout.addWidget(self.stop_button)

        self.cut_button = QPushButton('Cut')
        self.cut_button.setFixedWidth(100)
        self.cut_button.clicked.connect(self.cut_recording)
        recording_btn_layout.addWidget(self.cut_button)

        self.recording_widget = DotWidget(Qt.GlobalColor.red, "recording", "recording")
        recording_btn_layout.addWidget(self.recording_widget)

        button_layout.addWidget(self.recording_group_box)

        group_box = QGroupBox("Transcripts File")
        transcript_layout = QVBoxLayout()
        group_box.setLayout(transcript_layout)
        group_box.setMaximumWidth(group_box_max_w)

        self.transcript_fname_label = QLabel('Path: ' + self.fname_transcript)
        transcript_layout.addWidget(self.transcript_fname_label)

        self.clear_button = QPushButton('Clear')
        self.clear_button.setFixedWidth(100)
        self.clear_button.clicked.connect(self.clear_transcription)
        transcript_layout.addWidget(self.clear_button)

        button_layout.addWidget(group_box)

        layout.addLayout(button_layout)

        self.table = TranscriptTable()
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        stylesheet = """
        QHeaderView::section::horizontal{
            Background-color:rgb(240,240,240);
            border-radius:14px;
            border-right: 1px solid rgb(130, 136, 144);
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        header.setStyleSheet(stylesheet)

        self.transcript_store = TranscriptStore(self.fname_transcript)
        self.table_model = TranscriptionStoreTableModel(self.transcript_store)
        self.table.setModel(self.table_model)
        self.table.setColumnWidth(0, 400)
        self.table.setColumnWidth(1, 400)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 400)
        self.table.play_clicked.connect(self.play_audio)

        layout.addWidget(self.table)

        self.setLayout(layout)

        # get threaded stuff started
        self.task_manager = TaskManager(10)
        self.recording_thread.start()
        self.table_model.layoutChanged.emit()
        self.on_refresh_devices()

    def on_refresh_devices(self):
        logging.info('refreshing audio devices')
        self.device_label.setText("Device: ...") # type: ignore
        self.task_manager.submit(self.refresh_devices)

    def on_device_refreshed(self, device):
        if device:
            self.device_label.setText("Device: " + device['name'])
        else:
            self.device_label.setText("Device: <none>,")

    def refresh_devices(self):
        was_recording = self.recording_thread.recording_enabled
        if was_recording:
            self.recording_thread.set_recording_enabled(False)
            self.recording_group_box.setEnabled(False)
        try:
            # re-init the sound lib so that new devices are detected.
            sd._terminate()
            sd._initialize()
            device = sd.query_devices(kind='input')
            logging.info("found audio input device: " + str(device))
            self.recording_thread.set_device(device)
            self.device_refreshed.emit(device)
            if was_recording:
                self.recording_thread.set_recording_enabled(True)
                self.recording_group_box.setEnabled(True)
        except sd.PortAudioError:
            device = None
            self.recording_thread.set_device(device)
            self.device_refreshed.emit(device)

    def play_audio(self, row):
        def _play(row):
            transcript = self.transcript_store[row]
            data, samplerate = sf.read(transcript.fname)
            sd.play(data, samplerate)
            sd.wait()

        self.task_manager.submit(_play, row)

    def clear_transcription(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Icon.Question)
        msgBox.setText("Are you sure you want to clear all transcripts?")
        msgBox.setWindowTitle("Confirmation")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.StandardButton.Yes:
            self.transcript_store.clear()
            self.write_transcription()
            self.table_model.layoutChanged.emit()

    def write_transcription(self):
        self.transcript_store.write_to_file()

    def set_recording_ui_state(self, is_recording):
        self.start_button.setEnabled(not is_recording)
        self.stop_button.setEnabled(is_recording)

    def start_recording(self):
        self.set_recording_ui_state(True)
        self.recording_thread.start_recording()

    def stop_recording(self, vehicle_pos=None):
        self.set_recording_ui_state(False)
        self.recording_thread.stop_recording(vehicle_pos)

    def cut_recording(self, vehicle_pos=None):
        self.set_recording_ui_state(True)
        # self.stop_recording('cut_recording', vehicle_pos)
        # dont send the vehicle_pos because it will be really close to stop_recording's vehicle_pos.
        # self.start_recording()
        self.recording_thread.cut_recording(vehicle_pos)

    def on_transcript_created(self, transcript):
        self.transcript_store.add(transcript)
        self.table_model.layoutChanged.emit()
        self.task_manager.submit(self.run_transcribe, transcript)

    def run_transcribe(self, transcript):
        transcript.transcribe()
        self.transcript_store.print()
        self.transcribe_done.emit()

    def update_recording_status(self, is_recording):
        self.recording_widget.setState(is_recording)

    def on_endpoint_recording_start(self, vehicle_pos):
        logging.debug("TranscribeTab recording start")
        self.start_recording()

    def on_endpoint_recording_stop(self, vehicle_pos):
        logging.debug("TranscribeTab recording stop")
        self.stop_recording(vehicle_pos)

    def on_endpoint_recording_cut(self, vehicle_pos):
        logging.debug("TranscribeTab recording cut")
        self.cut_recording(vehicle_pos)

    def audio_signal_detected(self, above_threshold):
        self.monitor.setState(above_threshold)

    def on_transcribe_done(self):
        self.table_model.layoutChanged.emit()
        self.write_transcription()

    def on_enable_voice_toggled(self):
        if self.enable_voice_button.isChecked():
            self.enable_voice_button.setText("Voice Recording ON")
            self.enable_voice_button.setStyleSheet("""
            QPushButton:checked {
                background-color: red;
                color: white;
                font-weight: bold;
                border: 1px solid black;
                padding: 3px;
            }
            """)
            self.recording_group_box.setEnabled(True)
            self.recording_thread.set_recording_enabled(True)
        else:
            self.enable_voice_button.setText("Voice Recording OFF")
            self.enable_voice_button.setStyleSheet("")
            self.recording_group_box.setEnabled(False)
            self.recording_thread.set_recording_enabled(False)
            self.monitor.setState(False)
