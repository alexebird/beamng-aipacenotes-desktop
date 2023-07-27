import os
from functools import partial

from PyQt6.QtWidgets import (
    QMenu,
    QTreeWidget,
)

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