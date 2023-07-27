# This file was originally made following: https://www.pythonguis.com/tutorials/packaging-pyqt6-applications-windows-pyinstaller/

import sys
import os
import pathlib
import json
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import partial

import requests

from PyQt6 import (
    QtWidgets,
    QtGui,
)

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QThread,
    pyqtSignal,
)

from PyQt6.QtGui import (
    QAction,
    QKeySequence,
    QColor,
)

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QTableWidget,
    QSizePolicy,
    QMenu,
    QPushButton,
    QSplitter,
    QLabel,
    QTreeWidget,
    QHeaderView,
    QTreeWidgetItem,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

basedir = os.path.dirname(__file__)

PN_STATUS_UNKNOWN = '?'
PN_STATUS_OK = 'ok'
PN_STATUS_NEEDS_SYNC = 'needs_sync'
PN_STATUS_UPDATING = 'updating'
PN_STATUS_ERROR = 'error'

try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'com.aipacenotes.desktop.v1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

class PacenotesTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, parent_node, columns_text, full_path):
        super().__init__(parent_node, columns_text)
        self.full_path = full_path
        # print(f"node name={columns_text[0]} full_path={full_path}")

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

class TaskManager:
    def __init__(self, max_workers):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = []
    
    def get_future_count(self):
        return len(self.futures)
    
    def gc_finished(self):
        self.futures = [future for future in self.futures if not future.done()]

    def submit_pacenote(self, fn, pacenote):
        print(f"submitting pacenote '{pacenote['note_text']}'")
        future = self.executor.submit(fn, pacenote)
        future.add_done_callback(self.handle_future)
        self.futures.append(future)

    def handle_future(self, future):
        try:
            # If the job has completed and raised an exception, this
            # will re-raise the exception. If the job has not yet completed,
            # this will raise a concurrent.futures.TimeoutError.
            future.result(timeout=0)
        except TimeoutError:
            pass
        except Exception as e:
            print(f"An error occurred in a future: {e}")

    def shutdown(self):
        self.wait_for_futures()
        self.executor.shutdown()

    def wait_for_futures(self):
        return [future.result() for future in self.futures]

class ContextMenuTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item is not None:
            context_menu = QMenu(self)

            full_path = item.full_path
            action_txt = "Open in file explorer"

            if os.path.isfile(full_path):
                action_txt = "Show in file explorer"

            open_action = context_menu.addAction(action_txt)
            fn = partial(self.open_file_explorer, full_path)
            open_action.triggered.connect(fn)

            context_menu.exec(event.globalPos())
    
    def open_file_explorer(self, file_path):
        if os.path.isfile(file_path):
            file_path = os.path.dirname(file_path)
        print(f"opening {file_path}")
        os.startfile(file_path)


