import aipacenotes.util

from PyQt6.QtCore import (
    Qt,
    QEvent,
)

from PyQt6.QtWidgets import (
    QTableView,
    QAbstractItemView,
    QToolTip,
)

from .proxy_request import headers

class RequestsTable(QTableView):
    def __init__(self):
        super().__init__()
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # header = self.horizontalHeader()
        # stylesheet = """
        # QHeaderView::section::horizontal{
        #     Background-color:rgb(240,240,240);
        #     border-radius:14px;
        #     border-right: 1px solid rgb(130, 136, 144);
        #     border-bottom: 1px solid rgb(130, 136, 144);
        # }
        # """
        # header.setStyleSheet(stylesheet)


    def setColumnWidths(self):
        for i,hdr in enumerate(headers):
            self.setColumnWidth(i, hdr['width'])

    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            globalPos = event.globalPos()
            pos = self.viewport().mapFromGlobal(globalPos)
            index = self.indexAt(pos)

            if index.isValid():
                # Assuming the tooltip text is stored in a specific column, e.g., column 1
                tooltip_text = self.model().tooltip(index)
                QToolTip.showText(globalPos, tooltip_text)
            else:
                QToolTip.hideText()
                event.ignore()
        return super().event(event)
