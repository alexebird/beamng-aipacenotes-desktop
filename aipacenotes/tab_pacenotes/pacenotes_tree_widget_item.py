from PyQt6.QtWidgets import (
    QTreeWidgetItem,
)

class PacenotesTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, parent_node, columns_text, full_path):
        super().__init__(parent_node, columns_text)
        self.full_path = full_path
        # print(f"node name={columns_text[0]} full_path={full_path}")
