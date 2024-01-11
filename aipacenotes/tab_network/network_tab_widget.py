from PyQt6.QtCore import (
    pyqtSignal,
)

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)

from aipacenotes.concurrency import TaskManager, TimerThread
from .server_thread import ServerThread
from .requests_table import RequestsTable
from .requests_table_model import RequestsTableModel
from .proxy_request_manager import ProxyRequestManager

class NetworkTabWidget(QWidget):

    proxy_request = pyqtSignal()

    def __init__(self, settings_manager):
        super().__init__()

        self.settings_manager = settings_manager

        self.proxy_request_manager = ProxyRequestManager(self.proxy_request)

        self.server_thread = ServerThread(self.proxy_request_manager)
        self.server_thread.start()

        self.task_manager = TaskManager(10)
        self.timer_thread = TimerThread(0.5)
        self.timer_thread.timeout.connect(self.on_timer_timeout)

        # proxy some signals to the tab class' public api.
        self.on_endpoint_recording_start = self.server_thread.on_recording_start
        self.on_endpoint_recording_stop = self.server_thread.on_recording_stop
        self.on_endpoint_recording_cut = self.server_thread.on_recording_cut

        self.proxy_request.connect(self.on_proxy_request)

        self.requests_table_model = RequestsTableModel(self.proxy_request_manager)
        self.requests_table = RequestsTable()
        self.requests_table.setModel(self.requests_table_model)
        self.requests_table.setColumnWidths()

        vbox = QVBoxLayout()
        vbox.addWidget(self.requests_table)
        self.setLayout(vbox)

    def on_proxy_request(self):
        self.requests_table_model.layoutChanged.emit()
        self.task_manager.submit(self.proxy_request_manager.run)

    def on_timer_timeout(self):
        pass
        # self.task_manager.submit(self.refresh_pacenotes)
