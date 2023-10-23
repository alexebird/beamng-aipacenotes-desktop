from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QAbstractTableModel,
    QRect,
    QPoint
)

from PyQt6.QtGui import QPainter, QMouseEvent, QPainterPath, QColor

from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QMessageBox,
    QHeaderView,
    QPushButton,
    QComboBox,
    QTableView,
    QLabel,
    QWidget,
    QVBoxLayout,
)

class PlayButtonDelegate(QStyledItemDelegate):
    buttonClicked = pyqtSignal(int)

    def paint(self, painter: QPainter, option, index):
        tri_width = 20
        padding = 5
        rect = option.rect

        # Enable anti-aliasing
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Define square box dimensions
        square_side = tri_width-5
        square_x = rect.left() + 5
        square_y = rect.top() + (rect.height() - square_side) // 2

        # Draw the square box
        # painter.setBrush(Qt.GlobalColor.white)
        # square_rect = QRect(square_x, square_y, square_side, square_side)
        # painter.drawRect(square_rect)

        # Draw the sideways triangle within the square box
        painter.setBrush(Qt.GlobalColor.blue)
        path = QPainterPath()
        path.moveTo(square_x, square_y)
        path.lineTo(square_x + square_side, square_y + square_side // 2)
        path.lineTo(square_x, square_y + square_side)
        path.lineTo(square_x, square_y)
        painter.drawPath(path)

        option.rect.setLeft(option.rect.left() + tri_width + padding)

        super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if isinstance(event, QMouseEvent):
            if event.type() == QMouseEvent.Type.MouseButtonRelease:
                if option.rect.contains(event.pos()):
                    self.buttonClicked.emit(index.row())
                    return True
        return False

class NotebookTable(QTableView):
    play_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setItemDelegateForColumn(3, PlayButtonDelegate())
        self.itemDelegateForColumn(3).buttonClicked.connect(self.playClicked)

    def playClicked(self, row):
        print(f"Play button clicked on row {row}")
        self.play_clicked.emit(row)

class NotebookTableModel(QAbstractTableModel):
    headers = ['file?', 'note', 'name', 'fname']

    def __init__(self):
        super(NotebookTableModel, self).__init__()
        self.notebook = None
    
    def setNotebook(self, notebook):
        self.notebook = notebook

    def rowCount(self, parent=None):
        if self.notebook:
            return len(self.notebook)
        else:
            return 0

    def columnCount(self, parent=None):
        return 4

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if self.notebook:
                pacenote = self.notebook.pacenotes()[index.row()]
                if index.column() == 0:
                    if pacenote.note_file_exists():
                        return 'yes'
                    else:
                        return 'no'
                elif index.column() == 1:
                    return pacenote.note()
                elif index.column() == 2:
                    return pacenote.name()
                elif index.column() == 3:
                    return pacenote.note_basename()
            else:
                return None

        if role == Qt.ItemDataRole.BackgroundRole:
            if self.notebook:
                pacenote = self.notebook.pacenotes()[index.row()]
                if index.column() == 0:
                    if pacenote.note_file_exists():
                        return QColor(Qt.GlobalColor.green)
                    else:
                        return QColor(Qt.GlobalColor.red)
        
        return None
    
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.headers[section]