from PyQt5.QtWidgets import QStatusBar, QLabel


class StatusBar(QStatusBar):
    """Bottom status bar: grid coords | zoom | canvas size in tiles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coords_label = QLabel('grid (-, -)')
        self.zoom_label = QLabel('zoom 100%')
        self.size_label = QLabel('canvas -x- tiles')
        self.addPermanentWidget(self.coords_label)
        self.addPermanentWidget(self.zoom_label)
        self.addPermanentWidget(self.size_label)

    def set_coords(self, col: int, row: int):
        self.coords_label.setText(f'grid ({col}, {row})')

    def set_zoom(self, zoom: float):
        self.zoom_label.setText(f'zoom {int(zoom * 100)}%')

    def set_canvas_size(self, cols: int, rows: int):
        self.size_label.setText(f'canvas {cols}x{rows} tiles')