class MainWindow(QMainWindow):
    
    pacenote_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.resize(1200, 800)

        self.setWindowTitle("AI Pacenotes")

        # Create a menu bar
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Add action to the file menu
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+q"))
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        # Create a tab widget
        self.tab_widget = QTabWidget()

        self.controls_pane = QWidget()
        stylesheet = """
        QWidget#ControlsPane {
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        self.controls_pane.setStyleSheet(stylesheet)
        self.controls_pane.setObjectName('ControlsPane')
        self.controls_pane.setFixedHeight(75)
        self.controls_layout = QHBoxLayout()
        self.controls_pane.setLayout(self.controls_layout)

        self.on_off_button = QPushButton()
        self.on_off_button.setCheckable(True)
        self.on_off_button.setChecked(True)
        self.on_off_button.setFixedHeight(50)
        self.on_off_button.setFixedWidth(50)
        self.on_off_button.toggled.connect(self.on_toggle)
        self.controls_layout.addWidget(self.on_off_button)

        self.controls_label = QLabel("", self.controls_pane)
        self.controls_layout.addWidget(self.controls_label)

        # Create a splitter to divide the tab into two panes
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Add a QTreeWidget to the left pane
        self.tree = ContextMenuTreeWidget()
        self.tree.setFixedWidth(400)
        self.tree.setHeaderLabel("Pacenotes Files")
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.splitter.addWidget(self.tree)

        # Add a blank widget to the right pane
        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout(self.right_pane)
        self.splitter.addWidget(self.right_pane)

        self.pacenotes_info_label = QLabel("This is a label\nFoobar", self.right_pane)
        self.right_layout.addWidget(self.pacenotes_info_label)

        self.table = QTableWidget(0, 7)  
        self.table.setHorizontalHeaderLabels(['Status', 'Pacenote', 'Audio File', 'Pacenote Name', 'Pacenotes Version Name', 'Mission ID', 'Location']) 
        # Set table header to stretch to the size of the window

        header = self.table.horizontalHeader()       
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        stylesheet = """
        QHeaderView::section::horizontal{
            Background-color:rgb(240,240,240);
            border-radius:14px;
            border-right: 1px solid rgb(130, 136, 144);
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        header.setStyleSheet(stylesheet)

        self.table.setColumnWidth(0, 75)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)
        self.right_layout.addWidget(self.table)

        # Create a widget for the first tab
        self.pacenotes_tab = QWidget()
        self.pacenotes_tab_layout = QVBoxLayout()
        self.pacenotes_tab_layout.addWidget(self.controls_pane)
        self.pacenotes_tab_layout.addWidget(self.splitter)
        self.pacenotes_tab.setLayout(self.pacenotes_tab_layout)

        # Add the first tab to the tab widget
        self.tab_widget.addTab(self.pacenotes_tab, "Pacenotes")

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

        self.timeout_ms = 1000
        self.timeout_sec = self.timeout_ms / 1000
        # self.timer_thread = TimerThread(self.timeout_ms)
        # self.timer_thread.timeout.connect(self.on_timer_timeout)
        # self.timer_thread.start()

        self.timer_thread = TimerThread(self.timeout_sec)
        self.timer_thread.timeout.connect(self.on_timer_timeout)
        self.timer_thread.start()

        self.task_manager = TaskManager(10)
        self.update_pacenotes_info_label()

        self.pacenote_updated.connect(self.on_pacenote_updated)

        self.on_toggle(True)
    
    def update_pacenotes_info_label(self):
        self.pacenotes_info_label.setText(f"""
        Updating pacenotes: {self.task_manager.get_future_count()}
        """)

    def on_toggle(self, checked):
        # Change the button text depending on the state
        if checked:
            # TODO refresh pacenotes data when toggling ON
            self.controls_label.setText(f"Pacenotes are being updated every {self.timeout_ms / 1000} seconds.")
            self.on_off_button.setText("On")
            self.timer_thread.enable()
            # self.on_off_button.setStyleSheet("""
            # QPushButton { background-color: green; }
            # QPushButton:pressed { background-color: green; }
            # QPushButton:checked { background-color: green; }
            # QPushButton:disabled { background-color: green; }
            # """)

            self.load_pacenotes()
        else:
            self.controls_label.setText("Pacenotes are not being updated.")
            self.on_off_button.setText("Off")
            self.timer_thread.disable()
            # self.on_off_button.setStyleSheet("background-color: red;")
    
    def on_timer_timeout(self):
        # print("on_timer_timeout:", threading.current_thread().name)
        # self.task_manager.gc_finished()
        # self.update_pacenotes_info_label()
        self.clean_up_orphaned_audio(self.pacenotes_data, self.root_path)
        self.refresh_pacenotes_data()
        self.update_pacenotes_audio()
    
    def update_pacenotes_audio(self):
        # print("update_pacenotes:", threading.current_thread().name)

        for pn in self.pacenotes_data:
            # fs_status = pn['filesystem_status']
            status = pn['status']
            if status == PN_STATUS_NEEDS_SYNC:
                pn['network_status'] = PN_STATUS_UPDATING
                pn['status'] = pn['network_status']
                self.task_manager.submit_pacenote(self.update_pacenote, pn)
                # print("submitted note")

    def update_pacenote(self, pacenote):
        # print("update_pacenote:", threading.current_thread().name)
        print(f"update_pacenote '{pacenote['note_text']}'")

        url = "https://pacenotes-concurrent-mo5q6vt2ea-uw.a.run.app/pacenotes/audio/create"

        data = {
            "note_text": pacenote['note_text'],
            "voice_name": pacenote['voice_name'],
            "language_code": pacenote['language_code'],
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            audio_path = pacenote['audio_path']

            version_path = os.path.dirname(audio_path)
            if not os.path.exists(version_path):
                pacenotes_path = os.path.dirname(version_path)
                if not os.path.exists(pacenotes_path):
                    os.mkdir(pacenotes_path)
                os.mkdir(version_path)

            with open(audio_path, 'wb') as f:
                f.write(response.content)

            pacenote['network_status'] = None
            pacenote['filesystem_status'] = PN_STATUS_OK
            pacenote['status'] = pacenote['filesystem_status']

            print(f"wrote audio file: {audio_path}")
        else:
            print(f"request failed with status code {response.status_code}")
            pacenote['network_status'] = PN_STATUS_ERROR
            pacenote['status'] = pacenote['network_status']

        res = f"pacenote updated '{pacenote['note_text']}'"
        print(res)

        self.pacenote_updated.emit(pacenote)
        return res
    
    def on_pacenote_updated(self, pacenote):
        # print("on_pacenote_updated:", threading.current_thread().name)
        print('pacenote updated!!!')
        self.task_manager.gc_finished()
        self.update_pacenotes_info_label()
        self.refresh_pacenotes_data()
    
    def load_pacenotes(self):
        home_dir = os.path.expanduser('~')
        ver = '0.29'
        # ver = 'latest' # TODO doesnt work
        root_path = os.path.join(home_dir, 'AppData', 'Local', 'BeamNG.drive', ver)
        self.root_path = pathlib.Path(root_path)
        self.root_path.resolve()

        # setup the tree widget
        pacenotes_files = self.populate_tree(self.root_path, '*.pacenotes.json', ver)

        # setup the table widget
        pacenotes_json = [self.load_pacenotes_file(f) for f in pacenotes_files]
        self.pacenotes_data = self.massage_pacenotes_for_table(pacenotes_json)

        self.refresh_pacenotes_data()

    def refresh_pacenotes_data(self):
        self.update_filesystem_statuses(self.pacenotes_data)
        self.pacenotes_data = self.sort_pacenotes_data(self.pacenotes_data)
        self.update_table()
    
    def clean_up_orphaned_audio(self, pacenotes_data, root_path):
        pacenote_expected_audio_files = set()
        for pacenote in pacenotes_data:
            audio_path = pacenote['audio_path']
            pacenote_expected_audio_files.add(audio_path)

        ogg_search_path = pathlib.Path(root_path)
        paths = ogg_search_path.rglob('pacenotes/*/pacenote_*.ogg')
        found_oggs = set()
        for ogg in paths:
            ogg = str(ogg)
            found_oggs.add(ogg)
        
        to_delete = found_oggs - pacenote_expected_audio_files

        for deleteme in to_delete:
            os.remove(deleteme)
            print(f"deleted {deleteme}")
    
    def sort_pacenotes_data(self, pacenotes_data):
        def sort_fn(pacenote):
            st = pacenote['status']
            if st == PN_STATUS_ERROR:
                return 0
            if st == PN_STATUS_UNKNOWN:
                return 1
            elif st == PN_STATUS_UPDATING:
                return 2
            elif st == PN_STATUS_NEEDS_SYNC:
                return 3
            elif st == PN_STATUS_OK:
                return 4
            else:
                return 5
        return sorted(pacenotes_data, key=sort_fn)
    
    def get_filesystem_status_for_pacenote(self, pacenote):
        audio_path = pacenote['audio_path']
        if os.path.isfile(audio_path):
            return PN_STATUS_OK
        else:
            return PN_STATUS_NEEDS_SYNC

    def update_filesystem_statuses(self, data):
        for pacenote in data:
            new_fs_status = self.get_filesystem_status_for_pacenote(pacenote)
            if pacenote["filesystem_status"] == PN_STATUS_OK and new_fs_status == PN_STATUS_NEEDS_SYNC:
                print(f"audio file doesnt exist: {pacenote['audio_path']}")
            pacenote["filesystem_status"] = new_fs_status
            nw_status = pacenote["network_status"]
            if nw_status is not None:
                pacenote["status"] = nw_status
            else:
                pacenote["status"] = pacenote["filesystem_status"]

        return data

    def update_table(self):
        data = self.pacenotes_data
        # Clear existing data
        self.table.setRowCount(0)
        
        for i, pacenote in enumerate(data):
            (status, note, audio, name, version, mission, location) = self.to_table_row(pacenote)
            self.table.insertRow(i)

            status_item = QTableWidgetItem(status)
            if status == PN_STATUS_ERROR:
                status_item.setBackground(QColor(255, 0, 0))
            elif status == PN_STATUS_UPDATING:
                status_item.setBackground(QColor(255, 255, 0))
            elif status == PN_STATUS_NEEDS_SYNC:
                status_item.setBackground(QColor(0, 255, 255))
            elif status == PN_STATUS_OK:
                status_item.setBackground(QColor(0, 255, 0))
            self.table.setItem(i, 0, status_item)

            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(i, 1, QTableWidgetItem(note))
            self.table.setItem(i, 2, QTableWidgetItem(audio))
            self.table.setItem(i, 3, QTableWidgetItem(name))
            self.table.setItem(i, 4, QTableWidgetItem(version))
            self.table.setItem(i, 5, QTableWidgetItem(mission))
            self.table.setItem(i, 6, QTableWidgetItem(location))

        # self.table.resizeColumnsToContents()


    # also needs to be changed in the private repo, and in the custom lua flowgraph code.
    def normalize_pacenote_text(self, input):
        # Convert the input to lower case
        input = input.lower()

        # Substitute any non-alphanumeric character with a hyphen
        input = re.sub(r'\W', '-', input)

        # Remove any consecutive hyphens
        input = re.sub(r'-+', '-', input)

        # Remove any leading or trailing hyphens
        input = re.sub(r'^-', '', input)
        input = re.sub(r'-$', '', input)

        return input
    
    def get_mission_id_from_path(self, fname):
        pattern = r"missions\\([^\\]+\\[^\\]+\\[^\\]+)"
        match = re.search(pattern, fname)

        if match:
            return match.group(1)
        else:
            raise ValueError(f"couldnt extract mission id from: {fname}")

    def get_mission_location_from_path(self, fname):
        # pattern = r"BeamNG\.drive\\\d\.\d+\\(.*)\\gameplay"
        pattern = r"BeamNG\.drive\\\d\.\d+\\(?:.*?)gameplay\\missions\\(.+)\\pacenotes.pacenotes.json"
        match = re.search(pattern, fname)
        print(f"checking for mission id: {fname}")

        if match:
            m = match.group(1)
            print(f"found: {m}")
            return m
        else:
            raise ValueError(f"couldnt extract mission id from: {fname}")
    
    def build_pacenotes_audio_file_path(self, pacenotes_json_fname, version_id, pacenote_fname):
        pacenotes_dir = os.path.dirname(pacenotes_json_fname)
        ver_str = f'version{version_id}'
        fname = os.path.join(pacenotes_dir, 'pacenotes', ver_str, pacenote_fname)
        return fname

    def massage_pacenotes_for_table(self, pacenotes_json):
        massaged = []

        for fname, single_file_json in pacenotes_json:
            # print(fname)

            mission_id = self.get_mission_id_from_path(fname)
            mission_location = self.get_mission_location_from_path(fname)

            for version in single_file_json['versions']:
                authors = version['authors']
                desc = version['description']
                version_id = version['id']
                version_installed = version['installed']
                language_code = version['language_code']
                version_name = version['name']
                voice = version['voice']
                voice_name = version['voice_name']
                pacenotes = version['pacenotes']

                for pacenote in pacenotes:
                    note_name = pacenote['name']
                    note_text = pacenote['note']
                    audio_fname = f'pacenote_{self.normalize_pacenote_text(note_text)}.ogg'
                    audio_path = self.build_pacenotes_audio_file_path(fname, version_id, audio_fname)

                    data_dict = {}
                    data_dict['mission_id'] = mission_id
                    data_dict['mission_location'] = mission_location

                    data_dict['authors'] = authors
                    data_dict['desc'] = desc
                    data_dict['version_id'] = version_id
                    data_dict['version_installed'] = version_installed
                    data_dict['language_code'] = language_code
                    data_dict['version_name'] = version_name
                    data_dict['voice'] = voice
                    data_dict['voice_name'] = voice_name
                    data_dict['pacenotes'] = pacenotes

                    data_dict['note_name'] = note_name
                    data_dict['note_text'] = note_text
                    data_dict['audio_fname'] = audio_fname
                    data_dict['audio_path'] = audio_path

                    data_dict['filesystem_status'] = PN_STATUS_UNKNOWN
                    data_dict['network_status'] = None
                    data_dict['status'] = data_dict['filesystem_status']

                    massaged.append(data_dict)
        
        return massaged
    
    def to_table_row(self, pacenote):
        row_fields = ['status', 'note_text', 'audio_fname', 'note_name', 'version_name', 'mission_id', 'mission_location']
        row_data = [pacenote[f] for f in row_fields]
        return row_data

    def load_pacenotes_file(self, fname):
        with open(fname) as f:
            return (fname, json.load(f))
    
    def populate_tree(self, root_path, pattern, root_item_name):
        self.tree.clear()
        root_item = PacenotesTreeWidgetItem(self.tree, [root_item_name], root_path)
        idx = { root_path: root_item }
        search_path = pathlib.Path(root_path)
        paths = search_path.rglob(pattern)
        pacenotes_files = []
        for e in paths:
            pacenotes_files.append(str(e))
            rel_path = e.relative_to(root_path)
            parts = pathlib.PurePath(rel_path).parts
            dir_parts = parts[:-1]
            file_part = parts[-1]
            node = self.get_nested_node(idx, root_path, dir_parts)
            file_node = PacenotesTreeWidgetItem(node, [file_part], os.path.join(root_path, rel_path))

        self.tree.expandAll()

        return pacenotes_files
    
    def get_nested_node(self, idx, root_path, names):
        node = self.get_node(idx, None, root_path, root_path)
        names_so_far = []
        for name in names:
            names_so_far.append(name)
            idx_key = self.make_idx_key(root_path, names_so_far)
            parent_key = self.make_idx_key(root_path, names_so_far[:-1])
            if parent_key is None:
                parent_key = root_path
            node = self.get_node(idx, parent_key, name, idx_key)
            parent_key = idx_key
        return node
    
    def make_idx_key(self, root_path, names):
        if len(names) > 0:
            return os.path.join(root_path, *names)
        else:
            return None
    
    def get_node(self, idx, parent_key, name, idx_key):
        if idx_key in idx:
            return idx[idx_key]
        elif parent_key is not None:
            idx[idx_key] = PacenotesTreeWidgetItem(idx[parent_key], [name], idx_key)
            return idx[idx_key]
        else:
            raise ValueError("parent_key is None")

    def on_tree_item_clicked(self, item, column):
        print(f'Item clicked: {item.full_path}')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icons', 'aipacenotes.ico')))
    w = MainWindow()
    app.aboutToQuit.connect(w.timer_thread.stop)
    app.aboutToQuit.connect(w.task_manager.shutdown)
    w.showMaximized()
    w.show()
    app.exec()
