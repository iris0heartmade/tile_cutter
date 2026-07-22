from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent
from editor.tools.base_tool import Tool


class RectSelectTool(Tool):
    """Drag to create a rectangular pixel selection on the canvas."""

    name = 'Rectangle Select'

    def __init__(self):
        self._start = None
        self._current = None

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._current = event.pos()

    def on_mouse_move(self, event: QMouseEvent, canvas):
        if self._start is not None:
            self._current = event.pos()
            self._update_selection(canvas)

    def on_mouse_release(self, event: QMouseEvent, canvas):
        if self._start is not None:
            self._current = event.pos()
            self._update_selection(canvas)
            self._start = None
            self._current = None

    def _update_selection(self, canvas):
        x1 = int(min(self._start.x(), self._current.x()) / canvas.zoom())
        y1 = int(min(self._start.y(), self._current.y()) / canvas.zoom())
        x2 = int(max(self._start.x(), self._current.x()) / canvas.zoom())
        y2 = int(max(self._start.y(), self._current.y()) / canvas.zoom())
        pixels = set()
        for y in range(max(0, y1), min(canvas.project.height, y2 + 1)):
            for x in range(max(0, x1), min(canvas.project.width, x2 + 1)):
                pixels.add((x, y))
        canvas.project.set_selection(pixels)