import time

from PyQt6.QtCore import (
    QThread,
    pyqtSignal,
)

class TimerThread(QThread):
    timeout = pyqtSignal()

    def __init__(self, timeout_sec):
        super().__init__()
        self.timeout_sec = timeout_sec

    def run(self):
        while not self.isInterruptionRequested():
            time.sleep(self.timeout_sec)
            self.timeout.emit()

    def stop(self):
        self.requestInterruption()
