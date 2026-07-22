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


def test_brush_get_options_includes_hardness(app):
    tool = BrushTool(color=QColor(0, 0, 0), size=1, opacity=255)
    opts = tool.get_options()
    assert 'hardness' in opts
    assert opts['hardness'] == 100  # default is a hard brush


def test_brush_hardness_defaults_to_hard(app):
    tool = BrushTool()
    assert tool.hardness == 100


def test_low_hardness_paints_softer_edge(app):
    """A low-hardness brush leaves the centre at full strength while the
    outer ring fades to transparent."""
    project = ProjectModel(64, 64, 4, 4)
    stack = CommandStack()
    cx, cy = 32, 32
    radius = 4  # size = 9 -> radius = 4

    soft = BrushTool(color=QColor(255, 0, 0), size=9, opacity=255,
                     hardness=0)
    soft._paint_at(project, stack, cx, cy)

    center_alpha = project.image.pixelColor(cx, cy).alpha()
    edge_alpha = project.image.pixelColor(cx + radius, cy).alpha()
    assert center_alpha == 255                 # centre stays fully opaque
    assert edge_alpha < center_alpha           # edge is softer
    assert edge_alpha == 0                      # edge fades to transparent


def test_high_hardness_paints_uniform(app):
    """A hardness=100 brush is uniform: centre and edge share full alpha."""
    project = ProjectModel(64, 64, 4, 4)
    stack = CommandStack()
    cx, cy = 32, 32
    radius = 4

    hard = BrushTool(color=QColor(255, 0, 0), size=9, opacity=255,
                     hardness=100)
    hard._paint_at(project, stack, cx, cy)

    center_alpha = project.image.pixelColor(cx, cy).alpha()
    edge_alpha = project.image.pixelColor(cx + radius, cy).alpha()
    assert center_alpha == 255
    assert edge_alpha == center_alpha