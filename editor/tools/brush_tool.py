from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QMouseEvent
from editor.tools.base_tool import Tool
from editor.commands.draw_command import DrawCommand


class BrushTool(Tool):
    """Square brush kernel of side `size`. Drags produce a single undoable stroke."""

    name = 'Brush'

    def __init__(self, color: QColor = None, size: int = 1, opacity: int = 255):
        self.color = color if color is not None else QColor(0, 0, 0)
        self.size = max(1, int(size))
        self.opacity = max(0, min(255, int(opacity)))
        # Active stroke state; None when idle.
        self._stroke: dict | None = None
        # True when `_paint_at` was invoked outside of an active stroke and
        # should commit a DrawCommand immediately.
        self._auto_commit = False

    def get_options(self) -> dict:
        return {'color': self.color, 'size': self.size, 'opacity': self.opacity}

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() != Qt.LeftButton:
            return
        self._stroke = {'old': {}, 'new': {}}
        self._auto_commit = False
        self._paint_at(canvas.project, canvas.command_stack,
                       int(event.pos().x() / canvas.zoom()),
                       int(event.pos().y() / canvas.zoom()))

    def on_mouse_move(self, event: QMouseEvent, canvas):
        if self._stroke is None:
            return
        self._paint_at(canvas.project, canvas.command_stack,
                       int(event.pos().x() / canvas.zoom()),
                       int(event.pos().y() / canvas.zoom()))

    def on_mouse_release(self, event: QMouseEvent, canvas):
        if self._stroke is None:
            return
        stroke = self._stroke
        if stroke['new']:
            cmd = DrawCommand(canvas.project, stroke['old'], stroke['new'])
            canvas.command_stack.push(cmd)
        self._stroke = None
        self._auto_commit = False

    def _paint_at(self, project, stack, x: int, y: int):
        # If called outside an active stroke, treat the stamp as a
        # single-shot command so direct unit-test / API callers still get
        # an undoable operation.
        if self._stroke is None:
            self._stroke = {'old': {}, 'new': {}}
            self._auto_commit = True

        radius = self.size // 2
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 0 <= px < project.width and 0 <= py < project.height:
                    if (px, py) not in self._stroke['old']:
                        self._stroke['old'][(px, py)] = project.image.pixel(px, py)
                    new_color = self._compute_pixel_color(project, px, py)
                    project.image.setPixel(px, py, new_color.rgba())
                    self._stroke['new'][(px, py)] = project.image.pixel(px, py)

        if self._auto_commit and self._stroke['new']:
            stack.push(DrawCommand(project,
                                   self._stroke['old'],
                                   self._stroke['new']))
            self._stroke = None
            self._auto_commit = False

    def _compute_pixel_color(self, project, px: int, py: int) -> QColor:
        """Apply opacity blending against the existing pixel (alpha additive)."""
        if self.opacity >= 255:
            return QColor(self.color)
        old = project.image.pixelColor(px, py)
        blended = QColor(old)
        blended.setRed(int((old.red() * (255 - self.opacity)
                            + self.color.red() * self.opacity) / 255))
        blended.setGreen(int((old.green() * (255 - self.opacity)
                              + self.color.green() * self.opacity) / 255))
        blended.setBlue(int((old.blue() * (255 - self.opacity)
                             + self.color.blue() * self.opacity) / 255))
        blended.setAlpha(min(255, old.alpha() + self.opacity))
        return blended