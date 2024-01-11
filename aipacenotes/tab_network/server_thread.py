from PyQt6.QtCore import (
    QThread,
    pyqtSignal,
)

import logging
from aipacenotes.server import Server
import aipacenotes.util

class ServerThread(QThread):

    on_recording_start = pyqtSignal(dict)
    on_recording_stop = pyqtSignal(dict)
    on_recording_cut = pyqtSignal(dict)

    def __init__(self, proxy_request_manager):
        super().__init__()

        self.proxy_request_manager = proxy_request_manager
        self.latest_transcript_text = ""

    def run(self):
        server = Server(self)
        server.run(debug=aipacenotes.util.is_dev())

    def _on_recording_start(self, vehicle_pos):
        logging.debug("SeverThread._on_recording_start")
        self.on_recording_start.emit(vehicle_pos)

    def _on_recording_stop(self, vehicle_pos):
        logging.debug("SeverThread._on_recording_stop")
        self.on_recording_stop.emit(vehicle_pos)

    def _on_recording_cut(self, vehicle_pos):
        logging.debug("SeverThread._on_recording_cut")
        self.on_recording_cut.emit(vehicle_pos)

    def _on_get_transcript(self, id):
        logging.debug("SeverThread._on_get_transcript")
        return self.latest_transcript_text

    def set_latest_transcript(self, txt):
        self.latest_transcript_text = txt
