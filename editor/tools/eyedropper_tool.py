from PyQt5.QtGui import QMouseEvent
from editor.tools.base_tool import Tool


class EyedropperTool(Tool):
    """Click picks the canvas pixel color into `self.picked_color`."""

    name = 'Eyedropper'

    def __init__(self):
        self.picked_color = None

    def on_mouse_press(self, event: QMouseEvent, canvas):
        x = int(event.pos().x() / canvas.zoom())
        y = int(event.pos().y() / canvas.zoom())
        if 0 <= x < canvas.project.width and 0 <= y < canvas.project.height:
            self.picked_color = canvas.project.image.pixelColor(x, y)

    def on_mouse_move(self, event: QMouseEvent, canvas):
        pass

    def on_mouse_release(self, event: QMouseEvent, canvas):
        pass