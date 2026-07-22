from PyQt5.QtCore import QRect
from PyQt5.QtGui import QImage, qRgba, QPainter
from typing import List, Tuple, Optional


class ProjectModel:
    def __init__(self, tile_width: int, tile_height: int,
                 cols: int, rows: int,
                 offset_x: int = 0, offset_y: int = 0,
                 gutter_x: int = 0, gutter_y: int = 0):
        self.tile_width = int(tile_width)
        self.tile_height = int(tile_height)
        self.offset_x = int(offset_x)
        self.offset_y = int(offset_y)
        self.gutter_x = int(gutter_x)
        self.gutter_y = int(gutter_y)
        self.cols = int(cols)
        self.rows = int(rows)
        self.sources: List = []
        self.selection = set()
        self.active_tool = None
        self._recreate_image()

    def set_selection(self, pixels):
        """Replace the current selection with a fresh copy of `pixels`."""
        self.selection = set(pixels)

    def clear_selection(self):
        self.selection = set()

    def _calculate_size(self, cols: int, rows: int) -> Tuple[int, int]:
        w = self.offset_x + cols * self.tile_width
        if cols > 1:
            w += (cols - 1) * self.gutter_x
        h = self.offset_y + rows * self.tile_height
        if rows > 1:
            h += (rows - 1) * self.gutter_y
        return max(1, w), max(1, h)

    def _recreate_image(self):
        w, h = self._calculate_size(self.cols, self.rows)
        self.image = QImage(w, h, QImage.Format_ARGB32)
        self.image.fill(qRgba(0, 0, 0, 0))

    @property
    def width(self) -> int:
        return self.image.width()

    @property
    def height(self) -> int:
        return self.image.height()

    def tile_rect(self, col: int, row: int) -> QRect:
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            raise IndexError(f'Tile ({col}, {row}) out of bounds ({self.cols}x{self.rows})')
        x = self.offset_x + col * (self.tile_width + self.gutter_x)
        y = self.offset_y + row * (self.tile_height + self.gutter_y)
        return QRect(x, y, self.tile_width, self.tile_height)

    def pixel_to_tile(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        # Reverse mapping: find tile containing pixel (x, y)
        if x < self.offset_x or y < self.offset_y:
            return None
        col = (x - self.offset_x) // (self.tile_width + self.gutter_x)
        row = (y - self.offset_y) // (self.tile_height + self.gutter_y)
        # Check gutter dead zones
        within_col = (x - self.offset_x) % (self.tile_width + self.gutter_x)
        within_row = (y - self.offset_y) % (self.tile_height + self.gutter_y)
        if within_col >= self.tile_width or within_row >= self.tile_height:
            return None
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return col, row
        return None

    def resize_canvas(self, delta_cols: int, delta_rows: int, anchor: str = 'top-left'):
        if delta_cols == 0 and delta_rows == 0:
            return
        new_cols = max(1, self.cols + delta_cols)
        new_rows = max(1, self.rows + delta_rows)
        new_w, new_h = self._calculate_size(new_cols, new_rows)
        new_image = QImage(new_w, new_h, QImage.Format_ARGB32)
        new_image.fill(qRgba(0, 0, 0, 0))

        old_rect = self.image.rect()
        new_rect = new_image.rect()

        if anchor == 'top-left':
            x = 0
            y = 0
        elif anchor == 'top-right':
            x = new_rect.width() - old_rect.width()
            y = 0
        elif anchor == 'bottom-left':
            x = 0
            y = new_rect.height() - old_rect.height()
        elif anchor == 'bottom-right':
            x = new_rect.width() - old_rect.width()
            y = new_rect.height() - old_rect.height()
        else:
            raise ValueError(f'Unknown anchor: {anchor}')

        # Clamp so the anchored edge is preserved for both grow and shrink.
        # Valid offset range is between min(0, delta) and max(0, delta) where
        # delta = new - old. Growing -> [0, delta]; shrinking -> [delta, 0]
        # (delta < 0), letting right/bottom anchors keep their edge visible
        # instead of collapsing to (0, 0).
        dx = new_rect.width() - old_rect.width()
        dy = new_rect.height() - old_rect.height()
        x = max(min(0, dx), min(x, max(0, dx)))
        y = max(min(0, dy), min(y, max(0, dy)))

        painter = QPainter(new_image)
        painter.drawImage(x, y, self.image)
        painter.end()

        self.image = new_image
        self.cols = new_cols
        self.rows = new_rows
