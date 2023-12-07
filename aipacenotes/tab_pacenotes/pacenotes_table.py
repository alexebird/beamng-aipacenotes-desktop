from functools import partial

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QAbstractTableModel,
    QRect,
    QPoint
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
    QMessageBox,
    QHeaderView,
    QPushButton,
    QComboBox,
    QTableView,
    QAbstractItemView,
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

# from PyQt6.QtCore import Qt, pyqtSignal
# from PyQt6.QtWidgets import QStyledItemDelegate, QPushButton, QHBoxLayout, QWidget, QStyle
# from PyQt6.QtGui import QMouseEvent, QPainter, QPainterPath

# class PacenoteRowControls(QStyledItemDelegate):
#     playClicked = pyqtSignal(int)
#     copyClicked = pyqtSignal(int)
#     forceUpdateClicked = pyqtSignal(int)

#     def __init__(self, table_model, parent=None):
#         super(PacenoteRowControls, self).__init__(parent)
#         self.table_model = table_model

#     # def paint(self, painter, option, index):
#     #     super().paint(painter, option, index)
#     #     print('paint')

#     def createEditor(self, parent, option, index):
#         print('ce')
#         # Create QWidget and Layout
#         editor = QWidget(parent)
#         layout = QHBoxLayout(editor)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)

#         row = index.row()

#         notebook = self.table_model.notebook
#         if notebook:
#             pacenote = notebook.pacenotes()[row]

#         # Play Button
#         play_btn = QPushButton()
#         play_btn.setIcon(parent.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
#         play_btn.setToolTip("Play pacenote")
#         layout.addWidget(play_btn)
#         play_btn.clicked.connect(lambda pacenote=pacenote: self.playClicked.emit(pacenote))

#         # Copy Button
#         copy_btn = QPushButton()
#         copy_btn.setIcon(parent.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
#         copy_btn.setToolTip("Copy path to clipboard")
#         layout.addWidget(copy_btn)
#         copy_btn.clicked.connect(lambda pacenote=pacenote: self.copyClicked.emit(pacenote))

#         # Force Update Button
#         force_update_btn = QPushButton()
#         force_update_btn.setIcon(parent.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
#         force_update_btn.setToolTip("Force re-generate audio file")
#         layout.addWidget(force_update_btn)
#         force_update_btn.clicked.connect(lambda pacenote=pacenote: self.forceUpdateClicked.emit(pacenote))

#         return editor

#     def setEditorData(self, editor, index):
#         print('setEditorData')
#         # pass  # No data setting needed

#     def setModelData(self, editor, model, index):
#         print('setModelData')
#         # pass  # No data retrieval needed

#     def updateEditorGeometry(self, editor, option, index):
#         editor.setGeometry(option.rect)

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

        self.setItemDelegateForColumn(4, PlayButtonDelegate())
        self.itemDelegateForColumn(4).buttonClicked.connect(self.playClicked)

    def showContextMenu(self, position):
        index = self.indexAt(position)
        row = index.row()

        globalPos = self.mapToGlobal(position)
        menu = QMenu()
        menu.addAction("TODO - Copy audio file path", partial(self.context_menu_action_copy_audio_file_path, row))
        menu.addAction("TODO - Force re-generate audio file", partial(self.context_menu_action_force_regen, row))

        menuSize = menu.sizeHint()
        globalPos.setY(globalPos.y() + int(menuSize.height()/2))
        menu.exec(globalPos)

    def context_menu_action_copy_audio_file_path(self, row):
        print(f"Option 1 selected for row {row}")

    def context_menu_action_force_regen(self, row):
        print(f"Option 2 selected for row {row}")

    def playClicked(self, row):
        print(f"Play button clicked on row {row}")
        self.play_clicked.emit(row)

class NotebookTableModel(QAbstractTableModel):
    headers = ['file?', 'note', 'language', 'name', 'fname']

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
        return 5

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
                    return f'{pacenote.language()} ({pacenote.voice()})'
                elif index.column() == 3:
                    return pacenote.name()
                elif index.column() == 4:
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
