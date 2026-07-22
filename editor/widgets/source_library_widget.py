from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QSpinBox, QFormLayout
)
from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage


class SourceLibraryWidget(QWidget):
    tile_copied = pyqtSignal(QImage)

    def __init__(self, project: ProjectModel, parent=None):
        super().__init__(parent)
        self.project = project
        self.sources = []
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

        self.preview_label = QLabel('Select a source')
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

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
            self._update_preview()

    def _update_preview(self):
        if not hasattr(self, '_current_source_index'):
            return
        source = self.sources[self._current_source_index]
        pixmap = QPixmap.fromImage(source.image)
        self.preview_label.setPixmap(pixmap.scaled(
            self.preview_label.width(), self.preview_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

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

    def copy_selection(self):
        # Placeholder: full implementation in Task 9.
        if not self.sources:
            return
        source = self.sources[0]
        self.tile_copied.emit(source.image.copy())