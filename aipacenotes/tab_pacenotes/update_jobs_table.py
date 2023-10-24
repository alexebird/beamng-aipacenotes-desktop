import time

from PyQt6.QtCore import (
    Qt,
    QAbstractTableModel,
)

from PyQt6.QtGui import (
    QColor,
    QFont,
)

from PyQt6.QtWidgets import (
    QTableView,
    QAbstractItemView,
)

from .update_jobs import (
    pacenote_job_id,
    UPDATE_JOB_STATUS_UPDATING,
    UPDATE_JOB_STATUS_SUCCESS,
    UPDATE_JOB_STATUS_ERROR,
)

class UpdateJobsTable(QTableView):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader().setStyleSheet("""
        QHeaderView::section::horizontal{
            Background-color:rgb(240,240,240);
            border-radius:14px;
            border-right: 1px solid rgb(130, 136, 144);
            border-bottom: 1px solid rgb(130, 136, 144);
        }
        """)

class UpdateJobsTableModel(QAbstractTableModel):
    headers = ['status', 'updated', 'note', 'fname', 'notebook', 'pacenote']

    def __init__(self, jobs_store):
        super(UpdateJobsTableModel, self).__init__()
        self.jobs_store = jobs_store

    def rowCount(self, parent=None):
        return len(self.jobs_store)

    def columnCount(self, parent=None):
        return 6

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            job = self.jobs_store.get(index.row())
            pacenote = job.pacenote

            if index.column() == 0:
                return job.status()
            elif index.column() == 1:
                return job._cached_updated_at_str
            elif index.column() == 2:
                return pacenote.note()
            elif index.column() == 3:
                return pacenote.note_basename()
            elif index.column() == 4:
                return pacenote.notebook.name()
            elif index.column() == 5:
                return pacenote_job_id(pacenote)
            else:
                return None

        if role == Qt.ItemDataRole.BackgroundRole:
            job = self.jobs_store.get(index.row())
            # pacenote = job.pacenote

            if index.column() == 0:
                if job.status() == UPDATE_JOB_STATUS_UPDATING:
                    return QColor(Qt.GlobalColor.cyan)
                elif job.status() == UPDATE_JOB_STATUS_SUCCESS:
                    return QColor(Qt.GlobalColor.green)
                elif job.status() == UPDATE_JOB_STATUS_ERROR:
                    return QColor(Qt.GlobalColor.red)
        
        if role == Qt.ItemDataRole.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setBold(True)
                return font

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 0:
                return Qt.AlignmentFlag.AlignCenter
        
        return None
    
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.headers[section]