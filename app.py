# This file was originally made following: https://www.pythonguis.com/tutorials/packaging-pyqt6-applications-windows-pyinstaller/

import sys
import os
import logging
import datetime
import pathlib

from PyQt6 import QtGui
from PyQt6.QtWidgets import QApplication

from aipacenotes.main_window import MainWindow
import aipacenotes.settings.settings_manager
import aipacenotes.util

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


def rotate_file(file_path, max_rotation):
    if os.path.isfile(file_path):
        base, ext = os.path.splitext(file_path)  # Separate the extension from the path
        i = max_rotation - 1
        os.remove(f"{base}.{i+1}{ext}")

        while i > 0:
            src = f"{base}.{i}{ext}"
            dst = f"{base}.{i+1}{ext}"
            if os.path.isfile(src):
                os.rename(src, dst)
            i -= 1

        os.rename(file_path, f"{base}.1{ext}")

def set_up_logger():
    numba_logger = logging.getLogger('numba')
    numba_logger.setLevel(logging.WARNING)

    if aipacenotes.util.is_dev():
        print(f"AIP_DEV is {aipacenotes.util.is_dev()}")
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S%z'
        )
    else:
        # date_time_obj = datetime.datetime.now()
        # timestamp_str = date_time_obj.strftime("%d-%b-%YT%H-%M-%S")

        hom = os.environ.get('HOME', os.environ.get('USERPROFILE'))
        # fname_log = 'aipacenotes-{}.log'.format(timestamp_str)
        fname_log = 'aipacenotes.log'

        dirname_tmp = '{}/AppData/Local/BeamNG.drive/latest/temp'.format(hom)
        dirname_tmp = aipacenotes.settings_manager.expand_windows_symlinks(dirname_tmp)
        dirname_tmp = os.path.normpath(dirname_tmp)
        dirname_tmp = aipacenotes.util.normalize_path(dirname_tmp)
        pathlib.Path(dirname_tmp).mkdir(parents=False, exist_ok=True)

        dirname_aip = '{}/aipacenotes'.format(dirname_tmp)
        dirname_aip = os.path.normpath(dirname_aip)
        dirname_aip = aipacenotes.util.normalize_path(dirname_aip)
        pathlib.Path(dirname_aip).mkdir(parents=False, exist_ok=True)

        filename = '{}/{}'.format(dirname_aip, fname_log)

        rotate_file(filename, 3)

        notice_fname = filename.replace('/', '\\')

        print("")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!! NOTICE")
        print(f"!! Thank you for using my software.")
        print(f"!! If there are any errors or crashes, check the log file in the BeamNG user dir at temp/aipacenotes/.")
        print(f"!!")
        print(f"!!   log file: {notice_fname}")
        print(f"!!")
        print(f"!! DM me on the BeamNG forums. My handle is dirtwheel.")
        print(f"!!")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("")

        logging.basicConfig(
            filename=filename,
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S%z'
        )
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

def main():
    set_windows_app_id()
    start_app()

if __name__ == '__main__':
    main()
