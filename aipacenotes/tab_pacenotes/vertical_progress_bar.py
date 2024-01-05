from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QBrush

class VerticalColorSegmentProgressBar(QProgressBar):
    def __init__(self, top_offset):
        super().__init__()
        self.set_segments([])
        self.top_offset = top_offset  # Top offset to start drawing segments
        self.setOrientation(Qt.Orientation.Vertical)  # Set progress bar orientation to vertical

    def calc_total(self):
        self.total = sum(number for number, color in self.segments)

    # List of [number, color] pairs
    def set_segments(self, segments):
        self.segments = segments
        self.calc_total()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        brush = QBrush()
        rect = self.rect()

        # Calculate the total height for segments by subtracting the top offset
        total_drawable_height = rect.height() - self.top_offset

        # Start drawing from the top offset position
        last_y = self.top_offset
        for number, color in self.segments:
            # Calculate height of the segment
            height = int(total_drawable_height * (number / self.total))

            # Set the brush color and draw the segment
            brush.setColor(QColor(color))
            brush.setStyle(Qt.BrushStyle.SolidPattern)
            painter.fillRect(0, last_y, rect.width(), height, brush)

            # Update the starting y position for the next segment
            last_y += height

        # Draw the text (percentage) in the center
        # progress_percentage = f"{int((self.value() / self.maximum()) * 100)}%"
        # painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, progress_percentage)
