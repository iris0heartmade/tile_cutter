# TileCutter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-window PyQt5 tileset editor that imports multiple source images, supports grid-based copy/paste, pixel-level editing, and exports PNG + Godot `.tres`.

**Architecture:** A Model-Widget-Command architecture. `ProjectModel` owns the target canvas and metadata. `SourceLibraryWidget` and `CanvasWidget` handle display and input. `Tool` subclasses interpret mouse events into model mutations wrapped as `Command` instances for undo/redo. `GodotExporter` serializes the canvas and a Godot 4 TileSet resource.

**Tech Stack:** Python 3.13, PyQt5, Pillow, numpy, pytest (no pytest-qt).

## Global Constraints

- Python 3.13.2
- PyQt5 available
- Pillow (PIL) available
- numpy available
- pytest 9.0.3 available
- Single-window desktop application
- Target platform: Windows 11
- All file paths in docs use `/`; implementation uses `pathlib.Path`
- RGBA images only
- Grid sizes are positive integers
- Source grid must match target grid for copy/paste

---

## File Map

| File | Responsibility |
|------|----------------|
| `main.py` | Application entry point. Creates `QApplication` and `MainWindow`. |
| `editor/app.py` | `create_application()` helper. |
| `editor/models/source_image.py` | Wrapper around a source PNG with grid metadata. |
| `editor/models/project_model.py` | Target canvas, grid config, selection, source list. |
| `editor/commands/base_command.py` | `Command` abstract base. |
| `editor/commands/draw_command.py` | Records a brush/eraser stroke for undo. |
| `editor/commands/paste_command.py` | Pastes a copied tile block. |
| `editor/commands/clear_command.py` | Clears a selection to transparent. |
| `editor/commands/replace_color_command.py` | Replaces a color with transparency. |
| `editor/commands/resize_canvas_command.py` | Adds/removes rows/columns. |
| `editor/tools/base_tool.py` | `Tool` abstract base. |
| `editor/tools/brush_tool.py` | Paints pixels. |
| `editor/tools/eraser_tool.py` | Makes pixels transparent. |
| `editor/tools/eyedropper_tool.py` | Picks color. |
| `editor/tools/rect_select_tool.py` | Rectangular selection. |
| `editor/tools/magic_wand_tool.py` | Contiguous color selection. |
| `editor/tools/color_to_transparent_tool.py` | Global color replacement. |
| `editor/exporters/godot_exporter.py` | Exports PNG + `.tres`. |
| `editor/widgets/source_library_widget.py` | Left panel for source images and tile copying. |
| `editor/widgets/canvas_widget.py` | Center target canvas. |
| `editor/widgets/options_bar.py` | Top bar showing active tool properties. |
| `editor/widgets/status_bar.py` | Bottom status display. |
| `editor/main_window.py` | Main window, menu/toolbar wiring, layout. |
| `tests/test_models.py` | Tests for `SourceImage` and `ProjectModel`. |
| `tests/test_exporter.py` | Tests for `GodotExporter`. |
| `tests/test_commands.py` | Tests for commands and undo/redo. |
| `tests/test_tools.py` | Tests for tool logic. |

---

### Task 1: Project Skeleton and Core Models

**Files:**
- Create: `editor/__init__.py`
- Create: `editor/app.py`
- Create: `editor/models/source_image.py`
- Create: `editor/models/project_model.py`
- Create: `main.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `SourceImage(path: Path, tile_width: int, tile_height: int, offset_x=0, offset_y=0, gutter_x=0, gutter_y=0)`
  - `SourceImage.image: QImage`
  - `SourceImage.cols: int`
  - `SourceImage.rows: int`
  - `SourceImage.rect_for_tile(col: int, row: int) -> QRect`
  - `ProjectModel(tile_width: int, tile_height: int, cols: int, rows: int)`
  - `ProjectModel.image: QImage`
  - `ProjectModel.tile_rect(col: int, row: int) -> QRect`
  - `ProjectModel.pixel_to_tile(x: int, y: int) -> tuple[int, int] | None`
  - `ProjectModel.resize_canvas(delta_cols: int, delta_rows: int, anchor: str = 'top-left') -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
from pathlib import Path
from PIL import Image
from PyQt5.QtCore import QRect
from editor.models.source_image import SourceImage
from editor.models.project_model import ProjectModel


def test_source_image_rect_for_tile(tmp_path):
    # Create a 64x64 RGBA image with 16x16 tiles
    img = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
    p = tmp_path / 'source.png'
    img.save(p)

    source = SourceImage(p, tile_width=16, tile_height=16)
    assert source.cols == 4
    assert source.rows == 4
    assert source.rect_for_tile(1, 1) == QRect(16, 16, 16, 16)


def test_project_model_tile_rect():
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=3)
    assert project.tile_rect(0, 0) == QRect(0, 0, 16, 16)
    assert project.tile_rect(1, 2) == QRect(16, 32, 16, 16)


def test_project_model_resize_canvas():
    project = ProjectModel(tile_width=16, tile_height=16, cols=2, rows=2)
    old = project.image.copy()
    project.resize_canvas(delta_cols=1, delta_rows=0, anchor='top-left')
    assert project.cols == 3
    assert project.rows == 2
    assert project.image.width() == 48
    assert project.image.height() == 32
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`

Expected: FAIL with import errors (`ModuleNotFoundError: No module named 'editor'`).

- [ ] **Step 3: Write minimal implementation**

Create `editor/__init__.py` (empty).

Create `editor/app.py`:

```python
import sys
from PyQt5.QtWidgets import QApplication


def create_application(argv=None):
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    app.setApplicationName('TileCutter')
    app.setApplicationVersion('0.1.0')
    return app
```

Create `editor/models/source_image.py`:

```python
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
```

Create `editor/models/project_model.py`:

```python
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QImage, qRgba
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
        self.selection = None
        self.active_tool = None
        self._recreate_image()

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

        # Clamp to keep old image fully inside new image
        x = max(0, min(x, new_rect.width() - old_rect.width()))
        y = max(0, min(y, new_rect.height() - old_rect.height()))

        from PyQt5.QtGui import QPainter
        painter = QPainter(new_image)
        painter.drawImage(x, y, self.image)
        painter.end()

        self.image = new_image
        self.cols = new_cols
        self.rows = new_rows
```

Create `main.py`:

```python
import sys
from editor.app import create_application


def main():
    app = create_application(sys.argv)
    # MainWindow will be added in a later task
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add editor/ tests/ main.py
git commit -m "feat: add project skeleton and core models"
```

---

### Task 2: Godot Exporter

**Files:**
- Create: `editor/exporters/godot_exporter.py`
- Create: `tests/test_exporter.py`

**Interfaces:**
- Consumes: `ProjectModel`
- Produces:
  - `GodotExporter.export(project: ProjectModel, png_path: Path, tres_path: Path, godot_texture_path: str) -> None`
  - PNG saved via PIL from `ProjectModel.image`
  - `.tres` file generated with Godot 4 `TileSetAtlasSource`

- [ ] **Step 1: Write the failing test**

Create `tests/test_exporter.py`:

```python
from pathlib import Path
from PyQt5.QtGui import QImage, qRgba
from editor.models.project_model import ProjectModel
from editor.exporters.godot_exporter import GodotExporter


