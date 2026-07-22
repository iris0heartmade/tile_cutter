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
