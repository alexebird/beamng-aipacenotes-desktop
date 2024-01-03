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

from .rally_file_scanner import RallyFileScanner
from .rally_file import NotebookFile
import aipacenotes.util

class PacenotesTreeWidget(QTreeWidget):
    notebookSelectionChanged = pyqtSignal(NotebookFile)

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setColumnCount(1)
        self.setHeaderLabels(["Pacenotes"])
        self.itemClicked.connect(self.on_tree_item_clicked)
        # self.currentItemChanged.connect(self.on_current_item_changed)

    def populate(self):
        rally_scanner = RallyFileScanner(self.settings_manager)
        rally_scanner.scan()

        root_items = []
        for search_path in rally_scanner.search_paths:
            item_search_path = QTreeWidgetItem([str(search_path)])
            item_search_path.setData(0, Qt.ItemDataRole.UserRole, search_path)
            root_items.append(item_search_path)

            for rally_file in search_path.rally_files:
                item_text = str(rally_file).removeprefix(str(search_path))
                child_rally_file = QTreeWidgetItem([item_text])
                child_rally_file.setData(0, Qt.ItemDataRole.UserRole, rally_file)
                item_search_path.addChild(child_rally_file)

        self.insertTopLevelItems(0, root_items)

    def on_tree_item_clicked(self, current_item):
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(item_data, NotebookFile):
            notebook_file = item_data
            self.notebookSelectionChanged.emit(notebook_file)

    # def on_current_item_changed(self, current_item, previous):
    #     print("foo")
    #     if previous is not None and current_item is None:
    #         # The previous item was deselected, and nothing is selected now
    #         print(f"Item deselected (Ctrl+Click): {previous.text(0)}")

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
            fn = partial(aipacenotes.util.open_file_explorer, full_path)
            open_action.triggered.connect(fn)

            context_menu.exec(event.globalPos())
