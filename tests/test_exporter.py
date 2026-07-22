from pathlib import Path
from PIL import Image
from PyQt5.QtGui import QImage, qRgba
from editor.models.project_model import ProjectModel
from editor.exporters.godot_exporter import GodotExporter


def test_export_png_and_tres(tmp_path):
    project = ProjectModel(tile_width=16, tile_height=16, cols=2, rows=2)
    project.image.setPixel(0, 0, qRgba(255, 0, 0, 255))

    png_path = tmp_path / 'out.png'
    tres_path = tmp_path / 'out.tres'
    GodotExporter.export(project, png_path, tres_path, 'res://out.png')

    assert png_path.exists()
    assert tres_path.exists()

    text = tres_path.read_text()
    assert '[gd_resource type="TileSet"' in text
    assert 'texture_region_size = Vector2i(16, 16)' in text
    assert 'type="Texture2D" path="res://out.png"' in text


def test_export_png_preserves_rgba(tmp_path):
    project = ProjectModel(tile_width=16, tile_height=16, cols=2, rows=2)
    project.image.setPixel(0, 0, qRgba(255, 0, 0, 255))

    png_path = tmp_path / 'out.png'
    tres_path = tmp_path / 'out.tres'
    GodotExporter.export(project, png_path, tres_path, 'res://out.png')

    saved = Image.open(png_path)
    assert saved.mode == 'RGBA'
    # Red pixel round-trips with full alpha; untouched pixels stay transparent.
    assert saved.getpixel((0, 0)) == (255, 0, 0, 255)
    assert saved.getpixel((1, 1)) == (0, 0, 0, 0)


def test_export_tres_uses_gutter_and_offset(tmp_path):
    project = ProjectModel(tile_width=64, tile_height=64, cols=2, rows=2,
                           offset_x=8, offset_y=4, gutter_x=2, gutter_y=3)

    png_path = tmp_path / 'out.png'
    tres_path = tmp_path / 'out.tres'
    GodotExporter.export(project, png_path, tres_path, 'res://tileset.png')

    text = tres_path.read_text()
    assert 'texture_region_size = Vector2i(64, 64)' in text
    assert 'separation = Vector2i(2, 3)' in text
    assert 'texture_offset = Vector2i(8, 4)' in text
    assert 'sources/0 = SubResource("TileSetAtlasSource_atlas0")' in text

