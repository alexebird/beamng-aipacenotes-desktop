from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QColor,
    QBrush,
    QPen,
    QPainter,
)
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QSizePolicy,
    QLabel,
    QGraphicsView,
    QGraphicsScene,
)

class DotWidget(QWidget):
    def __init__(self, on_color, on_text, off_text):
        super(DotWidget, self).__init__()

        self.on = False

        self.on_color = on_color
        self.off_color = Qt.GlobalColor.gray
        self.on_text = on_text
        self.off_text = off_text

        # Set maximum width
        self.setMaximumWidth(200)
        self.setMaximumHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        # Create the layout
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Create QGraphicsView and QGraphicsScene for the red dot
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setFixedSize(15, 15)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setStyleSheet("border: none;")
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 15, 15)
        self.dot_item = self.scene.addEllipse(0, 0, 15, 15,
                                              QPen(Qt.GlobalColor.transparent),
                                              QBrush(QColor(self.off_color)))
        self.graphics_view.setScene(self.scene)
        layout.addWidget(self.graphics_view)

        # Create and configure the label for "Monitor"
        self.label_monitor = QLabel(self.off_text)
        self.label_monitor.setFixedWidth(150)
        layout.addWidget(self.label_monitor)

        # Set the layout
        self.setLayout(layout)

    def setState(self, on):
        self.on = on
        if self.on:
            self.dot_item.setBrush(QBrush(QColor(self.on_color)))
            self.label_monitor.setText(self.on_text)
        else:
            self.dot_item.setBrush(QBrush(QColor(self.off_color)))
            self.label_monitor.setText(self.off_text)

    def getState(self):
        return self.on