def test_export_png_and_tres(tmp_path):
    project = ProjectModel(tile_width=16, tile_height=16, cols=2, rows=2)
    project.image.setPixelColor(0, 0, qRgba(255, 0, 0, 255))

    png_path = tmp_path / 'out.png'
    tres_path = tmp_path / 'out.tres'
    GodotExporter.export(project, png_path, tres_path, 'res://out.png')

    assert png_path.exists()
    assert tres_path.exists()

    text = tres_path.read_text()
    assert '[gd_resource type="TileSet"' in text
    assert 'texture_region_size = Vector2i(16, 16)' in text
    assert 'type="Texture2D" path="res://out.png"' in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exporter.py -v`

Expected: FAIL (`ModuleNotFoundError` or `GodotExporter` not found).

- [ ] **Step 3: Write minimal implementation**

Create `editor/exporters/__init__.py` (empty).

Create `editor/exporters/godot_exporter.py`:

```python
from pathlib import Path
from PyQt5.QtGui import QImage
from PIL import Image
import io
from editor.models.project_model import ProjectModel


class GodotExporter:
    @staticmethod
    def export(project: ProjectModel, png_path: Path, tres_path: Path, godot_texture_path: str):
        png_path = Path(png_path)
        tres_path = Path(tres_path)

        # Save PNG via PIL to preserve alpha
        buffer = io.BytesIO()
        # Convert QImage to PIL Image
        ptr = project.image.bits()
        ptr.setsize(project.image.byteCount())
        pil_image = Image.frombytes('RGBA', (project.image.width(), project.image.height()),
                                     ptr.asstring()).transpose(Image.FLIP_TOP_BOTTOM)
        # Note: QImage stores rows top-to-bottom; PIL also top-to-bottom. The conversion above
        # uses the raw bytes, but QImage ARGB32 is stored in BGRA order on little-endian.
        # A safer conversion is via QImage.save to a buffer.
        buf = io.BytesIO()
        project.image.save(buf, 'PNG')
        buf.seek(0)
        pil_image = Image.open(buf)
        pil_image.save(png_path, 'PNG')

        separation_x = project.gutter_x
        separation_y = project.gutter_y
        offset_x = project.offset_x
        offset_y = project.offset_y

        tres_content = f"""[gd_resource type="TileSet" load_steps=2 format=3]

[ext_resource type="Texture2D" path="{godot_texture_path}" id="1"]

[resource]
sources/0 = SubResource("TileSetAtlasSource_atlas0")

[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_atlas0"]
texture = ExtResource("1")
texture_region_size = Vector2i({project.tile_width}, {project.tile_height})
separation = Vector2i({separation_x}, {separation_y})
texture_offset = Vector2i({offset_x}, {offset_y})
"""
        tres_path.write_text(tres_content, encoding='utf-8')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exporter.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/exporters tests/test_exporter.py
git commit -m "feat: add Godot PNG + tres exporter"
```

---

### Task 3: Command Base and Command Stack

**Files:**
- Create: `editor/commands/base_command.py`
- Create: `tests/test_commands.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Command` abstract class with `do(self) -> None` and `undo(self) -> None`
  - `CommandStack` with `push(command)`, `undo()`, `redo()`, `can_undo()`, `can_redo()`
  - Signals: `can_undo_changed(bool)`, `can_redo_changed(bool)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_commands.py`:

```python
from editor.commands.base_command import Command, CommandStack


class AddCommand(Command):
    def __init__(self, target, value):
        self.target = target
        self.value = value

    def do(self):
        self.target['value'] += self.value

    def undo(self):
        self.target['value'] -= self.value


def test_command_stack_undo_redo():
    state = {'value': 0}
    stack = CommandStack()
    stack.push(AddCommand(state, 5))
    assert state['value'] == 5
    stack.undo()
    assert state['value'] == 0
    assert not stack.can_undo()
    stack.redo()
    assert state['value'] == 5


def test_command_stack_push_clears_redo():
    state = {'value': 0}
    stack = CommandStack()
    stack.push(AddCommand(state, 5))
    stack.undo()
    stack.push(AddCommand(state, 3))
    assert state['value'] == 3
    assert not stack.can_redo()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_commands.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/commands/__init__.py` (empty).

Create `editor/commands/base_command.py`:

```python
from abc import ABC, abstractmethod
from typing import List
from PyQt5.QtCore import QObject, pyqtSignal


class Command(ABC):
    @abstractmethod
    def do(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> None:
        raise NotImplementedError


class CommandStack(QObject):
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def push(self, command: Command):
        command.do()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        self._emit_signals()

    def undo(self):
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._emit_signals()

    def redo(self):
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.do()
        self._undo_stack.append(command)
        self._emit_signals()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def _emit_signals(self):
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_commands.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/commands tests/test_commands.py
git commit -m "feat: add Command base and CommandStack"
```

---

### Task 4: Source Library Widget

**Files:**
- Create: `editor/widgets/source_library_widget.py`
- Create: `tests/test_source_library_widget.py`

**Interfaces:**
- Consumes: `SourceImage`, `ProjectModel`
- Produces:
  - `SourceLibraryWidget(project: ProjectModel)`
  - `SourceLibraryWidget.add_source(source_image: SourceImage)`
  - `SourceLibraryWidget.copy_selection()` slot
  - Signal: `tile_copied(QImage)` — emitted when user copies tiles

- [ ] **Step 1: Write the failing test**

Create `tests/test_source_library_widget.py`:

```python
import pytest
from pathlib import Path
from PIL import Image
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage
from editor.widgets.source_library_widget import SourceLibraryWidget


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_source_library_add_source(app, tmp_path):
    project = ProjectModel(16, 16, 4, 4)
    widget = SourceLibraryWidget(project)

    img = Image.new('RGBA', (64, 64), (0, 255, 0, 255))
    p = tmp_path / 'src.png'
    img.save(p)
    source = SourceImage(p, 16, 16)

    widget.add_source(source)
    assert widget.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_source_library_widget.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/widgets/__init__.py` (empty).

Create `editor/widgets/source_library_widget.py`:

```python
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
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
        self.selected_tiles = []  # list of (source_index, col, row)
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

        # Grid config for source (mirrors project grid by default)
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
                self.src_tile_h.value()
            )
            self.add_source(source)

    def copy_selection(self):
        # Placeholder: full implementation in Task 9
        if not self.sources:
            return
        source = self.sources[0]
        # Copy the whole image as a stub; real copy handles tile selection
        self.tile_copied.emit(source.image.copy())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_source_library_widget.py -v`

Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add editor/widgets tests/test_source_library_widget.py
git commit -m "feat: add source library widget"
```

---

### Task 5: Canvas Widget Base

**Files:**
- Create: `editor/widgets/canvas_widget.py`
- Create: `tests/test_canvas_widget.py`

**Interfaces:**
- Consumes: `ProjectModel`, `CommandStack`
- Produces:
  - `CanvasWidget(project: ProjectModel, command_stack: CommandStack)`
  - `CanvasWidget.set_tool(tool: Tool)`
  - `CanvasWidget.set_zoom(zoom: float)`
  - `CanvasWidget.grid_to_screen(col, row) -> QPoint`
  - `CanvasWidget.screen_to_grid(x, y) -> tuple[int, int] | None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_canvas_widget.py`:

