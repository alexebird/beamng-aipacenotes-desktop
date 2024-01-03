from PyQt6.QtCore import (
    pyqtSignal,
)

# from PyQt6.QtGui import (
# )

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QMenu,
    QApplication,
)

class ClickableLabel(QLabel):
    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)
        copyAction = contextMenu.addAction("Copy")

        action = contextMenu.exec(event.globalPos())

        if action == copyAction:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.text())

class StatusBarWidget(QWidget):
    updateLeftLabel = pyqtSignal(str)
    updateRightLabel = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # self.setFixedHeight(20)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.left_label = ClickableLabel("")
        self.right_label = ClickableLabel("")
        # self.statusBar().addPermanentWidget(status_label)
        # font = QFont("Monospace")
        # font.setStyleHint(QFont.StyleHint.TypeWriter)
        # self.left_label.setFont(font)

        self.layout.addWidget(self.left_label)
        self.layout.addWidget(self.right_label)

        self.updateLeftLabel.connect(self.on_update_left_label)
        self.updateRightLabel.connect(self.on_update_right_label)

    def on_update_left_label(self, txt):
        self.left_label.setText(txt)

    def on_update_right_label(self, txt):
        self.right_label.setText(txt)
