from pathlib import Path
import pytest
from PIL import Image
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QImage, qRgba, QMouseEvent

from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.models.source_image import SourceImage
from editor.commands.base_command import CommandStack
from editor.commands.paste_command import PasteCommand
from editor.widgets.source_library_widget import SourceLibraryWidget
from editor.widgets.canvas_widget import CanvasWidget


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
    return create_application([])


def _make_left_press(x: int, y: int) -> QMouseEvent:
    return QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(x, y),
                       Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)


def _make_solid_source(tmp_path, w: int, h: int, tile_w: int, tile_h: int,
                       rgba: int, name: str = 'src.png') -> SourceImage:
    img = Image.new('RGBA', (w, h), rgba)
    p = tmp_path / name
    img.save(p)
    return SourceImage(p, tile_w, tile_h)


# ---------------------------------------------------------------------------
# PasteCommand
# ---------------------------------------------------------------------------

def test_paste_command_pastes_pixels(app):
    project = ProjectModel(16, 16, 4, 4)

    # Build a 16x16 green block to paste onto the canvas at (16, 16).
    source = QImage(16, 16, QImage.Format_ARGB32)
    source.fill(qRgba(0, 255, 0, 255))

    cmd = PasteCommand(project, source, 16, 16)
    cmd.do()

    assert project.image.pixelColor(16, 16).rgba() == qRgba(0, 255, 0, 255)
    assert project.image.pixelColor(31, 31).rgba() == qRgba(0, 255, 0, 255)


def test_paste_command_undo_restores_previous_pixels(app):
    project = ProjectModel(16, 16, 4, 4)
    # Seed the paste area with a known red pixel so we can detect restoration.
    project.image.setPixel(20, 20, qRgba(255, 0, 0, 255))

    source = QImage(16, 16, QImage.Format_ARGB32)
    source.fill(qRgba(0, 255, 0, 255))

    cmd = PasteCommand(project, source, 16, 16)
    cmd.do()
    assert project.image.pixelColor(20, 20).rgba() == qRgba(0, 255, 0, 255)

    cmd.undo()
    # (20, 20) returns to the original red; everything else stays transparent.
    assert project.image.pixelColor(20, 20).rgba() == qRgba(255, 0, 0, 255)
    assert project.image.pixelColor(16, 16).alpha() == 0


# ---------------------------------------------------------------------------
# SourceLibraryWidget.copy_selection
# ---------------------------------------------------------------------------

def test_copy_selection_emits_correctly_sized_image(app, tmp_path):
    # Source: 64x64 RGBA, 16x16 tiles (4x4). Fill with a known gradient so we
    # can verify the right pixels end up in the emitted image.
    img = Image.new('RGBA', (64, 64), qRgba(255, 255, 255, 255))
    pixels = img.load()
    for y in range(64):
        for x in range(64):
            pixels[x, y] = (x * 4, y * 4, 0, 255)
    p = tmp_path / 'src.png'
    img.save(p)
    source = SourceImage(p, 16, 16)

    project = ProjectModel(16, 16, 4, 4)
    widget = SourceLibraryWidget(project)
    widget.add_source(source)
    widget._current_source_index = 0

    # Simulate a 2x2 selection from columns 1..2 and rows 1..2.
    widget._select_start = (1, 1)
    widget._select_end = (2, 2)

    captured = []
    widget.tile_copied.connect(lambda img: captured.append(img))

    widget.copy_selection()

    assert len(captured) == 1
    copied = captured[0]
    # Width and height: 2 tiles x 16 px each = 32.
    assert copied.width() == 32
    assert copied.height() == 32
    # Spot-check: the pixel at the top-left of the copied image corresponds
    # to source pixel (16, 16) which was set to (16*4=64, 16*4=64, 0, 255).
    assert copied.pixelColor(0, 0).rgba() == qRgba(64, 64, 0, 255)
    # Bottom-right of the copied image = source pixel (47, 47).
    assert copied.pixelColor(31, 31).rgba() == qRgba(188, 188, 0, 255)


def test_copy_selection_with_scaling(app, tmp_path):
    source = _make_solid_source(tmp_path, w=32, h=32, tile_w=16, tile_h=16,
                                rgba=qRgba(255, 0, 0, 255))

    project = ProjectModel(32, 32, 4, 4)
    widget = SourceLibraryWidget(project)
    widget.add_source(source)
    widget._current_source_index = 0
    widget._select_start = (0, 0)
    widget._select_end = (0, 0)

    widget._sync_mode = False

    captured = []
    widget.tile_copied.connect(lambda img: captured.append(img))

    widget.copy_selection()

    assert len(captured) == 1
    assert captured[0].width() == 32
    assert captured[0].height() == 32


def test_copy_selection_no_selection_does_nothing(app, tmp_path):
    source = _make_solid_source(tmp_path, w=32, h=32, tile_w=16, tile_h=16,
                                rgba=qRgba(0, 0, 255, 255))

    project = ProjectModel(16, 16, 4, 4)
    widget = SourceLibraryWidget(project)
    widget.add_source(source)
    widget._current_source_index = 0

    captured = []
    widget.tile_copied.connect(lambda img: captured.append(img))

    # No selection made.
    widget.copy_selection()
    assert captured == []


# ---------------------------------------------------------------------------
# CanvasWidget.set_paste_image
# ---------------------------------------------------------------------------

def test_canvas_set_paste_image_stores_image(app):
    project = ProjectModel(16, 16, 4, 4)
    stack = CommandStack()
    canvas = CanvasWidget(project, stack)

    paste = QImage(16, 16, QImage.Format_ARGB32)
    paste.fill(qRgba(0, 255, 0, 255))

    canvas.set_paste_image(paste)

    stored = canvas._paste_image
    # The widget may defensively copy the QImage; verify by dimensions and a
    # sample pixel instead of object identity.
    assert stored is not None
    assert stored.width() == paste.width()
    assert stored.height() == paste.height()
    assert stored.pixelColor(0, 0).rgba() == qRgba(0, 255, 0, 255)
    # The preview position resets to the origin so the preview shows
    # somewhere visible until the mouse moves.
    assert canvas._paste_pos == QPoint(0, 0)