from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QMouseEvent
from PyQt5.QtWidgets import QWidget
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.tools.base_tool import Tool


class CanvasWidget(QWidget):
    def __init__(self, project: ProjectModel, command_stack: CommandStack, parent=None):
        super().__init__(parent)
        self.project = project
        self.command_stack = command_stack
        self._zoom = 1.0
        self._tool = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)

    def sizeHint(self) -> QSize:
        return QSize(int(self.project.width * self._zoom),
                     int(self.project.height * self._zoom))

    def set_zoom(self, zoom: float):
        self._zoom = max(0.25, min(8.0, float(zoom)))
        self.updateGeometry()
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def set_tool(self, tool: Tool):
        self._tool = tool
        self.update()

    def grid_to_screen(self, col: int, row: int) -> QPoint:
        rect = self.project.tile_rect(col, row)
        return QPoint(int(rect.x() * self._zoom), int(rect.y() * self._zoom))

    def screen_to_grid(self, x: int, y: int):
        img_x = int(x / self._zoom)
        img_y = int(y / self._zoom)
        return self.project.pixel_to_tile(img_x, img_y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        scaled = self.project.image.scaled(
            int(self.project.width * self._zoom),
            int(self.project.height * self._zoom),
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation
        )
        painter.drawPixmap(0, 0, QPixmap.fromImage(scaled))

        self._draw_grid(painter)
        painter.end()

    def _draw_grid(self, painter: QPainter):
        pen = QPen(QColor(200, 200, 200, 120))
        pen.setWidth(1)
        painter.setPen(pen)

        for col in range(self.project.cols + 1):
            x = int((self.project.offset_x + col * (self.project.tile_width + self.project.gutter_x)) * self._zoom)
            painter.drawLine(x, 0, x, int(self.project.height * self._zoom))

        for row in range(self.project.rows + 1):
            y = int((self.project.offset_y + row * (self.project.tile_height + self.project.gutter_y)) * self._zoom)
            painter.drawLine(0, y, int(self.project.width * self._zoom), y)

    def mousePressEvent(self, event: QMouseEvent):
        if self._tool:
            self._tool.on_mouse_press(event, self)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._tool:
            self._tool.on_mouse_move(event, self)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._tool:
            self._tool.on_mouse_release(event, self)