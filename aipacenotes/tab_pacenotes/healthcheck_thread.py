import time
import threading
import logging

from PyQt6.QtCore import (
    QThread,
    pyqtSignal,
)

from aipacenotes import client as aip_client

class HealthcheckThread(QThread):
    healthcheck_started = pyqtSignal()
    healthcheck_passed = pyqtSignal()
    healthcheck_failed = pyqtSignal()

    def __init__(self, timeout_sec):
        super().__init__()
        self.timeout_sec = timeout_sec
        self.enabled = True
        self.running = True

    def run(self):
        while self.running:
            if self.enabled:
                self.healthcheck_started.emit()
                if aip_client.get_healthcheck_rate_limited():
                    self.healthcheck_passed.emit()
                else:
                    self.healthcheck_failed.emit()
                    logging.warn("TimerThread timeout on thread:", threading.current_thread().name)

            time.sleep(self.timeout_sec)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def stop(self):
        self.running = False