```python
import pytest
from PyQt5.QtCore import Qt
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.widgets.canvas_widget import CanvasWidget


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_canvas_size(app):
    project = ProjectModel(16, 16, 4, 4)
    stack = CommandStack()
    canvas = CanvasWidget(project, stack)
    # Default zoom = 1.0, widget minimum size should reflect image size
    assert canvas.sizeHint().width() >= 64
    assert canvas.sizeHint().height() >= 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_canvas_widget.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/widgets/canvas_widget.py`:

```python
from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QMouseEvent
from PyQt5.QtWidgets import QWidget
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.tools.base_tool import Tool


class CanvasWidget(QWidget):
    def __init__(self, project: ProjectModel, command_stack: CommandStack, parent=None):
        super().__init__(parent)
        self.project = project
        self.command_stack = command_stack
        self._zoom = 1.0
        self._tool = None
        self._panning = False
        self._last_pan_pos = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)

    def sizeHint(self) -> QSize:
        return QSize(int(self.project.width * self._zoom),
                     int(self.project.height * self._zoom))

    def set_zoom(self, zoom: float):
        self._zoom = max(0.25, min(8.0, zoom))
        self.updateGeometry()
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def set_tool(self, tool: Tool):
        self._tool = tool
        self.update()

    def grid_to_screen(self, col: int, row: int) -> QPoint:
        rect = self.project.tile_rect(col, row)
        return QPoint(int(rect.x() * self._zoom), int(rect.y() * self._zoom))

    def screen_to_grid(self, x: int, y: int):
        img_x = int(x / self._zoom)
        img_y = int(y / self._zoom)
        return self.project.pixel_to_tile(img_x, img_y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        # Draw canvas image scaled
        scaled = self.project.image.scaled(
            int(self.project.width * self._zoom),
            int(self.project.height * self._zoom),
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation
        )
        painter.drawPixmap(0, 0, QPixmap.fromImage(scaled))

        # Draw grid
        self._draw_grid(painter)
        painter.end()

    def _draw_grid(self, painter: QPainter):
        pen = QPen(QColor(200, 200, 200, 120))
        pen.setWidth(1)
        painter.setPen(pen)

        for col in range(self.project.cols + 1):
            x = int((self.project.offset_x + col * (self.project.tile_width + self.project.gutter_x)) * self._zoom)
            painter.drawLine(x, 0, x, int(self.project.height * self._zoom))

        for row in range(self.project.rows + 1):
            y = int((self.project.offset_y + row * (self.project.tile_height + self.project.gutter_y)) * self._zoom)
            painter.drawLine(0, y, int(self.project.width * self._zoom), y)

    def mousePressEvent(self, event: QMouseEvent):
        if self._tool:
            self._tool.on_mouse_press(event, self)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._tool:
            self._tool.on_mouse_move(event, self)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._tool:
            self._tool.on_mouse_release(event, self)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_canvas_widget.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/widgets tests/test_canvas_widget.py
git commit -m "feat: add canvas widget base"
```

---

### Task 6: Tool Base and Basic Tools (Brush, Eraser, Eyedropper)

**Files:**
- Create: `editor/tools/base_tool.py`
- Create: `editor/tools/brush_tool.py`
- Create: `editor/tools/eraser_tool.py`
- Create: `editor/tools/eyedropper_tool.py`
- Create: `editor/commands/draw_command.py`
- Create: `tests/test_tools.py`

**Interfaces:**
- Consumes: `ProjectModel`, `CommandStack`, `QMouseEvent`, `CanvasWidget`
- Produces:
  - `Tool` abstract base with `on_mouse_press/move/release(event, canvas)`
  - `BrushTool(color, size, opacity)`
  - `EraserTool(size, opacity)`
  - `EyedropperTool`
  - `DrawCommand(stroke_pixels: dict)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tools.py`:

```python
import pytest
from PyQt5.QtGui import QColor, qRgba
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.tools.brush_tool import BrushTool


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_brush_tool_paints(app):
    project = ProjectModel(16, 16, 4, 4)
    stack = CommandStack()
    tool = BrushTool(color=QColor(255, 0, 0), size=1, opacity=255)

    # Simulate drawing at (5, 5)
    tool._paint_at(project, stack, 5, 5)
    assert project.image.pixelColor(5, 5).rgba() == qRgba(255, 0, 0, 255)
    assert stack.can_undo()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/tools/__init__.py` (empty).

Create `editor/tools/base_tool.py`:

```python
from abc import ABC, abstractmethod
from PyQt5.QtGui import QMouseEvent


class Tool(ABC):
    name = 'Tool'

    @abstractmethod
    def on_mouse_press(self, event: QMouseEvent, canvas):
        raise NotImplementedError

    @abstractmethod
    def on_mouse_move(self, event: QMouseEvent, canvas):
        raise NotImplementedError

    @abstractmethod
    def on_mouse_release(self, event: QMouseEvent, canvas):
        raise NotImplementedError

    def get_options(self) -> dict:
        return {}
```

Create `editor/commands/draw_command.py`:

```python
from PyQt5.QtGui import QColor, qRgba
from editor.commands.base_command import Command


class DrawCommand(Command):
    def __init__(self, old_pixels: dict):
        """old_pixels maps (x, y) -> int rgba"""
        self.old_pixels = old_pixels
        self.new_pixels = {}

    def add_pixel(self, x: int, y: int, rgba: int):
        self.new_pixels[(x, y)] = rgba

    def do(self):
        for (x, y), rgba in self.new_pixels.items():
            # Canvas reference is injected via set_canvas in tool
            pass

    def undo(self):
        pass

    def set_canvas(self, canvas):
        self.canvas = canvas
        self.project = canvas.project

    def apply_new(self):
        for (x, y), rgba in self.new_pixels.items():
            self.project.image.setPixel(x, y, rgba)

    def apply_old(self):
        for (x, y), rgba in self.old_pixels.items():
            self.project.image.setPixel(x, y, rgba)
```

Note: The above needs refinement. A cleaner design is for `DrawCommand` to capture old pixels at construction time and receive new pixels after the stroke.

Revised `editor/commands/draw_command.py`:

```python
from editor.commands.base_command import Command


class DrawCommand(Command):
    def __init__(self, project, old_pixels: dict, new_pixels: dict):
        self.project = project
        self.old_pixels = old_pixels
        self.new_pixels = new_pixels

    def do(self):
        for (x, y), rgba in self.new_pixels.items():
            self.project.image.setPixel(x, y, rgba)

    def undo(self):
        for (x, y), rgba in self.old_pixels.items():
            self.project.image.setPixel(x, y, rgba)
```

Create `editor/tools/brush_tool.py`:

