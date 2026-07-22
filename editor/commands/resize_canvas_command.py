from typing import Optional

from PyQt5.QtGui import QImage

from editor.commands.base_command import Command


class ResizeCanvasCommand(Command):
    """Add/remove rows and columns on the target canvas.

    `do` snapshots the full pre-resize state (image, cols, rows) and then
    delegates to `ProjectModel.resize_canvas`, which handles anchor placement
    and clamps the grid to at least 1x1. `undo` restores the snapshot, so
    pixels cropped away by a shrink come back intact.
    """

    def __init__(self, project, delta_cols: int, delta_rows: int,
                 anchor: str = 'top-left'):
        self.project = project
        self.delta_cols = int(delta_cols)
        self.delta_rows = int(delta_rows)
        self.anchor = anchor
        self._old_image: Optional[QImage] = None
        self._old_cols: Optional[int] = None
        self._old_rows: Optional[int] = None

    def do(self) -> None:
        self._old_image = QImage(self.project.image)
        self._old_cols = self.project.cols
        self._old_rows = self.project.rows
        self.project.resize_canvas(self.delta_cols, self.delta_rows, self.anchor)

    def undo(self) -> None:
        self.project.image = QImage(self._old_image)
        self.project.cols = self._old_cols
        self.project.rows = self._old_rows
