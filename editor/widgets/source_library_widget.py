from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QSpinBox, QFormLayout,
    QMessageBox, QScrollArea, QDoubleSpinBox,
)
from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage


class TilePreviewLabel(QLabel):
    """A QLabel that delegates mouse events to its parent SourceLibraryWidget.

    The label shows the source image at a user-controlled zoom level.
    The parent widget owns the selection state and maps widget-space
    mouse coordinates back to image-space tile coordinates.
    """

    def __init__(self, widget: 'SourceLibraryWidget', parent=None):
        super().__init__(parent)
        self.widget = widget
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.widget._on_preview_mouse_press(event)

    def mouseMoveEvent(self, event):
        self.widget._on_preview_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.widget._on_preview_mouse_release(event)


class SourceLibraryWidget(QWidget):
    tile_copied = pyqtSignal(QImage)
    tile_size_changed = pyqtSignal(int, int)

    def __init__(self, project: ProjectModel, parent=None):
        super().__init__(parent)
        self.project = project
        self.sources = []
        # Selection state: rectangular range in (col, row) tile coords.
        self._select_start = None  # (col, row) or None
        self._select_end = None    # (col, row) or None
        self._current_source_index = -1
        self._zoom = 4.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.source_list = QListWidget()
        self.source_list.currentRowChanged.connect(self._on_source_changed)
        layout.addWidget(self.source_list)

        self.add_btn = QPushButton('添加源图')
        self.add_btn.clicked.connect(self._add_source_dialog)
        layout.addWidget(self.add_btn)

        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel('缩放:'))
        self.zoom_spin = QDoubleSpinBox()
        self.zoom_spin.setRange(0.25, 8.0)
        self.zoom_spin.setSingleStep(0.25)
        self.zoom_spin.setValue(self._zoom)
        self.zoom_spin.setSuffix('x')
        self.zoom_spin.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_spin)
        layout.addLayout(zoom_layout)

        self.copy_btn = QPushButton('复制选区')
        self.copy_btn.setShortcut('Ctrl+C')
        self.copy_btn.clicked.connect(self.copy_selection)
        layout.addWidget(self.copy_btn)

        # Preview area: scrollable so large source images can be viewed
        # at 1:1 or higher zoom.
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(False)
        self.preview_label = TilePreviewLabel(self)
        self.preview_scroll.setWidget(self.preview_label)
        layout.addWidget(self.preview_scroll, 1)

        # Grid config for source (mirrors project grid by default).
        form = QFormLayout()
        self.src_tile_w = QSpinBox()
        self.src_tile_w.setRange(1, 512)
        self.src_tile_w.setValue(self.project.tile_width)
        self.src_tile_h = QSpinBox()
        self.src_tile_h.setRange(1, 512)
        self.src_tile_h.setValue(self.project.tile_height)
        form.addRow('瓦片宽:', self.src_tile_w)
        form.addRow('瓦片高:', self.src_tile_h)
        layout.addLayout(form)

        self.src_tile_w.valueChanged.connect(self._on_tile_size_changed)
        self.src_tile_h.valueChanged.connect(self._on_tile_size_changed)

        self.setLayout(layout)

    def _on_zoom_changed(self, value: float):
        self._zoom = max(0.25, min(8.0, float(value)))
        self._update_preview()

    def _on_tile_size_changed(self, _):
        tile_w = self.src_tile_w.value()
        tile_h = self.src_tile_h.value()
        for source in self.sources:
            source.set_tile_size(tile_w, tile_h)
        self._select_start = None
        self._select_end = None
        self._update_preview()
        self.tile_size_changed.emit(tile_w, tile_h)

    def add_source(self, source: SourceImage):
        self.sources.append(source)
        item = QListWidgetItem(source.path.name)
        self.source_list.addItem(item)
        if self.source_list.count() == 1:
            self.source_list.setCurrentRow(0)

    def count(self) -> int:
        return len(self.sources)

    def _on_source_changed(self, index: int):
        if 0 <= index < len(self.sources):
            self._current_source_index = index
            # Reset selection when switching source images.
            self._select_start = None
            self._select_end = None
            self._update_preview()

    def _update_preview(self):
        if self._current_source_index < 0 or self._current_source_index >= len(self.sources):
            return
        source = self.sources[self._current_source_index]
        img_w = source.image.width()
        img_h = source.image.height()
        if img_w <= 0 or img_h <= 0:
            return

        # Scale the image by the user-controlled zoom factor.
        draw_w = int(img_w * self._zoom)
        draw_h = int(img_h * self._zoom)
        pixmap = QPixmap.fromImage(source.image).scaled(
            draw_w, draw_h,
            Qt.IgnoreAspectRatio, Qt.FastTransformation)

        # Overlay the selection rectangle on top of the scaled image.
        if self._select_start is not None and self._select_end is not None:
            overlay = QPixmap(pixmap)
            painter = QPainter(overlay)
            pen = QPen(QColor(0, 150, 255, 230))
            pen.setWidth(max(1, int(self._zoom * 2)))
            painter.setPen(pen)
            min_col, max_col, min_row, max_row = self._normalized_selection()

            pitch_w = (source.tile_width + source.gutter_x) * self._zoom
            pitch_h = (source.tile_height + source.gutter_y) * self._zoom
            off_x = source.offset_x * self._zoom
            off_y = source.offset_y * self._zoom

            x = off_x + min_col * pitch_w
            y = off_y + min_row * pitch_h
            w = (max_col - min_col + 1) * pitch_w - source.gutter_x * self._zoom
            h = (max_row - min_row + 1) * pitch_h - source.gutter_y * self._zoom
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.end()
            pixmap = overlay

        # Draw grid overlay (tile boundaries) on top of everything.
        pixmap = self._draw_grid_on_pixmap(pixmap, source)

        self.preview_label.setFixedSize(draw_w, draw_h)
        self.preview_label.setPixmap(pixmap)

    def _draw_grid_on_pixmap(self, pixmap: QPixmap, source: SourceImage) -> QPixmap:
        """Draw tile grid lines on top of the given pixmap.

        Returns a new pixmap with grid overlay so the original is not
        modified in-place.
        """
        overlay = QPixmap(pixmap)
        painter = QPainter(overlay)
        pen = QPen(QColor(100, 200, 255, 120))
        pen.setWidth(max(1, int(self._zoom)))
        painter.setPen(pen)

        z = self._zoom
        off_x = source.offset_x * z
        off_y = source.offset_y * z
        pitch_w = (source.tile_width + source.gutter_x) * z
        pitch_h = (source.tile_height + source.gutter_y) * z
        draw_w = pixmap.width()
        draw_h = pixmap.height()

        # Vertical lines (tile boundaries, not gutter boundaries).
        for col in range(source.cols + 1):
            x = int(off_x + col * pitch_w)
            if 0 <= x <= draw_w:
                painter.drawLine(x, int(off_y), x, int(min(draw_h, off_y + source.rows * pitch_h)))

        # Horizontal lines.
        for row in range(source.rows + 1):
            y = int(off_y + row * pitch_h)
            if 0 <= y <= draw_h:
                painter.drawLine(int(off_x), y, int(min(draw_w, off_x + source.cols * pitch_w)), y)

        painter.end()
        return overlay

    def _add_source_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, '打开源图片', '', 'PNG图片 (*.png)')
        if not paths:
            return
        for path in paths:
            source = SourceImage(
                path,
                self.src_tile_w.value(),
                self.src_tile_h.value(),
            )
            self.add_source(source)

    # --- Tile selection handling -------------------------------------------

    def _on_preview_mouse_press(self, event):
        if self._current_source_index < 0 or self._current_source_index >= len(self.sources):
            return
        tile = self._event_to_tile(event)
        if tile is None:
            return
        self._select_start = tile
        self._select_end = tile
        self._update_preview()

    def _on_preview_mouse_move(self, event):
        if self._select_start is None:
            return
        tile = self._event_to_tile(event)
        if tile is None:
            return
        self._select_end = tile
        self._update_preview()

    def _on_preview_mouse_release(self, event):
        # Selection is finalized on press/move; release is a no-op.
        return

    def _event_to_tile(self, event):
        """Map a widget-space mouse event to (col, row) tile coords in the
        current source image. Returns None when the event is outside the
        drawn image area or falls inside a gutter.
        """
        if self._current_source_index < 0:
            return None
        source = self.sources[self._current_source_index]
        img_w = source.image.width()
        img_h = source.image.height()
        if img_w <= 0 or img_h <= 0:
            return None

        # Mouse coords are directly in scaled image space because the label
        # size matches the scaled image exactly.
        ix = event.x() / self._zoom
        iy = event.y() / self._zoom
        if ix < 0 or iy < 0 or ix >= img_w or iy >= img_h:
            return None

        # Respect source offset: pixels before offset_x/offset_y are not part
        # of any tile.
        if ix < source.offset_x or iy < source.offset_y:
            return None

        # Compute position relative to the first tile origin.
        rel_x = ix - source.offset_x
        rel_y = iy - source.offset_y

        pitch_x = source.tile_width + source.gutter_x
        pitch_y = source.tile_height + source.gutter_y
        if pitch_x <= 0 or pitch_y <= 0:
            return None

        col = int(rel_x) // pitch_x
        row = int(rel_y) // pitch_y

        # Reject clicks that fall inside a gutter (not on actual tile pixels).
        within_col = int(rel_x) % pitch_x
        within_row = int(rel_y) % pitch_y
        if within_col >= source.tile_width or within_row >= source.tile_height:
            return None

        if 0 <= col < source.cols and 0 <= row < source.rows:
            return col, row
        return None

    def _normalized_selection(self):
        """Return (min_col, max_col, min_row, max_row) for the current
        rectangular selection. Raises if there is no selection.
        """
        if self._select_start is None or self._select_end is None:
            raise ValueError('No tile selection')
        c1, r1 = self._select_start
        c2, r2 = self._select_end
        return min(c1, c2), max(c1, c2), min(r1, r2), max(r1, r2)

    # --- Copy selection to clipboard QImage ---------------------------------

    def copy_selection(self):
        if self._current_source_index < 0 or self._current_source_index >= len(self.sources):
            return
        if self._select_start is None or self._select_end is None:
            return
        source = self.sources[self._current_source_index]

        # Grid match check happens BEFORE any pixel copying.
        if (source.tile_width != self.project.tile_width
                or source.tile_height != self.project.tile_height):
            QMessageBox.warning(
                self,
                '网格不匹配',
                f'源图网格 {source.tile_width}x{source.tile_height} 与目标网格 '
                f'{self.project.tile_width}x{self.project.tile_height} 不匹配。'
                f'复制已取消。',
            )
            return

        min_col, max_col, min_row, max_row = self._normalized_selection()
        cols = max_col - min_col + 1
        rows = max_row - min_row + 1
        out_w = cols * source.tile_width
        out_h = rows * source.tile_height

        copied = QImage(out_w, out_h, QImage.Format_ARGB32)
        copied.fill(0)

        # Walk row-by-row from source into the output QImage.
        for r_offset, r in enumerate(range(min_row, max_row + 1)):
            for c_offset, c in enumerate(range(min_col, max_col + 1)):
                src_rect = source.rect_for_tile(c, r)
                dst_x = c_offset * source.tile_width
                dst_y = r_offset * source.tile_height
                for dy in range(src_rect.height()):
                    for dx in range(src_rect.width()):
                        rgba = source.image.pixel(src_rect.x() + dx,
                                                  src_rect.y() + dy)
                        copied.setPixel(dst_x + dx, dst_y + dy, rgba)

        self.tile_copied.emit(copied)
