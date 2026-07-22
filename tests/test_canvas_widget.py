import pytest
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