from pathlib import Path
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QImage


class SourceImage:
    def __init__(self, path: Path, tile_width: int, tile_height: int,
                 offset_x: int = 0, offset_y: int = 0,
                 gutter_x: int = 0, gutter_y: int = 0):
        self.path = Path(path)
        self.tile_width = int(tile_width)
        self.tile_height = int(tile_height)
        self.offset_x = int(offset_x)
        self.offset_y = int(offset_y)
        self.gutter_x = int(gutter_x)
        self.gutter_y = int(gutter_y)

        if not self.path.exists():
            raise FileNotFoundError(f'Source image not found: {self.path}')

        self.image = QImage(str(self.path))
        if self.image.isNull():
            raise ValueError(f'Failed to load image: {self.path}')

        available_w = self.image.width() - self.offset_x
        available_h = self.image.height() - self.offset_y
        if available_w <= 0 or available_h <= 0:
            self._cols = 0
            self._rows = 0
        else:
            self._cols = max(0, (available_w + self.gutter_x) // (self.tile_width + self.gutter_x))
            self._rows = max(0, (available_h + self.gutter_y) // (self.tile_height + self.gutter_y))

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def rows(self) -> int:
        return self._rows

    def rect_for_tile(self, col: int, row: int) -> QRect:
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            raise IndexError(f'Tile ({col}, {row}) out of bounds ({self.cols}x{self.rows})')
        x = self.offset_x + col * (self.tile_width + self.gutter_x)
        y = self.offset_y + row * (self.tile_height + self.gutter_y)
        return QRect(x, y, self.tile_width, self.tile_height)
