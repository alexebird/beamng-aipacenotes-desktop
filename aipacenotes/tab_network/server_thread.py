import time
import threading

from PyQt6.QtCore import (
    QThread,
    pyqtSignal,
)

from aipacenotes import client as aip_client
from aipacenotes.server import Server

class ServerThread(QThread):

    on_recording_start = pyqtSignal()
    on_recording_stop = pyqtSignal()
    on_recording_cut = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        server = Server(self)
        server.run(debug=True)
    
    def _on_recording_start(self):
        print("SeverThread._on_recording_start")
        self.on_recording_start.emit()

    def _on_recording_stop(self):
        print("SeverThread._on_recording_stop")
        self.on_recording_stop.emit()
 
    def _on_recording_cut(self):
        print("SeverThread._on_recording_cut")
        self.on_recording_cut.emit()