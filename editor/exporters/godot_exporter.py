from pathlib import Path
from PyQt5.QtCore import QBuffer, QByteArray
from PIL import Image
import io
from editor.models.project_model import ProjectModel


class GodotExporter:
    @staticmethod
    def export(project: ProjectModel, png_path: Path, tres_path: Path, godot_texture_path: str):
        png_path = Path(png_path)
        tres_path = Path(tres_path)

        # Save PNG via PIL to preserve alpha. QImage.save handles the
        # ARGB32/BGRA byte ordering correctly, so round-trip through an
        # in-memory PNG buffer (QBuffer) and re-open with PIL.
        byte_array = QByteArray()
        buf = QBuffer(byte_array)
        buf.open(QBuffer.WriteOnly)
        project.image.save(buf, 'PNG')
        buf.close()
        pil_image = Image.open(io.BytesIO(bytes(byte_array)))
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