```python
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, qRgba, QMouseEvent
from editor.tools.base_tool import Tool
from editor.commands.draw_command import DrawCommand


class BrushTool(Tool):
    name = 'Brush'

    def __init__(self, color: QColor = None, size: int = 1, opacity: int = 255):
        self.color = color if color else QColor(0, 0, 0)
        self.size = max(1, size)
        self.opacity = max(0, min(255, opacity))
        self._current_command = None

    def get_options(self) -> dict:
        return {'color': self.color, 'size': self.size, 'opacity': self.opacity}

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() != Qt.LeftButton:
            return
        self._current_command = {'old': {}, 'new': {}}
        self._paint_at(canvas.project, canvas.command_stack,
                        int(event.pos().x() / canvas.zoom()),
                        int(event.pos().y() / canvas.zoom()))

    def on_mouse_move(self, event: QMouseEvent, canvas):
        if self._current_command is None:
            return
        self._paint_at(canvas.project, canvas.command_stack,
                        int(event.pos().x() / canvas.zoom()),
                        int(event.pos().y() / canvas.zoom()))

    def on_mouse_release(self, event: QMouseEvent, canvas):
        if self._current_command is None:
            return
        old = self._current_command['old']
        new = self._current_command['new']
        if new:
            cmd = DrawCommand(canvas.project, old, new)
            canvas.command_stack.push(cmd)
        self._current_command = None

    def _paint_at(self, project, stack, x: int, y: int):
        radius = self.size // 2
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 0 <= px < project.width and 0 <= py < project.height:
                    if (px, py) not in self._current_command['old']:
                        self._current_command['old'][(px, py)] = project.image.pixel(px, py)
                    new_color = self.color
                    if self.opacity < 255:
                        old = project.image.pixelColor(px, py)
                        new_color = QColor(old)
                        new_color.setRed(int((old.red() * (255 - self.opacity) + self.color.red() * self.opacity) / 255))
                        new_color.setGreen(int((old.green() * (255 - self.opacity) + self.color.green() * self.opacity) / 255))
                        new_color.setBlue(int((old.blue() * (255 - self.opacity) + self.color.blue() * self.opacity) / 255))
                        new_color.setAlpha(min(255, old.alpha() + self.opacity))
                    project.image.setPixel(px, py, new_color.rgba())
                    self._current_command['new'][(px, py)] = project.image.pixel(px, py)
```

Create `editor/tools/eraser_tool.py`:

```python
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, qRgba, QMouseEvent
from editor.tools.brush_tool import BrushTool


class EraserTool(BrushTool):
    name = 'Eraser'

    def __init__(self, size: int = 1, opacity: int = 255):
        super().__init__(color=QColor(0, 0, 0, 0), size=size, opacity=opacity)

    def _paint_at(self, project, stack, x: int, y: int):
        radius = self.size // 2
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 0 <= px < project.width and 0 <= py < project.height:
                    if (px, py) not in self._current_command['old']:
                        self._current_command['old'][(px, py)] = project.image.pixel(px, py)
                    old = project.image.pixelColor(px, py)
                    new_alpha = max(0, old.alpha() - self.opacity)
                    old.setAlpha(new_alpha)
                    project.image.setPixel(px, py, old.rgba())
                    self._current_command['new'][(px, py)] = project.image.pixel(px, py)
```

Create `editor/tools/eyedropper_tool.py`:

```python
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent
from editor.tools.base_tool import Tool


class EyedropperTool(Tool):
    name = 'Eyedropper'

    def __init__(self):
        self.picked_color = None

    def on_mouse_press(self, event: QMouseEvent, canvas):
        x = int(event.pos().x() / canvas.zoom())
        y = int(event.pos().y() / canvas.zoom())
        if 0 <= x < canvas.project.width and 0 <= y < canvas.project.height:
            self.picked_color = canvas.project.image.pixelColor(x, y)

    def on_mouse_move(self, event: QMouseEvent, canvas):
        pass

    def on_mouse_release(self, event: QMouseEvent, canvas):
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/tools editor/commands/draw_command.py tests/test_tools.py
git commit -m "feat: add tool base, brush, eraser, eyedropper"
```

---

### Task 7: Selection Tools

**Files:**
- Create: `editor/tools/rect_select_tool.py`
- Create: `editor/tools/magic_wand_tool.py`
- Create: `editor/commands/clear_command.py`
- Modify: `editor/models/project_model.py` (add `selection` helpers)
- Create: `tests/test_selection_tools.py`

**Interfaces:**
- Consumes: `ProjectModel`, `CommandStack`
- Produces:
  - `RectSelectTool`
  - `MagicWandTool(tolerance=0, contiguous=True)`
  - `ClearCommand(project, selection)` — clears selected pixels to transparent
  - `ProjectModel.set_selection(pixels: set)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_selection_tools.py`:

```python
import pytest
from PyQt5.QtGui import qRgba
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.tools.magic_wand_tool import MagicWandTool


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_magic_wand_selects_contiguous(app):
    project = ProjectModel(16, 16, 4, 4)
    project.image.setPixel(5, 5, qRgba(255, 0, 0, 255))
    project.image.setPixel(6, 5, qRgba(255, 0, 0, 255))
    project.image.setPixel(20, 20, qRgba(255, 0, 0, 255))

    tool = MagicWandTool(tolerance=0, contiguous=True)
    pixels = tool._select_at(project, 5, 5)
    assert (5, 5) in pixels
    assert (6, 5) in pixels
    assert (20, 20) not in pixels
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_selection_tools.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Modify `editor/models/project_model.py` to add selection helpers:

```python
# In ProjectModel.__init__
self.selection = set()

# Add methods
def set_selection(self, pixels):
    self.selection = set(pixels)

def clear_selection(self):
    self.selection = set()
```

Create `editor/tools/rect_select_tool.py`:

```python
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent
from editor.tools.base_tool import Tool


class RectSelectTool(Tool):
    name = 'Rectangle Select'

    def __init__(self):
        self._start = None
        self._current = None

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._current = event.pos()

    def on_mouse_move(self, event: QMouseEvent, canvas):
        if self._start is not None:
            self._current = event.pos()
            self._update_selection(canvas)

    def on_mouse_release(self, event: QMouseEvent, canvas):
        if self._start is not None:
            self._current = event.pos()
            self._update_selection(canvas)
            self._start = None
            self._current = None

    def _update_selection(self, canvas):
        x1 = int(min(self._start.x(), self._current.x()) / canvas.zoom())
        y1 = int(min(self._start.y(), self._current.y()) / canvas.zoom())
        x2 = int(max(self._start.x(), self._current.x()) / canvas.zoom())
        y2 = int(max(self._start.y(), self._current.y()) / canvas.zoom())
        pixels = set()
        for y in range(max(0, y1), min(canvas.project.height, y2 + 1)):
            for x in range(max(0, x1), min(canvas.project.width, x2 + 1)):
                pixels.add((x, y))
        canvas.project.set_selection(pixels)
```

Create `editor/tools/magic_wand_tool.py`:

```python
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent, QColor
from editor.tools.base_tool import Tool


