# This file was originally made following: https://www.pythonguis.com/tutorials/packaging-pyqt6-applications-windows-pyinstaller/

import sys
import os
import logging
import datetime
import numba

from PyQt6 import QtGui
from PyQt6.QtWidgets import QApplication

from aipacenotes.main_window import MainWindow

# set the windows process' id in order to get the desired task bar icon.
def set_windows_app_id():
    try:
        from ctypes import windll  # Only exists on Windows.
        myappid = 'com.aipacenotes.desktop.v1'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

def exception_hook(exc_type, exc_value, exc_traceback):
   logging.error(
       "Uncaught exception",
       exc_info=(exc_type, exc_value, exc_traceback)
   )
   sys.exit()

def set_up_logger():
    print(f"AIP_DEV is {is_dev()}")

    numba_logger = logging.getLogger('numba')
    numba_logger.setLevel(logging.WARNING)

    if is_dev():
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
        date_time_obj = datetime.datetime.now()
        timestamp_str = date_time_obj.strftime("%d-%b-%Y_%H_%M_%S")

        hom = os.environ.get('HOME', os.environ.get('USERPROFILE'))
        filename = '{}/AppData/Local/BeamNG.drive/0.30/aipacenotes-crash-{}.log'.format(hom, timestamp_str)
        logging.basicConfig(filename=filename, level=logging.DEBUG)
        sys.excepthook = exception_hook

def start_app():
    set_up_logger()
    app = QApplication(sys.argv)
    basedir = os.path.dirname(__file__)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icons', 'aipacenotes.ico')))
    w = MainWindow()
    for stoppable in w.things_to_stop():
        app.aboutToQuit.connect(stoppable)
    w.showMaximized()
    w.show()
    app.exec()

def is_dev():
    return os.environ.get('AIP_DEV', 'f') == 't'

def main():
    set_windows_app_id()
    start_app()

if __name__ == '__main__':
    main()