import pathlib
import os
import re
import time

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from PyQt6.QtGui import (
    QAction,
    QKeySequence,
    QColor,
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QTableWidget,
    QPushButton,
    QSplitter,
    QLabel,
    QHeaderView,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from aipacenotes.tab_pacenotes import (
    ContextMenuTreeWidget,
    TimerThread,
    TaskManager,
    PacenotesManager,
    PacenotesTreeWidgetItem,
)

from aipacenotes.tab_pacenotes import (
    statuses,
    Pacenote,
)
from aipacenotes import client as aip_client
from aipacenotes.settings import SettingsManager

import time

pacenotes_file_pattern = '*.pacenotes.json'

class Benchmark:
    def __init__(self):
        self.start_time = time.time()

    def stop(self, message):
        elapsed_time = time.time() - self.start_time
        ms = int(elapsed_time * 1000)
        print(f"{message}: {ms}ms")

class MainWindow(QMainWindow):
    
    pacenote_updated = pyqtSignal(Pacenote)

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
        self.tree.setFixedWidth(500)
        self.tree.setHeaderLabel("Pacenotes Files")
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.splitter.addWidget(self.tree)

        # Add a blank widget to the right pane
        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout(self.right_pane)
        self.splitter.addWidget(self.right_pane)

        self.pacenotes_info_label = QLabel("This is a label\nFoobar", self.right_pane)
        self.right_layout.addWidget(self.pacenotes_info_label)

        self.table = QTableWidget(0, 8)  
        self.table.setHorizontalHeaderLabels(['Status', 'Updated At', 'Pacenote', 'Audio File', 'Pacenote Name', 'Pacenotes Version Name', 'Mission ID', 'Location']) 
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

        # Managers live for the lifetime of the program so they can detect changes across pacenote file scans.
        self.settings_manager = SettingsManager()
        self.pacenotes_manager = PacenotesManager(self.settings_manager)

        self.pacenote_updated.connect(self.on_pacenote_updated)

        self.on_toggle(True)
    
    def update_pacenotes_info_label(self):
        self.pacenotes_info_label.setText(f"""
        Updating pacenotes: {self.task_manager.get_future_count()}
        """)
    
    def set_controls_label_enabled_message(self):
        self.controls_label.setText(f"Pacenotes are being updated every {self.timeout_ms / 1000} seconds.")
    
    def set_controls_label_disabled_message(self):
        self.controls_label.setText("Pacenotes are not being updated.")
    
    def set_controls_label_healthcheck_message(self):
        self.controls_label.setText("Connecting to pacenotes server...")

    def on_toggle(self, checked):
        if checked:
            self.set_controls_label_enabled_message()
            self.on_off_button.setText("On")

            # only re-load settings when enabling the timer, not every cycle.
            self.settings_manager.load()

            self.on_timer_timeout()
            self.timer_thread.enable()

            # self.on_off_button.setStyleSheet("""
            # QPushButton { background-color: green; }
            # QPushButton:pressed { background-color: green; }
            # QPushButton:checked { background-color: green; }
            # QPushButton:disabled { background-color: green; }
            # """)

        else:
            self.set_controls_label_disabled_message()
            self.on_off_button.setText("Off")
            self.timer_thread.disable()
            # self.on_off_button.setStyleSheet("background-color: red;")
    
    def on_timer_timeout(self):
        self.set_controls_label_healthcheck_message()
        # TODO call the healthcheck in a background thread.
        if not aip_client.get_healthcheck_rate_limited():
            raise RuntimeError("healthcheck error")
        self.set_controls_label_enabled_message()
        self.populate_tree()

        files = self.get_selected_pacenotes_files()
        self.pacenotes_manager.scan_pacenotes_files(files)
        filtered_pacenotes = self.get_filtered_pacenotes(files)
        sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)
        self.update_table(sorted_pacenotes)
        self.update_pacenotes_audio(filtered_pacenotes)

        self.pacenotes_manager.clean_up_orphaned_audio()
    
    def get_filtered_pacenotes(self, pacenotes_files_filter):
        return [d for d in self.pacenotes_manager.db.pacenotes if d.pacenotes_fname in pacenotes_files_filter]
    
    def sorted_pacenotes_for_table(self, pacenotes):
        def sort_fn(pacenote):
            st = pacenote.status
            status_n = -1
            if st == statuses.PN_STATUS_ERROR:
                 status_n = 0
            if st == statuses.PN_STATUS_UNKNOWN:
                status_n = 1
            elif st == statuses.PN_STATUS_UPDATING:
                status_n = 2
            elif st == statuses.PN_STATUS_NEEDS_SYNC:
                status_n = 3
            elif st == statuses.PN_STATUS_OK:
                status_n = 4
            else:
                status_n = 5

            return (status_n, -pacenote.updated_at)

        return sorted(pacenotes, key=sort_fn)
    
    # If anything is selected in the tree, only include those pacenotes files.
    def get_selected_pacenotes_files(self):
        # return ['C:\\Users\\bird\\AppData\\Local\\BeamNG.drive\\0.29\\gameplay\\missions\\jungle_rock_island\\timeTrial\\jri_road_race-procedural\\pacenotes.pacenotes.json']
        # return ['C:\\Users\\bird\\AppData\\Local\\BeamNG.drive\\0.29\\gameplay\\missions\\jungle_rock_island\\timeTrial\\aip-island-loop\\pacenotes.pacenotes.json']
        selected_items = self.tree.selectedItems()
        selected_item_path = None

        search_paths = []

        if len(selected_items) > 1:
            print(f"tree widget multi-select is not supported yet")
        elif len(selected_items) == 1:
            selected_item_path = selected_items[0].full_path
            search_paths.append(selected_item_path)
        else:
            search_paths = self.settings_manager.get_pacenotes_search_paths()

        pacenotes_files = []
        for search_path in search_paths:
            if os.path.isfile(search_path):
                pacenotes_files.append(search_path)
            else:
                paths = pathlib.Path(search_path).rglob(pacenotes_file_pattern)
                for e in paths:
                    pacenotes_files.append(str(e))
        
        return pacenotes_files


    def update_pacenotes_audio(self, pacenotes):
        # print("update_pacenotes:", threading.current_thread().name)

        for pn in pacenotes:
            if pn.status == statuses.PN_STATUS_NEEDS_SYNC:
                pn.network_status = statuses.PN_STATUS_UPDATING
                pn.touch()
                self.task_manager.submit(self.update_pacenote, pn.id)

    def update_pacenote(self, pnid):
        pacenote = self.pacenotes_manager.db.select(pnid)
        print(f"update_pacenote '{pacenote.note_text}'")

        response = aip_client.post_create_pacenotes_audio(pacenote)

        if response.status_code == 200:
            audio_path = pacenote.audio_path

            version_path = os.path.dirname(audio_path)
            if not os.path.exists(version_path):
                pacenotes_path = os.path.dirname(version_path)
                if not os.path.exists(pacenotes_path):
                    os.mkdir(pacenotes_path)
                os.mkdir(version_path)

            with open(audio_path, 'wb') as f:
                f.write(response.content)

            pacenote.clear_dirty()
            pacenote.touch()
            pacenote.network_status = None
            pacenote.filesystem_status = statuses.PN_STATUS_OK

            print(f"wrote audio file: {audio_path}")
        else:
            print(f"request failed with status code {response.status_code}")
            pacenote.clear_dirty()
            pacenote.network_status = statuses.PN_STATUS_ERROR

        res = f"pacenote updated '{pacenote.note_text}'"
        print(res)

        self.pacenote_updated.emit(pacenote)
        return res

    def on_tree_item_clicked(self, item, column):
        print(f'Item clicked: {item.full_path}')
    
    def on_pacenote_updated(self, pacenote):
        # print("on_pacenote_updated:", threading.current_thread().name)
        print('pacenote updated!!!')
        self.task_manager.gc_finished()
        self.update_pacenotes_info_label()

        files = self.get_selected_pacenotes_files()
        filtered_pacenotes = self.get_filtered_pacenotes(files)
        sorted_pacenotes = self.sorted_pacenotes_for_table(filtered_pacenotes)

        self.update_table(sorted_pacenotes)
    
    def update_table(self, data):
        self.table.setRowCount(0)
        
        for i, pacenote in enumerate(data):
            (status, updated_at, note, audio, name, version, mission, location) = self.to_table_row(pacenote)
            self.table.insertRow(i)

            status_item = QTableWidgetItem(status)
            if status == statuses.PN_STATUS_ERROR:
                status_item.setBackground(QColor(255, 0, 0))
            elif status == statuses.PN_STATUS_UPDATING:
                status_item.setBackground(QColor(255, 255, 0))
            elif status == statuses.PN_STATUS_NEEDS_SYNC:
                status_item.setBackground(QColor(0, 255, 255))
            elif status == statuses.PN_STATUS_OK:
                status_item.setBackground(QColor(0, 255, 0))
            self.table.setItem(i, 0, status_item)

            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            updated_at = time.time() - updated_at
            updated_at = int(updated_at)
            updated_at = f"{updated_at}s ago"
            item = QTableWidgetItem(updated_at)
            # item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.table.setItem(i, 1, item)

            self.table.setItem(i, 2, QTableWidgetItem(note))
            self.table.setItem(i, 3, QTableWidgetItem(audio))
            self.table.setItem(i, 4, QTableWidgetItem(name))
            self.table.setItem(i, 5, QTableWidgetItem(version))
            self.table.setItem(i, 6, QTableWidgetItem(mission))
            self.table.setItem(i, 7, QTableWidgetItem(location))

        # self.table.resizeColumnsToContents()

    def to_table_row(self, pacenote):
        row_fields = ['status', 'updated_at', 'note_text', 'audio_fname',
                      'note_name', 'version_name', 'mission_id', 'mission_location']
        row_data = [pacenote.get_data(f) for f in row_fields]
        return row_data
    
    def populate_tree(self):
        bench = Benchmark()
        selected_items = self.tree.selectedItems()
        selected_item_path = None

        if len(selected_items) > 1:
            print(f"tree widget multi-select is not supported yet")
        elif len(selected_items) == 1:
            selected_item_path = selected_items[0].full_path
        
        # print(f"tree selected_item_path={selected_item_path}")

        self.tree.clear()

        def shorten_root_path(input_string):
            pattern = r".*\\(BeamNG\.drive)"
            match = re.search(pattern, input_string)
            if match:
                last_component = match.group(1)
                return re.sub(pattern, last_component, input_string)
            return input_string

        idx = {}

        for root_path in self.settings_manager.get_pacenotes_search_paths():
            # print(f"populating tree for {root_path}")
            root_item_name = shorten_root_path(root_path)
            root_item = PacenotesTreeWidgetItem(self.tree, [root_item_name], root_path)
            idx[root_path] = root_item
            search_path = pathlib.Path(root_path)
            paths = search_path.rglob(pacenotes_file_pattern)
            pacenotes_files = []
            for e in paths:
                pacenotes_files.append(str(e))
                rel_path = e.relative_to(root_path)
                parts = pathlib.PurePath(rel_path).parts
                dir_parts = parts[:-1]
                file_part = parts[-1]
                parent_node = self.get_nested_node(idx, root_path, dir_parts)
                full_path = os.path.join(root_path, rel_path)
                file_node = PacenotesTreeWidgetItem(parent_node, [file_part], full_path)
                idx[full_path] = file_node

        self.tree.expandAll()

        if selected_item_path is not None:
            selected_item = idx[selected_item_path]
            if selected_item is not None:
                selected_item.setSelected(True)

        # bench.stop('populate_tree')
  
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