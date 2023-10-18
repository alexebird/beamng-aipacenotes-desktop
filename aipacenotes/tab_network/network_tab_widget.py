from PyQt6.QtWidgets import (
    QWidget,
)

from . import ServerThread

class NetworkTabWidget(QWidget):

    def __init__(self, settings_manager):
        super().__init__()

        self.settings_manager = settings_manager

        self.server_thread = ServerThread()
        self.server_thread.start()

        # proxy some signals to the tab's api.
        self.on_endpoint_recording_start = self.server_thread.on_recording_start
        self.on_endpoint_recording_stop = self.server_thread.on_recording_stop
        self.on_endpoint_recording_cut = self.server_thread.on_recording_cut