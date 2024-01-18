from PyQt6.QtCore import (
    QThread,
    pyqtSignal,
)

import logging
from aipacenotes.server import Server
import aipacenotes.util

class ServerThread(QThread):

    on_recording_start = pyqtSignal()
    on_recording_stop = pyqtSignal(bool)
    on_recording_cut = pyqtSignal(dict)

    def __init__(self, proxy_request_manager):
        super().__init__()

        self.proxy_request_manager = proxy_request_manager
        self.transcript_store = None
        self.transcribe_tab = None

    def set_transcript_store(self, transcript_store):
        self.transcript_store = transcript_store

    def set_transcribe_tab(self, transcribe_tab):
        self.transcribe_tab = transcribe_tab

    def run(self):
        server = Server(self)
        server.run(debug=aipacenotes.util.is_dev())

    def _on_recording_start(self):
        logging.debug("SeverThread._on_recording_start")
        self.on_recording_start.emit()

    def _on_recording_stop(self, create_entry):
        logging.debug("SeverThread._on_recording_stop")
        self.on_recording_stop.emit(create_entry)

    def _on_recording_cut(self, vehicle_data):
        logging.debug("SeverThread._on_recording_cut")
        self.on_recording_cut.emit(vehicle_data)

    def get_transcripts(self, count):
        # logging.debug("SeverThread.get_transcripts")
        if not self.transcript_store:
            logging.warn("SeverThread.get_transcripts: transcript_store is None")
            return []

        count = int(count)
        return [t.as_json_for_recce_app() for t in self.transcript_store.get_latest(count)]

    # def _on_get_transcript(self, id):
    #     logging.debug("SeverThread._on_get_transcript")
    #     return self.latest_transcript_text

    # def set_latest_transcript(self, txt):
    #     self.latest_transcript_text = txt
