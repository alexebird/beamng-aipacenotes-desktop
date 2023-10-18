from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox, QGraphicsView, QGraphicsScene

class MonitorWidget(QWidget):
    monitor_checkbox_changed = pyqtSignal(bool)

    def __init__(self):
        super(MonitorWidget, self).__init__()

        # Set maximum width
        self.setMaximumWidth(180)
        self.setMaximumHeight(50)

        # Create the layout
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Create and configure the checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(15)
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.checkbox_state_changed)
        # self.checkbox.setStyleSheet("border: 1px solid black;")
        layout.addWidget(self.checkbox)

        # Create and configure the label for "Monitor"
        self.label_monitor = QLabel("Monitor")
        self.label_monitor.setFixedWidth(50)
        # self.label_monitor.setStyleSheet("border: 1px solid black;")
        layout.addWidget(self.label_monitor)

        # Create QGraphicsView and QGraphicsScene for the red dot
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing) 
        self.graphics_view.setFixedSize(15, 15)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.graphics_view.setStyleSheet("border: 1px solid black;")
        self.graphics_view.setStyleSheet("border: none;")
        
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 15, 15)
        
        # blueBrush = QBrush(QColor(Qt.GlobalColor.blue))
        # outlinePen = QPen(Qt.GlobalColor.transparent)

        self.enabled_color = Qt.GlobalColor.blue
        self.disabled_color = Qt.GlobalColor.gray
        
        # self.scene.addEllipse(0, 0, 15, 15, outlinePen, blueBrush)
        self.dot_item = self.scene.addEllipse(0, 0, 15, 15, QPen(Qt.GlobalColor.transparent), QBrush(QColor(self.disabled_color)))
        
        self.graphics_view.setScene(self.scene)
        
        layout.addWidget(self.graphics_view)

        # Set the layout
        self.setLayout(layout)

    # def enable(self):
    #     if self.checkbox.isChecked():
    #         self.dot_item.setBrush(QBrush(QColor(self.enabled_color)))

    # def disable(self):
    #     self.dot_item.setBrush(QBrush(QColor(self.disabled_color)))

    def setMonitorState(self, on):
        if self.checkbox.isChecked() and on:
            self.dot_item.setBrush(QBrush(QColor(self.enabled_color)))
        else:
            self.dot_item.setBrush(QBrush(QColor(self.disabled_color)))

    def checkbox_state_changed(self, state):
       if state == Qt.CheckState.Checked:
           print("Checkbox is checked.")
           # Emit your custom signal here, or perform other actions
           self.monitor_checkbox_changed.emit(True)
       elif state == Qt.CheckState.Unchecked:
           print("Checkbox is unchecked.")
           # Emit your custom signal here, or perform other actions
           self.monitor_checkbox_changed.emit(False)