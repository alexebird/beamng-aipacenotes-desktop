from PyQt6.QtCore import (
    Qt,
    QAbstractTableModel,
)

from .proxy_request import headers

class RequestsTableModel(QAbstractTableModel):

    def __init__(self, proxy_requests_manager):
        super(RequestsTableModel, self).__init__()
        self.proxy_requests_manager = proxy_requests_manager

    def rowCount(self, parent=None):
        return len(self.proxy_requests_manager)

    def columnCount(self, parent=None):
        return len(headers)

    def data(self, index, role):
        if not index.isValid():
            return None

        proxy_request = self.proxy_requests_manager[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return proxy_request.cols(index.column())

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return headers[section]['name']

    def tooltip(self, index):
        proxy_request = self.proxy_requests_manager[index.row()]
        return proxy_request.response_body_tooltip_text()
