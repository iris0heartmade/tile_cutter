from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QMouseEvent
from editor.tools.base_tool import Tool
from editor.commands.draw_command import DrawCommand


class BrushTool(Tool):
    """Square brush kernel of side `size`. Drags produce a single undoable stroke."""

    name = '画笔'

    def __init__(self, color: QColor = None, size: int = 1, opacity: int = 255,
                 hardness: int = 100):
        self.color = color if color is not None else QColor(0, 0, 0)
        self.size = max(1, int(size))
        self.opacity = max(0, min(255, int(opacity)))
        # 0 = fully soft (centre opaque, edge transparent); 100 = hard/uniform.
        self.hardness = max(0, min(100, int(hardness)))
        # Active stroke state; None when idle.
        self._stroke: dict | None = None
        # True when `_paint_at` was invoked outside of an active stroke and
        # should commit a DrawCommand immediately.
        self._auto_commit = False

    def get_options(self) -> dict:
        return {'color': self.color, 'size': self.size,
                'opacity': self.opacity, 'hardness': self.hardness}

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
                    dist = (dx * dx + dy * dy) ** 0.5
                    falloff = self._falloff(dist, radius)
                    new_color = self._compute_pixel_color(project, px, py, falloff)
                    project.image.setPixel(px, py, new_color.rgba())
                    self._stroke['new'][(px, py)] = project.image.pixel(px, py)

        if self._auto_commit and self._stroke['new']:
            stack.push(DrawCommand(project,
                                   self._stroke['old'],
                                   self._stroke['new']))
            self._stroke = None
            self._auto_commit = False

    def _falloff(self, dist: float, radius: int) -> float:
        """Return an alpha multiplier in [0, 1] for a pixel `dist` away from
        the brush centre. hardness=100 -> uniform 1.0 everywhere (hard edge);
        hardness=0 -> linear fade from 1.0 at the centre to 0.0 at the edge."""
        if radius <= 0:
            return 1.0
        f = 1.0 - (1.0 - self.hardness / 100.0) * (dist / radius)
        return max(0.0, min(1.0, f))

    def _compute_pixel_color(self, project, px: int, py: int,
                             falloff: float = 1.0) -> QColor:
        """Apply opacity + hardness falloff blending against the existing
        pixel (alpha additive)."""
        base_alpha = self.opacity if self.opacity <= 255 else 255
        eff_alpha = int(round(base_alpha * falloff))
        if eff_alpha >= 255:
            return QColor(self.color)
        old = project.image.pixelColor(px, py)
        blended = QColor(old)
        blended.setRed(int((old.red() * (255 - eff_alpha)
                            + self.color.red() * eff_alpha) / 255))
        blended.setGreen(int((old.green() * (255 - eff_alpha)
                              + self.color.green() * eff_alpha) / 255))
        blended.setBlue(int((old.blue() * (255 - eff_alpha)
                             + self.color.blue() * eff_alpha) / 255))
        blended.setAlpha(min(255, old.alpha() + eff_alpha))
        return blended