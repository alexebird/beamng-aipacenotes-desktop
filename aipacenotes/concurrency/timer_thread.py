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
        self.enabled = True
        self.running = True

    def run(self):
        while self.running:
            time.sleep(self.timeout_sec)
            if self.enabled:
                # print("TimerThread timeout on thread:", threading.current_thread().name)
                self.timeout.emit()

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
    
    def stop(self):
        self.running = False
