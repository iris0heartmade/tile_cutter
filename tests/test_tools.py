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