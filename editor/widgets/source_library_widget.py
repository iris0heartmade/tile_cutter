from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QSpinBox, QFormLayout,
    QMessageBox, QScrollArea, QDoubleSpinBox, QComboBox, QGroupBox,
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
        self._select_start = None
        self._select_end = None
        self._current_source_index = -1
        self._zoom = 4.0
        self._pan_x = 0
        self._pan_y = 0
        self._drag_start = None
        self._sync_mode = True
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

        self.reset_btn = QPushButton('重置视图')
        self.reset_btn.clicked.connect(self._reset_view)
        layout.addWidget(self.reset_btn)

        mode_layout = QHBoxLayout()
        self.sync_btn = QPushButton('同步模式')
        self.sync_btn.setCheckable(True)
        self.sync_btn.setChecked(True)
        self.sync_btn.clicked.connect(self._on_mode_changed)
        mode_layout.addWidget(self.sync_btn)
        self.async_btn = QPushButton('非同步模式')
        self.async_btn.setCheckable(True)
        self.async_btn.setChecked(False)
        self.async_btn.clicked.connect(self._on_mode_changed)
        mode_layout.addWidget(self.async_btn)
        layout.addLayout(mode_layout)

        # Preview area: scrollable so large source images can be viewed
        # at 1:1 or higher zoom.
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(False)
        self.preview_label = TilePreviewLabel(self)
        self.preview_scroll.setWidget(self.preview_label)
        layout.addWidget(self.preview_scroll, 1)

        source_grid_group = QGroupBox('参考区网格')
        source_form = QFormLayout(source_grid_group)
        self.src_tile_w = QSpinBox()
        self.src_tile_w.setRange(1, 512)
        self.src_tile_w.setValue(self.project.tile_width)
        self.src_tile_h = QSpinBox()
        self.src_tile_h.setRange(1, 512)
        self.src_tile_h.setValue(self.project.tile_height)
        source_form.addRow('瓦片宽:', self.src_tile_w)
        source_form.addRow('瓦片高:', self.src_tile_h)
        layout.addWidget(source_grid_group)

        self.copy_scale_group = QGroupBox('复制缩放')
        copy_form = QFormLayout(self.copy_scale_group)
        self.scale_mode = QComboBox()
        self.scale_mode.addItem('不缩放', 'none')
        self.scale_mode.addItem('指定尺寸', 'scale')
        copy_form.addRow('缩放模式:', self.scale_mode)
        self.scale_target_w = QSpinBox()
        self.scale_target_w.setRange(1, 1024)
        self.scale_target_w.setValue(self.project.tile_width)
        self.scale_target_h = QSpinBox()
        self.scale_target_h.setRange(1, 1024)
        self.scale_target_h.setValue(self.project.tile_height)
        copy_form.addRow('目标宽:', self.scale_target_w)
        copy_form.addRow('目标高:', self.scale_target_h)
        layout.addWidget(self.copy_scale_group)
        self.copy_scale_group.setVisible(False)

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
        if self._sync_mode:
            self.project.set_tile_size(tile_w, tile_h)
            self.tile_size_changed.emit(tile_w, tile_h)

    def _on_mode_changed(self, checked):
        if checked:
            if self.sender() == self.sync_btn:
                self._sync_mode = True
                self.sync_btn.setChecked(True)
                self.async_btn.setChecked(False)
                self.copy_scale_group.setVisible(False)
                self.src_tile_w.setValue(self.project.tile_width)
                self.src_tile_h.setValue(self.project.tile_height)
                for source in self.sources:
                    source.set_tile_size(self.project.tile_width, self.project.tile_height)
                self._update_preview()
            else:
                self._sync_mode = False
                self.sync_btn.setChecked(False)
                self.async_btn.setChecked(True)
                self.copy_scale_group.setVisible(True)

    def _reset_view(self):
        self._pan_x = 0
        self._pan_y = 0
        self._select_start = None
        self._select_end = None
        self._update_preview()

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
            self._select_start = None
            self._select_end = None
            self._pan_x = 0
            self._pan_y = 0
            self._update_preview()

    def _update_preview(self):
        if self._current_source_index < 0 or self._current_source_index >= len(self.sources):
            return
        source = self.sources[self._current_source_index]
        img_w = source.image.width()
        img_h = source.image.height()
        if img_w <= 0 or img_h <= 0:
            return

        draw_w = int(img_w * self._zoom)
        draw_h = int(img_h * self._zoom)
        pixmap = QPixmap.fromImage(source.image).scaled(
            draw_w, draw_h,
            Qt.IgnoreAspectRatio, Qt.FastTransformation)

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

        pixmap = self._draw_grid_on_pixmap(pixmap, source)

        viewport = self.preview_scroll.viewport()
        view_w = viewport.width()
        view_h = viewport.height()
        display_w = max(draw_w, view_w)
        display_h = max(draw_h, view_h)
        final_pixmap = QPixmap(display_w, display_h)
        final_pixmap.fill(QColor(30, 30, 30))

        painter = QPainter(final_pixmap)
        painter.drawPixmap(int(self._pan_x), int(self._pan_y), pixmap)
        painter.end()

        self.preview_label.setFixedSize(display_w, display_h)
        self.preview_label.setPixmap(final_pixmap)

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
        if event.button() == Qt.RightButton:
            self._drag_start = (event.x(), event.y())
            return
        tile = self._event_to_tile(event)
        if tile is None:
            return
        self._select_start = tile
        self._select_end = tile
        self._update_preview()

    def _on_preview_mouse_move(self, event):
        if self._drag_start is not None:
            dx = event.x() - self._drag_start[0]
            dy = event.y() - self._drag_start[1]
            self._pan_x += dx
            self._pan_y += dy
            self._drag_start = (event.x(), event.y())
            self._update_preview()
            return
        if self._select_start is None:
            return
        tile = self._event_to_tile(event)
        if tile is None:
            return
        self._select_end = tile
        self._update_preview()

    def _on_preview_mouse_release(self, event):
        if event.button() == Qt.RightButton:
            self._drag_start = None

    def _event_to_tile(self, event):
        if self._current_source_index < 0:
            return None
        source = self.sources[self._current_source_index]
        img_w = source.image.width()
        img_h = source.image.height()
        if img_w <= 0 or img_h <= 0:
            return None

        ix = (event.x() - self._pan_x) / self._zoom
        iy = (event.y() - self._pan_y) / self._zoom
        if ix < 0 or iy < 0 or ix >= img_w or iy >= img_h:
            return None

        if ix < source.offset_x or iy < source.offset_y:
            return None

        rel_x = ix - source.offset_x
        rel_y = iy - source.offset_y

        pitch_x = source.tile_width + source.gutter_x
        pitch_y = source.tile_height + source.gutter_y
        if pitch_x <= 0 or pitch_y <= 0:
            return None

        col = int(rel_x) // pitch_x
        row = int(rel_y) // pitch_y

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

        min_col, max_col, min_row, max_row = self._normalized_selection()
        cols = max_col - min_col + 1
        rows = max_row - min_row + 1
        out_w = cols * source.tile_width
        out_h = rows * source.tile_height

        copied = QImage(out_w, out_h, QImage.Format_ARGB32)
        copied.fill(0)

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

        if not self._sync_mode:
            target_w = cols * self.project.tile_width
            target_h = rows * self.project.tile_height
            copied = copied.scaled(target_w, target_h,
                                   Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        self.tile_copied.emit(copied)
