# This file was originally made following: https://www.pythonguis.com/tutorials/packaging-pyqt6-applications-windows-pyinstaller/

import sys
import os

from PyQt6 import (
    QtGui,
)

from PyQt6.QtWidgets import (
    QApplication,
)

from aipacenotes.main_window import MainWindow

def main():
    # set the windows process' id in order to get the desired task bar icon.
    try:
        from ctypes import windll  # Only exists on Windows.
        myappid = 'com.aipacenotes.desktop.v1'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    app = QApplication(sys.argv)
    basedir = os.path.dirname(__file__)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icons', 'aipacenotes.ico')))
    w = MainWindow()
    app.aboutToQuit.connect(w.timer_thread.stop)
    app.aboutToQuit.connect(w.task_manager.shutdown)
    w.showMaximized()
    w.show()
    app.exec()

if __name__ == '__main__':
    main()