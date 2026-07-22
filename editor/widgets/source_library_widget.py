from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QSpinBox, QFormLayout,
    QMessageBox,
)
from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage


class TilePreviewLabel(QLabel):
    """A QLabel that delegates mouse events to its parent SourceLibraryWidget.

    The label handles its own paint of the source image (scaled with
    KeepAspectRatio). The parent widget owns the selection state
    (`_select_start`, `_select_end`) and the math that maps widget-space
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

    def __init__(self, project: ProjectModel, parent=None):
        super().__init__(parent)
        self.project = project
        self.sources = []
        # Selection state: rectangular range in (col, row) tile coords.
        self._select_start = None  # (col, row) or None
        self._select_end = None    # (col, row) or None
        self._current_source_index = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.source_list = QListWidget()
        self.source_list.currentRowChanged.connect(self._on_source_changed)
        layout.addWidget(self.source_list)

        self.add_btn = QPushButton('Add Source')
        self.add_btn.clicked.connect(self._add_source_dialog)
        layout.addWidget(self.add_btn)

        self.copy_btn = QPushButton('Copy Selection')
        self.copy_btn.clicked.connect(self.copy_selection)
        layout.addWidget(self.copy_btn)

        self.preview_label = TilePreviewLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        layout.addWidget(self.preview_label, 1)

        # Grid config for source (mirrors project grid by default).
        form = QFormLayout()
        self.src_tile_w = QSpinBox()
        self.src_tile_w.setRange(1, 512)
        self.src_tile_w.setValue(self.project.tile_width)
        self.src_tile_h = QSpinBox()
        self.src_tile_h.setRange(1, 512)
        self.src_tile_h.setValue(self.project.tile_height)
        form.addRow('Tile W:', self.src_tile_w)
        form.addRow('Tile H:', self.src_tile_h)
        layout.addLayout(form)

        self.setLayout(layout)

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
        label_size = self.preview_label.size()
        # Guard against a zero-sized label during initial layout.
        if label_size.width() <= 0 or label_size.height() <= 0:
            return
        pixmap = QPixmap.fromImage(source.image).scaled(
            label_size.width(), label_size.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Overlay the selection rectangle on top of the scaled image.
        if self._select_start is not None and self._select_end is not None:
            overlay = QPixmap(pixmap)
            painter = QPainter(overlay)
            pen = QPen(QColor(0, 150, 255, 230))
            pen.setWidth(2)
            painter.setPen(pen)
            min_col, max_col, min_row, max_row = self._normalized_selection()
            img_w = source.image.width()
            img_h = source.image.height()
            scale = min(label_size.width() / img_w, label_size.height() / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
            offset_x = (label_size.width() - draw_w) / 2
            offset_y = (label_size.height() - draw_h) / 2
            tile_pitch_w = source.tile_width * scale
            tile_pitch_h = source.tile_height * scale
            x = offset_x + min_col * tile_pitch_w
            y = offset_y + min_row * tile_pitch_h
            w = (max_col - min_col + 1) * tile_pitch_w
            h = (max_row - min_row + 1) * tile_pitch_h
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.end()
            pixmap = overlay
        self.preview_label.setPixmap(pixmap)

    def _add_source_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Open Source Image', '', 'PNG Images (*.png)')
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
        drawn image area.
        """
        if self._current_source_index < 0:
            return None
        source = self.sources[self._current_source_index]
        label_size = self.preview_label.size()
        img_w = source.image.width()
        img_h = source.image.height()
        if img_w <= 0 or img_h <= 0 or label_size.width() <= 0 or label_size.height() <= 0:
            return None
        # Same KeepAspectRatio math used by QPixmap.scaled() above.
        scale = min(label_size.width() / img_w, label_size.height() / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        offset_x = (label_size.width() - draw_w) / 2
        offset_y = (label_size.height() - draw_h) / 2
        ix = (event.x() - offset_x) / scale
        iy = (event.y() - offset_y) / scale
        if ix < 0 or iy < 0 or ix >= img_w or iy >= img_h:
            return None
        col = int(ix) // source.tile_width
        row = int(iy) // source.tile_height
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
                'Grid Mismatch',
                f'Source grid {source.tile_width}x{source.tile_height} does not '
                f'match target grid '
                f'{self.project.tile_width}x{self.project.tile_height}. '
                f'Copy aborted.',
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