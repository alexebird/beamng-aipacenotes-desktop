# This file was originally made following: https://www.pythonguis.com/tutorials/packaging-pyqt6-applications-windows-pyinstaller/

import sys
import os
import pathlib
import glob
import json
import re

import requests

from PyQt6 import (
    QtWidgets,
    QtGui,
)

from PyQt6.QtCore import Qt

from PyQt6.QtGui import (
    QAction,
    QKeySequence,
)

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QTableWidget,
    QSizePolicy,
    QSplitter,
    QLabel,
    QTreeWidget,
    QHeaderView,
    QTreeWidgetItem,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
)

basedir = os.path.dirname(__file__)

try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'com.aipacenotes.desktop.v1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

class MainWindow(QMainWindow):

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

        # Create a widget for the first tab
        self.pacenotes_tab = QWidget()
        self.pacenotes_tab_layout = QVBoxLayout()

        # Create a splitter to divide the tab into two panes
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Add a QTreeWidget to the left pane
        self.tree = QTreeWidget()
        self.tree.setFixedWidth(400)
        self.tree.setHeaderLabel("Pacenotes Files")
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.splitter.addWidget(self.tree)

        # Add a blank widget to the right pane
        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout(self.right_pane)
        self.splitter.addWidget(self.right_pane)

        self.label = QLabel("This is a label\nFoobar", self.right_pane)
        self.right_layout.addWidget(self.label)

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

        self.table.setColumnWidth(0, 100)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)
        self.right_layout.addWidget(self.table)

        # Add the splitter to the tab's layout
        self.pacenotes_tab_layout.addWidget(self.splitter)
        self.pacenotes_tab.setLayout(self.pacenotes_tab_layout)

        # Add the first tab to the tab widget
        self.tab_widget.addTab(self.pacenotes_tab, "Pacenotes")

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

        self.load_pacenotes()
    
    def load_pacenotes(self):
        home_dir = os.path.expanduser('~')
        ver = '0.29'
        # ver = 'latest' # TODO doesnt work
        root_path = os.path.join(home_dir, 'AppData', 'Local', 'BeamNG.drive', ver)
        root_path = pathlib.Path(root_path)
        root_path.resolve()

        # setup the tree widget
        pacenotes_files = self.populate_tree(root_path, '*.pacenotes.json', ver)

        # setup the table widget
        pacenotes_json = [self.load_pacenotes_file(f) for f in pacenotes_files]
        pacenotes_data = self.massage_pacenotes_for_table(pacenotes_json)
        pacenotes_data = self.update_statuses(pacenotes_data)
        self.clean_up_orphaned_audio(pacenotes_data, root_path)
        pacenotes_data = self.sort_pacenotes_data(pacenotes_data)
        self.update_table(pacenotes_data)
    
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
            if st == "needs_sync":
                return 0
            elif st == "ok":
                return 1
            else:
                return 2
        return sorted(pacenotes_data, key=sort_fn)
    
    def get_filesystem_status_for_pacenote(self, pacenote):
        audio_path = pacenote['audio_path']
        if os.path.isfile(audio_path):
            # print(f"audio file exists: {audio_path}")
            return "ok"
        else:
            print(f"audio file doesnt exist: {audio_path}")
            return "needs_sync"

    def update_statuses(self, data):
        for pacenote in data:
            new_fs_status = self.get_filesystem_status_for_pacenote(pacenote)
            pacenote["filesystem_status"] = new_fs_status
            pacenote["status"] = new_fs_status

        return data

    def update_table(self, data):
        # Clear existing data
        self.table.setRowCount(0)
        
        for i, pacenote in enumerate(data):
            (status, note, audio, name, version, mission, location) = self.to_table_row(pacenote)
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(status))
            self.table.setItem(i, 1, QTableWidgetItem(note))
            self.table.setItem(i, 2, QTableWidgetItem(audio))
            self.table.setItem(i, 3, QTableWidgetItem(name))
            self.table.setItem(i, 4, QTableWidgetItem(version))
            self.table.setItem(i, 5, QTableWidgetItem(mission))
            self.table.setItem(i, 6, QTableWidgetItem(location))

        self.table.resizeColumnsToContents()


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
        pattern = r"BeamNG\.drive\\\d\.\d+\\(.*)\\gameplay"
        match = re.search(pattern, fname)

        if match:
            return match.group(1)
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

                    data_dict['filesystem_status'] = '?'
                    data_dict['network_status'] = None
                    data_dict['status'] = '?'

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
        root_item = PacenotesTreeWidgetItem(self.tree, [root_item_name], root_item_name)
        idx = { root_item_name: root_item }
        search_path = pathlib.Path(root_path)
        paths = search_path.rglob(pattern)
        pacenotes_files = []
        for e in paths:
            pacenotes_files.append(str(e))
            rel_path = e.relative_to(root_path)
            parts = pathlib.PurePath(rel_path).parts
            dir_parts = parts[:-1]
            file_part = parts[-1]
            node = self.get_nested_node(idx, root_item_name, dir_parts)
            file_node = PacenotesTreeWidgetItem(node, [file_part], rel_path)

        self.tree.expandAll()

        return pacenotes_files
    
    def get_nested_node(self, idx, parent_name, names):
        node = self.get_node(idx, None, parent_name, parent_name)
        names_so_far = []
        for name in names:
            names_so_far.append(name)
            idx_key = self.make_idx_key(names_so_far)
            parent_key = self.make_idx_key(names_so_far[:-1])
            if parent_key is None:
                parent_key = parent_name
            node = self.get_node(idx, parent_key, name, idx_key)
            parent_key = idx_key
        return node
    
    def make_idx_key(self, names):
        if len(names) > 0:
            return os.path.join(*names)
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
        # print(f'Item clicked: {item.text(column)}')
        print(f'Item clicked: {item.full_path}')
    

class PacenotesTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, parent_node, columns_text, full_path):
        super().__init__(parent_node, columns_text)
        self.full_path = full_path
        # print(f"node name={columns_text[0]} full_path={full_path}")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icons', 'aipacenotes.ico')))
    w = MainWindow()
    w.showMaximized()
    w.show()
    app.exec()