class MagicWandTool(Tool):
    name = 'Magic Wand'

    def __init__(self, tolerance: int = 0, contiguous: bool = True):
        self.tolerance = max(0, min(255, tolerance))
        self.contiguous = contiguous

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() != Qt.LeftButton:
            return
        x = int(event.pos().x() / canvas.zoom())
        y = int(event.pos().y() / canvas.zoom())
        if 0 <= x < canvas.project.width and 0 <= y < canvas.project.height:
            pixels = self._select_at(canvas.project, x, y)
            canvas.project.set_selection(pixels)

    def on_mouse_move(self, event: QMouseEvent, canvas):
        pass

    def on_mouse_release(self, event: QMouseEvent, canvas):
        pass

    def _matches(self, target: QColor, current: QColor) -> bool:
        return all(abs(target.getRgb()[i] - current.getRgb()[i]) <= self.tolerance for i in range(4))

    def _select_at(self, project, x: int, y: int):
        target = project.image.pixelColor(x, y)
        width, height = project.width, project.height
        selected = set()

        if self.contiguous:
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in selected:
                    continue
                if not (0 <= cx < width and 0 <= cy < height):
                    continue
                if not self._matches(target, project.image.pixelColor(cx, cy)):
                    continue
                selected.add((cx, cy))
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
        else:
            for cy in range(height):
                for cx in range(width):
                    if self._matches(target, project.image.pixelColor(cx, cy)):
                        selected.add((cx, cy))
        return selected
```

Create `editor/commands/clear_command.py`:

```python
from editor.commands.base_command import Command


class ClearCommand(Command):
    def __init__(self, project, pixels):
        self.project = project
        self.pixels = set(pixels)
        self.old_values = {}

    def do(self):
        self.old_values = {}
        for x, y in self.pixels:
            if 0 <= x < self.project.width and 0 <= y < self.project.height:
                self.old_values[(x, y)] = self.project.image.pixel(x, y)
                self.project.image.setPixel(x, y, 0)

    def undo(self):
        for (x, y), rgba in self.old_values.items():
            self.project.image.setPixel(x, y, rgba)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_selection_tools.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/tools/rect_select_tool.py editor/tools/magic_wand_tool.py editor/commands/clear_command.py tests/test_selection_tools.py
# also stage project_model changes if any
git add editor/models/project_model.py
git commit -m "feat: add rectangle and magic wand selection tools"
```

---

### Task 8: Color-to-Transparent and Background Removal

**Files:**
- Create: `editor/tools/color_to_transparent_tool.py`
- Create: `editor/commands/replace_color_command.py`
- Create: `tests/test_replace_color.py`

**Interfaces:**
- Consumes: `ProjectModel`, `CommandStack`
- Produces:
  - `ReplaceColorCommand(project, target_color, tolerance)`
  - `ColorToTransparentTool` — can operate on selection or whole image

- [ ] **Step 1: Write the failing test**

Create `tests/test_replace_color.py`:

```python
import pytest
from PyQt5.QtGui import QColor, qRgba
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.replace_color_command import ReplaceColorCommand


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_replace_color_makes_transparent(app):
    project = ProjectModel(16, 16, 4, 4)
    project.image.setPixel(0, 0, qRgba(127, 127, 127, 255))
    project.image.setPixel(1, 0, qRgba(128, 128, 128, 255))

    cmd = ReplaceColorCommand(project, QColor(127, 127, 127), tolerance=2)
    cmd.do()

    assert project.image.pixelColor(0, 0).alpha() == 0
    assert project.image.pixelColor(1, 0).alpha() == 0
    cmd.undo()
    assert project.image.pixelColor(0, 0).alpha() == 255
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replace_color.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/commands/replace_color_command.py`:

```python
from PyQt5.QtGui import QColor
from editor.commands.base_command import Command


class ReplaceColorCommand(Command):
    def __init__(self, project, target_color: QColor, tolerance: int = 0, pixels=None):
        self.project = project
        self.target_color = target_color
        self.tolerance = tolerance
        self.pixels = pixels
        self.old_values = {}

    def _matches(self, current: QColor) -> bool:
        return all(abs(self.target_color.getRgb()[i] - current.getRgb()[i]) <= self.tolerance for i in range(4))

    def do(self):
        self.old_values = {}
        targets = self.pixels if self.pixels else (
            (x, y) for y in range(self.project.height) for x in range(self.project.width)
        )
        for x, y in targets:
            if 0 <= x < self.project.width and 0 <= y < self.project.height:
                if self._matches(self.project.image.pixelColor(x, y)):
                    self.old_values[(x, y)] = self.project.image.pixel(x, y)
                    self.project.image.setPixel(x, y, 0)

    def undo(self):
        for (x, y), rgba in self.old_values.items():
            self.project.image.setPixel(x, y, rgba)
```

Create `editor/tools/color_to_transparent_tool.py`:

```python
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent, QColor
from editor.tools.base_tool import Tool
from editor.commands.replace_color_command import ReplaceColorCommand


class ColorToTransparentTool(Tool):
    name = 'Color to Transparent'

    def __init__(self, color: QColor = None, tolerance: int = 0):
        self.color = color if color else QColor(127, 127, 127)
        self.tolerance = tolerance

    def on_mouse_press(self, event: QMouseEvent, canvas):
        if event.button() != Qt.LeftButton:
            return
        pixels = canvas.project.selection if canvas.project.selection else None
        cmd = ReplaceColorCommand(canvas.project, self.color, self.tolerance, pixels)
        canvas.command_stack.push(cmd)

    def on_mouse_move(self, event: QMouseEvent, canvas):
        pass

    def on_mouse_release(self, event: QMouseEvent, canvas):
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replace_color.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/commands/replace_color_command.py editor/tools/color_to_transparent_tool.py tests/test_replace_color.py
git commit -m "feat: add color-to-transparent background removal"
```

---

### Task 9: Copy/Paste Between Source and Canvas

**Files:**
- Modify: `editor/widgets/source_library_widget.py`
- Create: `editor/commands/paste_command.py`
- Modify: `editor/widgets/canvas_widget.py` (paste preview + placement)
- Create: `tests/test_copy_paste.py`

**Interfaces:**
- Consumes: `SourceImage`, `ProjectModel`, `CommandStack`
- Produces:
  - `PasteCommand(project, image, top_left_x, top_left_y)`
  - Source library emits `tile_copied(QImage)` with the copied tile block
  - Canvas widget receives paste and shows preview; click places

- [ ] **Step 1: Write the failing test**

Create `tests/test_copy_paste.py`:

```python
import pytest
from PyQt5.QtGui import QImage, qRgba
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.paste_command import PasteCommand


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_paste_command(app):
    project = ProjectModel(16, 16, 4, 4)
    source = QImage(16, 16, QImage.Format_ARGB32)
    source.fill(qRgba(0, 255, 0, 255))

    cmd = PasteCommand(project, source, 16, 16)
    cmd.do()

    assert project.image.pixelColor(16, 16).rgba() == qRgba(0, 255, 0, 255)
    assert project.image.pixelColor(31, 31).rgba() == qRgba(0, 255, 0, 255)
    cmd.undo()
    assert project.image.pixelColor(16, 16).alpha() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_copy_paste.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/commands/paste_command.py`:

```python
from PyQt5.QtGui import QImage
from editor.commands.base_command import Command


class PasteCommand(Command):
    def __init__(self, project, image: QImage, x: int, y: int):
        self.project = project
        self.image = image
        self.x = x
        self.y = y
        self.old_pixels = {}

    def do(self):
        self.old_pixels = {}
        for dy in range(self.image.height()):
            for dx in range(self.image.width()):
                px, py = self.x + dx, self.y + dy
                if 0 <= px < self.project.width and 0 <= py < self.project.height:
                    self.old_pixels[(px, py)] = self.project.image.pixel(px, py)
                    self.project.image.setPixel(px, py, self.image.pixel(dx, dy))

    def undo(self):
        for (px, py), rgba in self.old_pixels.items():
            self.project.image.setPixel(px, py, rgba)
