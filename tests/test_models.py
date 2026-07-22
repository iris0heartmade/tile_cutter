from pathlib import Path
from PIL import Image
from PyQt5.QtCore import QRect
from PyQt5.QtGui import qRgba
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


def test_source_image_offset_gutter(tmp_path):
    # 64x64 image, tile=16, gutter=2, offset=(8, 4)
    # available area: 56 wide x 60 tall, tile pitch 18x18
    # cols = (56 + 2) // 18 = 3, rows = (60 + 2) // 18 = 3
    img = Image.new('RGBA', (64, 64), (0, 255, 0, 255))
    p = tmp_path / 'source_offset.png'
    img.save(p)

    source = SourceImage(p, tile_width=16, tile_height=16,
                         offset_x=8, offset_y=4, gutter_x=2, gutter_y=2)
    assert source.cols == 3
    assert source.rows == 3
    # First tile starts at the offset
    assert source.rect_for_tile(0, 0) == QRect(8, 4, 16, 16)
    # Second tile is one pitch (tile + gutter) further
    assert source.rect_for_tile(1, 1) == QRect(8 + 18, 4 + 18, 16, 16)


def test_project_model_tile_rect():
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=3)
    assert project.tile_rect(0, 0) == QRect(0, 0, 16, 16)
    assert project.tile_rect(1, 2) == QRect(16, 32, 16, 16)


def test_project_model_width_height():
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=4)
    assert project.width == 64
    assert project.height == 64


def test_project_model_pixel_to_tile():
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=4)
    assert project.pixel_to_tile(0, 0) == (0, 0)
    assert project.pixel_to_tile(15, 15) == (0, 0)
    assert project.pixel_to_tile(16, 0) == (1, 0)
    assert project.pixel_to_tile(16, 16) == (1, 1)
    # Negative coordinate is outside the canvas
    assert project.pixel_to_tile(-1, 5) is None
    # Pixel outside the cols/rows bounds (col index 4 for a 4-wide grid)
    assert project.pixel_to_tile(64, 0) is None


def test_project_model_pixel_to_tile_gutter_dead_zone():
    # gutter=4 -> tile pitch is 20; pixels 16..19 in each cell are dead zone
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=4,
                           gutter_x=4, gutter_y=4)
    # Inside the first tile
    assert project.pixel_to_tile(5, 5) == (0, 0)
    # x=17 falls in the horizontal gutter between tile 0 and tile 1
    assert project.pixel_to_tile(17, 5) is None
    # y=17 falls in the vertical gutter
    assert project.pixel_to_tile(5, 17) is None


def test_project_model_resize_canvas():
    project = ProjectModel(tile_width=16, tile_height=16, cols=2, rows=2)
    project.resize_canvas(delta_cols=1, delta_rows=0, anchor='top-left')
    assert project.cols == 3
    assert project.rows == 2
    assert project.image.width() == 48
    assert project.image.height() == 32


def test_project_model_resize_canvas_top_right_preserves_edge():
    # Shrink one column with a top-right anchor: existing content must keep
    # its RIGHT edge visible, not collapse to (0, 0). This is the shrink-path
    # bug where the clamp forced x=0 for right/bottom anchors.
    project = ProjectModel(tile_width=16, tile_height=16, cols=3, rows=2)
    old_w = project.image.width()  # 48
    # Mark the old top-RIGHT pixel so we can track where it lands.
    project.image.setPixel(old_w - 1, 0, qRgba(255, 0, 0, 255))

    project.resize_canvas(delta_cols=-1, delta_rows=0, anchor='top-right')
    new_w = project.image.width()  # 32
    # Right edge preserved: old pixel (old_w-1, 0) now sits at (new_w-1, 0).
    assert project.image.pixelColor(new_w - 1, 0).getRgb() == (255, 0, 0, 255)


def test_project_model_resize_clamps_selection_to_new_bounds():
    # Set up a 3x3 project (3*16 = 48 wide) with selected pixels that span
    # the right and bottom edges. Shrink by 1 column / 1 row so the new
    # canvas is 2x2 (32 wide, valid coords 0..31). The three pixels that
    # fell outside must be dropped; the rest must stay selected.
    project = ProjectModel(tile_width=16, tile_height=16, cols=3, rows=3)

    project.selection = {
        (0, 0),           # stays (top-left corner)
        (16, 16),         # stays (col 1, row 1)
        (31, 31),         # stays (last valid pixel of new canvas)
        (32, 0),          # dropped (was start of column 2, now outside)
        (47, 47),         # dropped (bottom-right corner of old canvas)
        (0, 48),          # dropped (just past bottom edge)
    }

    project.resize_canvas(delta_cols=-1, delta_rows=-1, anchor='top-left')
    assert project.cols == 2
    assert project.rows == 2
    assert project.width == 32
    assert project.height == 32
    assert (0, 0) in project.selection
    assert (16, 16) in project.selection
    assert (31, 31) in project.selection
    assert (32, 0) not in project.selection
    assert (47, 47) not in project.selection
    assert (0, 48) not in project.selection
    # Sanity: selection only contains pixels inside the new canvas.
    for x, y in project.selection:
        assert 0 <= x < project.width
        assert 0 <= y < project.height


def test_project_model_resize_grow_keeps_selection():
    # Growing must not drop any selected pixels.
    project = ProjectModel(tile_width=16, tile_height=16, cols=2, rows=2)
    project.selection = {(0, 0), (15, 15), (16, 16)}
    before = set(project.selection)
    project.resize_canvas(delta_cols=1, delta_rows=1, anchor='top-left')
    assert project.selection == before

