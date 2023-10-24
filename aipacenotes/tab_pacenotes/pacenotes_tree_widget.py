import os
from functools import partial

from PyQt6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
)

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)

from .rally_file_scanner import RallyFileScanner, SearchPath
from .rally_file import Notebook, RallyFile

class PacenotesTreeWidget(QTreeWidget):
    notebookSelectionChanged = pyqtSignal(Notebook)

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setColumnCount(1)
        self.setHeaderLabels(["Pacenotes"])
        self.itemClicked.connect(self.on_tree_item_clicked)

    def populate(self):
        rally_scanner = RallyFileScanner(self.settings_manager)
        rally_scanner.scan()
        root_items = []
        for search_path in rally_scanner.search_paths:
            item_search_path = QTreeWidgetItem([str(search_path.fname)])
            item_search_path.setData(0, Qt.ItemDataRole.UserRole, search_path)
            for rally_file in search_path.rally_files:
                child_rally_file = QTreeWidgetItem([str(rally_file)])
                child_rally_file.setData(0, Qt.ItemDataRole.UserRole, rally_file)
                item_search_path.addChild(child_rally_file)
                for notebook in rally_file.notebooks():
                    child_notebook = QTreeWidgetItem([notebook.name()])
                    child_notebook.setData(0, Qt.ItemDataRole.UserRole, notebook)
                    child_rally_file.addChild(child_notebook)
            root_items.append(item_search_path)

        # self.clear()
        self.insertTopLevelItems(0, root_items)
        self.expandAll()

    def select_default(self):
        first_item = self.topLevelItem(0)
        if first_item:
            if first_item.childCount() > 0:
                child = first_item.child(0)
                if child.childCount() > 0:
                    notebook_item = child.child(0)
                    self.setCurrentItem(notebook_item)
                    notebook = notebook_item.data(0, Qt.ItemDataRole.UserRole)
                    self.notebookSelectionChanged.emit(notebook)

    def on_tree_item_clicked(self, current_item):
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
        notebook_item = None
        # notebook = None
        if isinstance(item_data, RallyFile):
            if current_item.childCount() > 0:
                notebook_item = current_item.child(0)
                self.setCurrentItem(notebook_item)
        elif isinstance(item_data, SearchPath):
            if current_item.childCount() > 0:
                child = current_item.child(0)
                if child.childCount() > 0:
                    notebook_item = child.child(0)
                    self.setCurrentItem(notebook_item)
        elif isinstance(item_data, Notebook):
            notebook_item = current_item

        notebook = notebook_item.data(0, Qt.ItemDataRole.UserRole)
        if notebook:
            self.notebookSelectionChanged.emit(notebook)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item is not None:
            context_menu = QMenu(self)
            user_data = item.data(0, Qt.ItemDataRole.UserRole)

            full_path = user_data.file_explorer_path()
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