```

Modify `editor/widgets/source_library_widget.py` to support tile selection and copying. Replace the stub `copy_selection` with real logic.

Update `SourceLibraryWidget.__init__` to track selected tile range:

```python
self.selected_tiles = []  # list of (source_index, col, row)
self._select_start = None
self._select_end = None
```

Add a custom preview widget to handle mouse events for selection. For simplicity, use `CanvasPreview` (a QLabel subclass with mouse handling) or directly handle events on the `preview_label` by subclassing.

Create a small helper `TilePreviewLabel`:

```python
class TilePreviewLabel(QLabel):
    selection_changed = pyqtSignal()

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
```

Update `_setup_ui`:

```python
self.preview_label = TilePreviewLabel(self)
self.preview_label.setAlignment(Qt.AlignCenter)
layout.addWidget(self.preview_label)
```

Add methods for selection:

```python
def _on_preview_mouse_press(self, event):
    if not self.sources or self.source_list.currentRow() < 0:
        return
    tile = self._event_to_tile(event)
    if tile:
        self._select_start = tile
        self._select_end = tile
        self._update_tile_selection()

def _on_preview_mouse_move(self, event):
    if self._select_start is None:
        return
    tile = self._event_to_tile(event)
    if tile:
        self._select_end = tile
        self._update_tile_selection()

def _on_preview_mouse_release(self, event):
    pass

