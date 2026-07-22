from pathlib import Path
import pytest
from PIL import Image
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