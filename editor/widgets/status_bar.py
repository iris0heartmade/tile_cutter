from PyQt5.QtWidgets import QStatusBar, QLabel


class StatusBar(QStatusBar):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coords_label = QLabel('网格 (-, -)')
        self.zoom_label = QLabel('缩放 100%')
        self.size_label = QLabel('画布 -x- 瓦片')
        self.addPermanentWidget(self.coords_label)
        self.addPermanentWidget(self.zoom_label)
        self.addPermanentWidget(self.size_label)

    def set_coords(self, col: int, row: int):
        self.coords_label.setText(f'网格 ({col}, {row})')

    def set_zoom(self, zoom: float):
        self.zoom_label.setText(f'缩放 {int(zoom * 100)}%')

    def set_canvas_size(self, cols: int, rows: int):
        self.size_label.setText(f'画布 {cols}x{rows} 瓦片')
