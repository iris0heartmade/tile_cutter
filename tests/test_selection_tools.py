import pytest
from PyQt5.QtGui import qRgba
from PyQt5.QtCore import QPoint
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.commands.clear_command import ClearCommand
from editor.tools.rect_select_tool import RectSelectTool
from editor.tools.magic_wand_tool import MagicWandTool


class _FakeCanvas:
    """Minimal stand-in for CanvasWidget so we can drive tools without a real widget."""
    def __init__(self, project, zoom=1.0):
        self.project = project
        self._zoom = zoom
        self.command_stack = CommandStack()

    def zoom(self):
        return self._zoom


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


def test_rect_select_tool_update_selection(app):
    project = ProjectModel(16, 16, 4, 4)
    canvas = _FakeCanvas(project, zoom=1.0)
    tool = RectSelectTool()
    # Drag from (2, 3) to (5, 6) in image coords.
    tool._start = QPoint(2, 3)
    tool._current = QPoint(5, 6)
    tool._update_selection(canvas)

    # Selection must contain every pixel inside the rectangle (inclusive).
    assert project.selection == {(x, y) for x in range(2, 6) for y in range(3, 7)}


def test_rect_select_tool_update_selection_handles_reversed_drag(app):
    project = ProjectModel(16, 16, 4, 4)
    canvas = _FakeCanvas(project, zoom=1.0)
    tool = RectSelectTool()
    # Reverse-drag: end is up-left of start.
    tool._start = QPoint(5, 6)
    tool._current = QPoint(2, 3)
    tool._update_selection(canvas)

    assert project.selection == {(x, y) for x in range(2, 6) for y in range(3, 7)}


def test_clear_command_sets_pixels_transparent_and_undoes(app):
    project = ProjectModel(16, 16, 4, 4)
    # Seed several pixels with distinct colors so we can check restoration.
    project.image.setPixel(0, 0, qRgba(255, 0, 0, 255))
    project.image.setPixel(1, 0, qRgba(0, 255, 0, 255))
    project.image.setPixel(2, 3, qRgba(0, 0, 255, 255))

    pixels = {(0, 0), (1, 0), (2, 3)}
    cmd = ClearCommand(project, pixels)
    stack = CommandStack()
    stack.push(cmd)

    # After do(): all selected pixels are transparent (rgba == 0).
    assert project.image.pixel(0, 0) == 0
    assert project.image.pixel(1, 0) == 0
    assert project.image.pixel(2, 3) == 0

    stack.undo()

    # After undo(): original colors restored.
    assert project.image.pixelColor(0, 0).rgba() == qRgba(255, 0, 0, 255)
    assert project.image.pixelColor(1, 0).rgba() == qRgba(0, 255, 0, 255)
    assert project.image.pixelColor(2, 3).rgba() == qRgba(0, 0, 255, 255)