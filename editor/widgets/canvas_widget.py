from PyQt5.QtCore import Qt, QPoint, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QMouseEvent, QImage
from PyQt5.QtWidgets import QWidget
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.commands.paste_command import PasteCommand
from editor.tools.base_tool import Tool


class CanvasWidget(QWidget):
    # Emits (col, row) of the tile under the cursor, or (-1, -1) when the
    # cursor is not over a tile (gutter, offset margin, outside canvas).
    mouse_moved = pyqtSignal(int, int)

    def __init__(self, project: ProjectModel, command_stack: CommandStack, parent=None):
        super().__init__(parent)
        self.project = project
        self.command_stack = command_stack
        self._zoom = 1.0
        self._tool = None
        # Paste preview state. When `_paste_image` is not None the widget
        # is in "place paste" mode: it draws a half-opacity preview that
        # snaps to the grid and pushes a PasteCommand on click.
        self._paste_image: QImage = None
        self._paste_pos: QPoint = None  # image-space (not screen-space)
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

    # --- Paste preview -----------------------------------------------------

    def set_paste_image(self, image: QImage):
        """Enter paste mode with a freshly copied tile block. Resets the
        preview position to the origin so the user sees the preview until
        they move the mouse.
        """
        self._paste_image = QImage(image) if image is not None else None
        self._paste_pos = QPoint(0, 0)
        self.update()

    def _snap_to_grid(self, img_x: int, img_y: int) -> QPoint:
        """Map an image-space pixel coordinate to the top-left corner of the
        tile it falls into, clamped to valid canvas tile indices.
        """
        col = max(0, min(self.project.cols - 1, img_x // self.project.tile_width))
        row = max(0, min(self.project.rows - 1, img_y // self.project.tile_height))
        rect = self.project.tile_rect(col, row)
        return QPoint(rect.x(), rect.y())

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
        self._draw_paste_preview(painter)
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

    def _draw_paste_preview(self, painter: QPainter):
        if self._paste_image is None or self._paste_pos is None:
            return
        x = int(self._paste_pos.x() * self._zoom)
        y = int(self._paste_pos.y() * self._zoom)
        w = int(self._paste_image.width() * self._zoom)
        h = int(self._paste_image.height() * self._zoom)
        painter.setOpacity(0.5)
        painter.drawPixmap(
            x, y,
            QPixmap.fromImage(self._paste_image.scaled(
                w, h, Qt.IgnoreAspectRatio, Qt.FastTransformation)),
        )
        painter.setOpacity(1.0)

    # --- Mouse events ------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        # Paste mode takes priority over active tools: a click places the
        # pending paste image at the snapped tile origin.
        if self._paste_image is not None and event.button() == Qt.LeftButton:
            img_x = int(event.pos().x() / self._zoom)
            img_y = int(event.pos().y() / self._zoom)
            snapped = self._snap_to_grid(img_x, img_y)
            cmd = PasteCommand(self.project, self._paste_image,
                               snapped.x(), snapped.y())
            self.command_stack.push(cmd)
            self._paste_image = None
            self._paste_pos = None
            self.update()
            return
        if self._tool:
            self._tool.on_mouse_press(event, self)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        tile = self.screen_to_grid(event.pos().x(), event.pos().y())
        if tile is not None:
            self.mouse_moved.emit(tile[0], tile[1])
        else:
            self.mouse_moved.emit(-1, -1)
        if self._paste_image is not None:
            img_x = int(event.pos().x() / self._zoom)
            img_y = int(event.pos().y() / self._zoom)
            self._paste_pos = self._snap_to_grid(img_x, img_y)
            self.update()
            return
        if self._tool:
            self._tool.on_mouse_move(event, self)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        # If we still have a paste image, the user released without clicking
        # the canvas (e.g. cancelled with right-click elsewhere). Only the
        # active tool handles releases during paste mode.
        if self._tool and self._paste_image is None:
            self._tool.on_mouse_release(event, self)