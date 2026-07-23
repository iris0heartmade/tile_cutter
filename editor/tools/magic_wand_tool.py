from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent, QColor
from editor.tools.base_tool import Tool


class MagicWandTool(Tool):
    """Click to select pixels matching a target color within a tolerance."""

    name = '魔棒'

    def __init__(self, tolerance: int = 0, contiguous: bool = True):
        self.tolerance = max(0, min(255, int(tolerance)))
        self.contiguous = bool(contiguous)

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() != Qt.LeftButton:
            return
        x = int(event.pos().x() / canvas.zoom())
        y = int(event.pos().y() / canvas.zoom())
        if 0 <= x < canvas.project.width and 0 <= y < canvas.project.height:
            pixels = self._select_at(canvas.project, x, y)
            canvas.project.set_selection(pixels)

    def on_mouse_move(self, event: QMouseEvent, canvas):
        pass

    def on_mouse_release(self, event: QMouseEvent, canvas):
        pass

    def _matches(self, target: QColor, current: QColor) -> bool:
        return all(abs(target.getRgb()[i] - current.getRgb()[i]) <= self.tolerance
                   for i in range(4))

    def _select_at(self, project, x: int, y: int):
        target = project.image.pixelColor(x, y)
        width, height = project.width, project.height
        selected = set()

        if self.contiguous:
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in selected:
                    continue
                if not (0 <= cx < width and 0 <= cy < height):
                    continue
                if not self._matches(target, project.image.pixelColor(cx, cy)):
                    continue
                selected.add((cx, cy))
                stack.extend([(cx + 1, cy), (cx - 1, cy),
                              (cx, cy + 1), (cx, cy - 1)])
        else:
            for cy in range(height):
                for cx in range(width):
                    if self._matches(target, project.image.pixelColor(cx, cy)):
                        selected.add((cx, cy))
        return selected