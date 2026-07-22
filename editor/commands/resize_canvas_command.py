from PyQt5.QtGui import QImage
from editor.commands.base_command import Command


class ResizeCanvasCommand(Command):
    """Add/remove rows and columns on the target canvas.

    NOTE: minimal placeholder created in Task 10 so MainWindow can wire up
    the cols/rows spinboxes; the full implementation (with its own tests)
    lands in Task 11. API is final: (project, delta_cols, delta_rows, anchor).
    """

    def __init__(self, project, delta_cols: int, delta_rows: int,
                 anchor: str = 'top-left'):
        self.project = project
        self.delta_cols = int(delta_cols)
        self.delta_rows = int(delta_rows)
        self.anchor = anchor
        self._old_image = None
        self._old_cols = None
        self._old_rows = None

    def do(self):
        self._old_image = QImage(self.project.image)
        self._old_cols = self.project.cols
        self._old_rows = self.project.rows
        self.project.resize_canvas(self.delta_cols, self.delta_rows, self.anchor)

    def undo(self):
        self.project.image = QImage(self._old_image)
        self.project.cols = self._old_cols
        self.project.rows = self._old_rows
