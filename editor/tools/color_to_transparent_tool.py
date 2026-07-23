from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QMouseEvent
from editor.tools.base_tool import Tool
from editor.commands.replace_color_command import ReplaceColorCommand


class ColorToTransparentTool(Tool):
    """Click to push a `ReplaceColorCommand` that turns matching pixels
    fully transparent. Default `color` is the gray Gemini checkerboard
    (127, 127, 127). Operates on the current selection if non-empty,
    otherwise scans the whole canvas.
    """

    name = '颜色转透明'

    def __init__(self, color: QColor = None, tolerance: int = 0):
        self.color = color if color is not None else QColor(127, 127, 127)
        self.tolerance = max(0, min(255, int(tolerance)))

    def get_options(self) -> dict:
        return {'color': self.color, 'tolerance': self.tolerance}

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() != Qt.LeftButton:
            return
        pixels: Optional[set] = None
        if canvas.project.selection:
            pixels = canvas.project.selection
        cmd = ReplaceColorCommand(canvas.project,
                                  self.color,
                                  QColor(0, 0, 0, 0),
                                  pixels=pixels,
                                  tolerance=self.tolerance)
        canvas.command_stack.push(cmd)

    def on_mouse_move(self, event: QMouseEvent, canvas):
        pass

    def on_mouse_release(self, event: QMouseEvent, canvas):
        pass