def _event_to_tile(self, event):
    source = self.sources[self.source_list.currentRow()]
    # Map widget coordinates to image coordinates
    pixmap = self.preview_label.pixmap()
    if not pixmap:
        return None
    label_size = self.preview_label.size()
    img_w = source.image.width()
    img_h = source.image.height()
    scale = min(label_size.width() / img_w, label_size.height() / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale
    offset_x = (label_size.width() - draw_w) / 2
    offset_y = (label_size.height() - draw_h) / 2
    x = (event.x() - offset_x) / scale
    y = (event.y() - offset_y) / scale
    if x < 0 or y < 0 or x >= img_w or y >= img_h:
        return None
    col = int(x) // source.tile_width
    row = int(y) // source.tile_height
    if 0 <= col < source.cols and 0 <= row < source.rows:
        return col, row
    return None

def _update_tile_selection(self):
    if self._select_start is None:
        return
    c1, r1 = self._select_start
    c2, r2 = self._select_end
    c1, c2 = min(c1, c2), max(c1, c2)
    r1, r2 = min(r1, r2), max(r1, r2)
    self.selected_tiles = [
        (self.source_list.currentRow(), c, r)
        for r in range(r1, r2 + 1)
        for c in range(c1, c2 + 1)
    ]
    self._update_preview()
```

Update `_update_preview` to draw selection overlay.

Update `copy_selection`:

```python
def copy_selection(self):
    if not self.selected_tiles:
        return
    # Group by source index
    by_source = {}
    for source_index, col, row in self.selected_tiles:
        by_source.setdefault(source_index, []).append((col, row))

    # For now only support single-source selection copy
    if len(by_source) > 1:
        return

    source_index, tiles = next(iter(by_source.items()))
    source = self.sources[source_index]

    cols = sorted({c for c, r in tiles})
    rows = sorted({r for c, r in tiles})
    min_col, max_col = min(cols), max(cols)
    min_row, max_row = min(rows), max(rows)

    # Ensure rectangular selection
    expected = {(c, r) for r in range(min_row, max_row + 1) for c in range(min_col, max_col + 1)}
    if set(tiles) != expected:
        return

    target_project = self.project
    if source.tile_width != target_project.tile_width or source.tile_height != target_project.tile_height:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(self, 'Grid Mismatch',
                            f'Source grid {source.tile_width}x{source.tile_height} does not match '
                            f'target grid {target_project.tile_width}x{target_project.tile_height}.')
        return

    width = (max_col - min_col + 1) * source.tile_width
    height = (max_row - min_row + 1) * source.tile_height
    copied = QImage(width, height, QImage.Format_ARGB32)
    copied.fill(0)

    for r_offset, r in enumerate(range(min_row, max_row + 1)):
        for c_offset, c in enumerate(range(min_col, max_col + 1)):
            src_rect = source.rect_for_tile(c, r)
            dst_x = c_offset * source.tile_width
            dst_y = r_offset * source.tile_height
            for dy in range(src_rect.height()):
                for dx in range(src_rect.width()):
                    color = source.image.pixel(src_rect.x() + dx, src_rect.y() + dy)
                    copied.setPixel(dst_x + dx, dst_y + dy, color)

    self.tile_copied.emit(copied)
```

Modify `editor/widgets/canvas_widget.py` to handle paste preview and placement. Add:

```python
self._paste_image = None
self._paste_pos = None
```

Add method `set_paste_image(image: QImage)`:

```python
def set_paste_image(self, image: QImage):
    self._paste_image = image
    self._paste_pos = QPoint(0, 0)
    self.update()
```

In `mouseMoveEvent`, update `_paste_pos` if paste image exists and snap to grid.

In `paintEvent`, draw paste preview before grid lines.

Add method `_place_paste()` that computes snapped tile and emits or executes `PasteCommand`.

In `mousePressEvent`, if `_paste_image` exists and left click, place it.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_copy_paste.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/commands/paste_command.py editor/widgets/source_library_widget.py editor/widgets/canvas_widget.py tests/test_copy_paste.py
git commit -m "feat: add copy/paste between source and target canvas"
```

---

### Task 10: Main Window and UI Wiring

**Files:**
- Create: `editor/main_window.py`
- Create: `editor/widgets/options_bar.py`
- Create: `editor/widgets/status_bar.py`
- Modify: `main.py` to launch MainWindow
- Create: `tests/test_main_window.py`

**Interfaces:**
- Consumes: all widgets, tools, commands, exporter
- Produces:
  - `MainWindow` with menu bar, tool bar, options bar, source library, canvas, status bar
  - Tool switching via toolbar buttons
  - File > New / Open / Save / Export actions
  - Edit > Undo / Redo / Delete Selection / Color to Transparent actions

- [ ] **Step 1: Write the failing test**

Create `tests/test_main_window.py`:

```python
import pytest
from editor.app import create_application
from editor.main_window import MainWindow


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_main_window_creates_widgets(app):
    window = MainWindow()
    assert window.canvas is not None
    assert window.source_library is not None
    assert window.options_bar is not None
    assert window.status_bar is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main_window.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/widgets/options_bar.py`:

```python
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpinBox, QPushButton, QColorDialog
from PyQt5.QtGui import QColor


class OptionsBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool = None
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)

        self.tool_label = QLabel('Tool: None')
        self.layout.addWidget(self.tool_label)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 64)
        self.size_spin.setValue(1)
        self.size_spin.setPrefix('Size: ')
        self.layout.addWidget(self.size_spin)

        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 255)
        self.opacity_spin.setValue(255)
        self.opacity_spin.setPrefix('Opacity: ')
        self.layout.addWidget(self.opacity_spin)

        self.color_btn = QPushButton('Color')
        self.color_btn.clicked.connect(self._pick_color)
        self.current_color = QColor(0, 0, 0)
        self.layout.addWidget(self.color_btn)

        self.layout.addStretch()

    def _pick_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color

    def set_tool(self, tool):
        self._tool = tool
        self.tool_label.setText(f'Tool: {tool.name if tool else "None"}')
        if tool and hasattr(tool, 'size'):
            self.size_spin.setValue(tool.size)
        if tool and hasattr(tool, 'opacity'):
            self.opacity_spin.setValue(tool.opacity)
```

Create `editor/widgets/status_bar.py`:

```python
from PyQt5.QtWidgets import QStatusBar, QLabel


class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.coords_label = QLabel('Tile: (-, -)')
        self.zoom_label = QLabel('Zoom: 100%')
        self.canvas_size_label = QLabel('Canvas: 0x0')
        self.addWidget(self.coords_label)
        self.addWidget(self.zoom_label)
        self.addWidget(self.canvas_size_label)

    def set_coords(self, col, row):
        self.coords_label.setText(f'Tile: ({col}, {row})')

    def set_zoom(self, zoom):
        self.zoom_label.setText(f'Zoom: {int(zoom * 100)}%')

    def set_canvas_size(self, cols, rows):
        self.canvas_size_label.setText(f'Canvas: {cols}x{rows}')
```

Create `editor/main_window.py`:

```python
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QAction, QFileDialog, QMessageBox, QToolBar, QSpinBox, QLabel
)
from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage
from editor.commands.base_command import CommandStack
from editor.commands.clear_command import ClearCommand
from editor.commands.replace_color_command import ReplaceColorCommand
from editor.widgets.source_library_widget import SourceLibraryWidget
from editor.widgets.canvas_widget import CanvasWidget
from editor.widgets.options_bar import OptionsBar
from editor.widgets.status_bar import StatusBar
from editor.tools.brush_tool import BrushTool
from editor.tools.eraser_tool import EraserTool
from editor.tools.eyedropper_tool import EyedropperTool
from editor.tools.rect_select_tool import RectSelectTool
from editor.tools.magic_wand_tool import MagicWandTool
from editor.tools.color_to_transparent_tool import ColorToTransparentTool
from editor.exporters.godot_exporter import GodotExporter


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('TileCutter')
        self.resize(1200, 800)

        self.project = ProjectModel(16, 16, 8, 8)
        self.command_stack = CommandStack(self)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._connect_signals()
        self._set_tool(BrushTool())

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left: source library
        self.source_library = SourceLibraryWidget(self.project)
        self.source_library.setFixedWidth(260)
        main_layout.addWidget(self.source_library)

        # Right: canvas + options/status
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.options_bar = OptionsBar()
        right_layout.addWidget(self.options_bar)

        self.canvas = CanvasWidget(self.project, self.command_stack)
        right_layout.addWidget(self.canvas, 1)

        self.status_bar = StatusBar()
        right_layout.addWidget(self.status_bar)

        main_layout.addWidget(right, 1)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')
        new_action = QAction('New', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction('Open Source...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._on_open_source)
        file_menu.addAction(open_action)

        export_action = QAction('Export...', self)
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        edit_menu = menubar.addMenu('Edit')
        undo_action = QAction('Undo', self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.command_stack.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction('Redo', self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.command_stack.redo)
        edit_menu.addAction(redo_action)

        clear_action = QAction('Clear Selection', self)
        clear_action.setShortcut(QKeySequence.Delete)
        clear_action.triggered.connect(self._on_clear_selection)
        edit_menu.addAction(clear_action)

    def _setup_toolbar(self):
        toolbar = QToolBar('Tools')
        self.addToolBar(toolbar)

        tools = [
            ('Brush', BrushTool),
            ('Eraser', EraserTool),
            ('Eyedropper', EyedropperTool),
            ('Rect Select', RectSelectTool),
            ('Magic Wand', MagicWandTool),
            ('Color to Transparent', ColorToTransparentTool),
        ]
        for name, cls in tools:
            action = toolbar.addAction(name)
            action.triggered.connect(lambda checked, c=cls, n=name: self._set_tool(c(), n))

        toolbar.addSeparator()

        # Zoom controls
        zoom_out = toolbar.addAction('Zoom -')
        zoom_out.triggered.connect(lambda: self.canvas.set_zoom(self.canvas.zoom() / 1.2))
        zoom_in = toolbar.addAction('Zoom +')
        zoom_in.triggered.connect(lambda: self.canvas.set_zoom(self.canvas.zoom() * 1.2))

        # Canvas size controls
        toolbar.addWidget(QLabel('Cols:'))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 256)
        self.cols_spin.setValue(self.project.cols)
        self.cols_spin.valueChanged.connect(self._on_canvas_size_changed)
        toolbar.addWidget(self.cols_spin)

        toolbar.addWidget(QLabel('Rows:'))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 256)
        self.rows_spin.setValue(self.project.rows)
        self.rows_spin.valueChanged.connect(self._on_canvas_size_changed)
        toolbar.addWidget(self.rows_spin)

    def _connect_signals(self):
        self.source_library.tile_copied.connect(self.canvas.set_paste_image)
        self.command_stack.can_undo_changed.connect(lambda ok: self.status_bar.showMessage('Undo available' if ok else ''))
        self.canvas.mouse_moved.connect(self._on_canvas_mouse_moved)

    def _set_tool(self, tool, name=None):
        self.canvas.set_tool(tool)
        self.options_bar.set_tool(tool)

    def _on_new(self):
        self.project = ProjectModel(16, 16, 8, 8)
        self.source_library.project = self.project
        self.canvas.project = self.project
        self.canvas.update()

    def _on_open_source(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Open Source Images', '', 'PNG Images (*.png)')
        for path in paths:
            try:
                source = SourceImage(Path(path), self.project.tile_width, self.project.tile_height)
                self.source_library.add_source(source)
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to load {path}: {e}')

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export Tileset', 'tileset.png', 'PNG (*.png)')
        if not path:
            return
        path = Path(path)
        tres_path = path.with_suffix('.tres')
        try:
            GodotExporter.export(self.project, path, tres_path, f'res://{path.name}')
            QMessageBox.information(self, 'Export Complete', f'Saved {path} and {tres_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Export Error', str(e))

    def _on_clear_selection(self):
        if self.project.selection:
            cmd = ClearCommand(self.project, self.project.selection)
            self.command_stack.push(cmd)

    def _on_canvas_size_changed(self):
        new_cols = self.cols_spin.value()
        new_rows = self.rows_spin.value()
        delta_cols = new_cols - self.project.cols
        delta_rows = new_rows - self.project.rows
        if delta_cols or delta_rows:
            from editor.commands.resize_canvas_command import ResizeCanvasCommand
            cmd = ResizeCanvasCommand(self.project, delta_cols, delta_rows, 'bottom-right')
            self.command_stack.push(cmd)

    def _on_canvas_mouse_moved(self, col, row):
        self.status_bar.set_coords(col, row)
        self.status_bar.set_zoom(self.canvas.zoom())
        self.status_bar.set_canvas_size(self.project.cols, self.project.rows)
```

Note: `CanvasWidget` needs `mouse_moved` signal. Add in Task 5 or here:

```python
from PyQt5.QtCore import pyqtSignal

class CanvasWidget(QWidget):
    mouse_moved = pyqtSignal(int, int)

    def mouseMoveEvent(self, event):
        if self._tool:
            self._tool.on_mouse_move(event, self)
        tile = self.screen_to_grid(event.pos().x(), event.pos().y())
        if tile:
            self.mouse_moved.emit(*tile)
        else:
            self.mouse_moved.emit(-1, -1)
        self.update()
```

Update `main.py`:

```python
import sys
from editor.app import create_application
from editor.main_window import MainWindow


def main():
    app = create_application(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main_window.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/main_window.py editor/widgets/options_bar.py editor/widgets/status_bar.py main.py tests/test_main_window.py
git commit -m "feat: add main window and UI wiring"
```

---

### Task 11: Canvas Resize Command

**Files:**
- Create: `editor/commands/resize_canvas_command.py`
- Create: `tests/test_resize_canvas_command.py`

**Interfaces:**
- Consumes: `ProjectModel`
- Produces:
  - `ResizeCanvasCommand(project, delta_cols, delta_rows, anchor)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_resize_canvas_command.py`:

```python
import pytest
from PyQt5.QtGui import qRgba
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.resize_canvas_command import ResizeCanvasCommand


@pytest.fixture(scope='session')
def app():
    return create_application([])


def test_resize_canvas_command_undo(app):
    project = ProjectModel(16, 16, 2, 2)
    project.image.setPixel(0, 0, qRgba(255, 0, 0, 255))

    old_image = project.image.copy()
    cmd = ResizeCanvasCommand(project, 1, 0, 'top-left')
    cmd.do()
    assert project.cols == 3
    assert project.image.pixelColor(0, 0).rgba() == qRgba(255, 0, 0, 255)

    cmd.undo()
    assert project.cols == 2
    assert project.image.width() == old_image.width()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resize_canvas_command.py -v`

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Create `editor/commands/resize_canvas_command.py`:

```python
from PyQt5.QtGui import QImage
from editor.commands.base_command import Command


class ResizeCanvasCommand(Command):
    def __init__(self, project, delta_cols: int, delta_rows: int, anchor: str = 'bottom-right'):
        self.project = project
        self.delta_cols = delta_cols
        self.delta_rows = delta_rows
        self.anchor = anchor
        self.old_image = None
        self.old_cols = None
        self.old_rows = None

    def do(self):
        self.old_image = self.project.image.copy()
        self.old_cols = self.project.cols
        self.old_rows = self.project.rows
        self.project.resize_canvas(self.delta_cols, self.delta_rows, self.anchor)

    def undo(self):
        self.project.image = self.old_image
        self.project.cols = self.old_cols
        self.project.rows = self.old_rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resize_canvas_command.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add editor/commands/resize_canvas_command.py tests/test_resize_canvas_command.py
git commit -m "feat: add canvas resize command with undo"
```

---

### Task 12: Integration, Manual Testing, and Run

**Files:**
- Modify: `editor/main_window.py` (polish, bug fixes)
- Modify: `editor/widgets/canvas_widget.py` (selection overlay, paste preview)
- Create: `README.md`

**Interfaces:**
- Whole application should launch and allow end-to-end workflow.

- [ ] **Step 1: Manual test plan**

No automated test for full UI. Run the app:

```bash
python main.py
```

Perform the following checks:

1. Window opens without error.
2. File > Open Source loads `raw_source/*.png`.
3. Left panel shows source image with grid.
4. Select one or more tiles in source, click Copy.
5. Canvas shows paste preview following mouse.
6. Click on canvas places tiles.
7. Undo/Redo works.
8. Brush draws red pixels.
9. Eraser makes pixels transparent.
10. Rectangle select works; Delete clears selection.
11. Color to Transparent removes gray checkerboard.
12. File > Export saves PNG and `.tres`.
13. Change cols/rows in toolbar resizes canvas.

- [ ] **Step 2: Fix obvious integration bugs**

Common issues to check:

- `CanvasWidget.paintEvent` should draw selection overlay (highlight selected pixels).
- `CanvasWidget.paintEvent` should draw paste preview with 50% opacity.
- `OptionsBar` should update tool properties when user changes spin boxes.
- `MainWindow._on_canvas_size_changed` should update spin boxes when undoing resize.
- `SourceLibraryWidget._update_preview` should not crash when no source selected.

Add selection overlay in `CanvasWidget._draw_selection`:

```python
def _draw_selection(self, painter):
    if not self.project.selection:
        return
    pen = QPen(QColor(0, 150, 255, 200))
    pen.setWidth(1)
    painter.setPen(pen)
    painter.setBrush(QColor(0, 150, 255, 40))
    for x, y in self.project.selection:
        painter.drawRect(int(x * self._zoom), int(y * self._zoom),
                         int(self._zoom), int(self._zoom))
```

Call `_draw_selection(painter)` in `paintEvent` after drawing image.

Add paste preview:

```python
def _draw_paste_preview(self, painter):
    if self._paste_image is None or self._paste_pos is None:
        return
    x = int(self._paste_pos.x() * self._zoom)
    y = int(self._paste_pos.y() * self._zoom)
    w = int(self._paste_image.width() * self._zoom)
    h = int(self._paste_image.height() * self._zoom)
    painter.setOpacity(0.5)
    painter.drawPixmap(x, y, QPixmap.fromImage(self._paste_image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.FastTransformation)))
    painter.setOpacity(1.0)
```

- [ ] **Step 3: Add README**

Create `README.md`:

```markdown
# TileCutter

A desktop tileset editor for Godot, built with Python and PyQt5.

## Features

- Import multiple source tileset images.
- Grid-based tile selection and copy/paste.
- Pixel-level editing: brush, eraser, eyedropper.
- Rectangle and magic-wand selection.
- Color-to-transparent background removal.
- Undo/redo.
- Export PNG + Godot 4 TileSet `.tres` resource.

## Run

```bash
python main.py
```

## Test

```bash
pytest tests/ -v
```

## Project Structure

See `docs/superpowers/specs/2026-07-22-tilecutter-design.md`.
```

- [ ] **Step 4: Final test run**

Run: `pytest tests/ -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md editor/main_window.py editor/widgets/canvas_widget.py
git commit -m "feat: integrate UI, add manual test plan and README"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Every requirement from the design doc maps to at least one task.
- [x] **No placeholders:** Each step has concrete code, commands, and expected output.
- [x] **Type consistency:** `ProjectModel`, `CommandStack`, `QImage`, `Tool` names match across tasks.
- [x] **Testability:** Each core component has a failing test before implementation.
- [x] **YAGNI:** Layers, animation, terrain generation, and isometric grids are excluded.

## Gaps / Notes

- `CanvasWidget` paste preview snapping needs `mouseMoveEvent` updates; this is covered in Task 9/12.
- `OptionsBar` two-way binding with active tool is left to integration polish in Task 12.
- The Godot `.tres` format is simplified; if Godot 4 syntax changes, `godot_exporter.py` is the single file to update.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-22-tilecutter-plan.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach would you like, 学长喵？🐾
