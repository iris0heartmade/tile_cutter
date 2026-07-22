from typing import Optional
from PyQt5.QtGui import QColor
from editor.commands.base_command import Command


class ReplaceColorCommand(Command):
    """Replace every pixel matching `target_color` (within `tolerance`) in
    either the supplied `pixels` set or the entire canvas with `replacement_color`.
    Stores old/new per-pixel maps so undo/redo are exact.
    """

    def __init__(self, project, target_color: QColor,
                 replacement_color: QColor = None,
                 pixels: Optional[set] = None,
                 tolerance: int = 0):
        self.project = project
        self.target_color = QColor(target_color)
        self.replacement_color = (QColor(replacement_color)
                                  if replacement_color is not None
                                  else QColor(0, 0, 0, 0))
        # Default replacement is fully transparent.
        self.replacement_rgba = self.replacement_color.rgba()
        self.tolerance = max(0, min(255, int(tolerance)))
        # Defensively copy so caller mutation doesn't corrupt a queued command.
        self.pixels = set(pixels) if pixels is not None else None
        self.old_values: dict = {}
        self.new_values: dict = {}

    def do(self):
        self.old_values = {}
        self.new_values = {}
        new_rgba = self.replacement_rgba
        if self.pixels is not None:
            targets = self.pixels
        else:
            targets = self._all_pixels()
        for x, y in targets:
            if not (0 <= x < self.project.width and 0 <= y < self.project.height):
                continue
            old_rgba = self.project.image.pixel(x, y)
            if not self._matches(old_rgba):
                continue
            self.old_values[(x, y)] = old_rgba
            self.new_values[(x, y)] = new_rgba
            self.project.image.setPixel(x, y, new_rgba)

    def undo(self):
        for (x, y), rgba in self.old_values.items():
            self.project.image.setPixel(x, y, rgba)

    def _all_pixels(self):
        return {(x, y)
                for y in range(self.project.height)
                for x in range(self.project.width)}

    def _matches(self, rgba: int) -> bool:
        # Compare the stored target color's RGBA channels against the pixel's.
        t = self.target_color.getRgb()
        pr = (rgba >> 16) & 0xFF
        pg = (rgba >> 8) & 0xFF
        pb = rgba & 0xFF
        pa = (rgba >> 24) & 0xFF
        return (abs(t[0] - pr) <= self.tolerance
                and abs(t[1] - pg) <= self.tolerance
                and abs(t[2] - pb) <= self.tolerance
                and abs(t[3] - pa) <= self.tolerance)