from functools import partial
import aipacenotes.util

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QAbstractTableModel,
)

from PyQt6.QtGui import (
    QPainter,
    QMouseEvent,
    QPainterPath,
    QColor,
    QFont,
)

from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QMenu,
    QTableView,
    QAbstractItemView,
    QApplication,
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
        self.verticalHeader().setVisible(False)
        # self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        header = self.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        stylesheet = """
        QHeaderView::section::horizontal{
            Background-color:rgb(240,240,240);
            border-radius:14px;
            border-right: 1px solid rgb(130, 136, 144);
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """
        header.setStyleSheet(stylesheet)

        # self.setItemDelegateForColumn(4, PacenoteRowControls(self.model))

        self.setItemDelegateForColumn(5, PlayButtonDelegate())
        self.itemDelegateForColumn(5).buttonClicked.connect(self.playClicked)

    def showContextMenu(self, position):
        index = self.indexAt(position)
        row = index.row()

        globalPos = self.mapToGlobal(position)
        menu = QMenu()
        menu.addAction("Open explorer", partial(self.context_menu_action_open_explorer, row))
        menu.addAction("Copy audio file path", partial(self.context_menu_action_copy_audio_file_path, row))
        menu.addAction("Force re-generate audio file", partial(self.context_menu_action_force_regen, row))

        menuSize = menu.sizeHint()
        globalPos.setY(globalPos.y() + int(menuSize.height()/2))
        menu.exec(globalPos)

    def context_menu_action_open_explorer(self, row):
        pacenote = self.get_pacenote_at_row(row)
        if pacenote:
            aipacenotes.util.open_file_explorer(pacenote.pacenotes_dir())

    def context_menu_action_copy_audio_file_path(self, row):
        pacenote = self.get_pacenote_at_row(row)
        if pacenote:
            QApplication.clipboard().setText(pacenote.note_abs_path())

    def context_menu_action_force_regen(self, row):
        pacenote = self.get_pacenote_at_row(row)
        if pacenote:
            pacenote.delete_audio_file()

    def get_pacenote_at_row(self, row):
        notebook_file = self.model().notebook_file
        notebook = notebook_file.notebook()
        if notebook:
            return notebook.pacenotes()[row]
        else:
            return None

    def playClicked(self, row):
        # print(f"Play button clicked on row {row}")
        self.play_clicked.emit(row)

class NotebookTableModel(QAbstractTableModel):
    headers = ['file?', 'note', 'language', 'codriver', 'name', 'fname']

    def __init__(self):
        super(NotebookTableModel, self).__init__()
        self.notebook_file = None
        self.notebook = None

    def setNotebookFile(self, notebook_file):
        self.notebook_file = notebook_file
        if self.notebook_file is None:
            self.notebook = None
        else:
            self.notebook = self.notebook_file.notebook()

    def rowCount(self, parent=None):
        if self.notebook:
            return len(self.notebook)
        else:
            return 0

    def columnCount(self, parent=None):
        return len(self.headers)

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
                    return repr(pacenote.note())[1:-1]
                elif index.column() == 2:
                    return f'{pacenote.language()} ({pacenote.voice()})'
                elif index.column() == 3:
                    return pacenote.codriver_name()
                elif index.column() == 4:
                    return pacenote.name()
                elif index.column() == 5:
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

        if role == Qt.ItemDataRole.FontRole:
            if self.notebook:
                pacenote = self.notebook.pacenotes()[index.row()]
                if index.column() == 0:
                    font = QFont()
                    font.setBold(True)
                    return font

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if self.notebook:
                pacenote = self.notebook.pacenotes()[index.row()]
                if index.column() == 0:
                    return Qt.AlignmentFlag.AlignCenter

        return None

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.headers[section]
