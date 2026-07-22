import pytest
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QMouseEvent, qRgba
from editor.app import create_application
from editor.models.project_model import ProjectModel
from editor.commands.base_command import CommandStack
from editor.commands.replace_color_command import ReplaceColorCommand
from editor.tools.color_to_transparent_tool import ColorToTransparentTool


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


def _make_left_press(x: int, y: int) -> QMouseEvent:
    """Build a left-button mouse press event at canvas coordinates (x, y)."""
    return QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(x, y),
                       Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)


# --- ReplaceColorCommand ----------------------------------------------------

def test_replace_color_command_replaces_whole_canvas(app):
    project = ProjectModel(16, 16, 4, 4)
    # Seed checkerboard gray (Gemini output background) across the whole canvas.
    gray = qRgba(127, 127, 127, 255)
    for y in range(project.height):
        for x in range(project.width):
            project.image.setPixel(x, y, gray)

    cmd = ReplaceColorCommand(project, QColor(127, 127, 127),
                              QColor(0, 0, 0, 0))
    stack = CommandStack()
    stack.push(cmd)

    # Every pixel should now be fully transparent (0).
    for y in range(project.height):
        for x in range(project.width):
            assert project.image.pixel(x, y) == 0


def test_replace_color_command_undo_restores_originals(app):
    project = ProjectModel(16, 16, 2, 2)
    gray = qRgba(127, 127, 127, 255)
    red = qRgba(255, 0, 0, 255)
    project.image.setPixel(0, 0, gray)
    project.image.setPixel(1, 0, gray)
    project.image.setPixel(0, 1, red)  # non-matching pixel must be preserved
    project.image.setPixel(1, 1, gray)

    cmd = ReplaceColorCommand(project, QColor(127, 127, 127),
                              QColor(0, 0, 0, 0))
    stack = CommandStack()
    stack.push(cmd)

    # The non-matching pixel is preserved (still red).
    assert project.image.pixelColor(0, 1).rgba() == red
    # Matching pixels are transparent.
    assert project.image.pixel(0, 0) == 0

    stack.undo()
    # All originals restored.
    assert project.image.pixelColor(0, 0).rgba() == gray
    assert project.image.pixelColor(1, 0).rgba() == gray
    assert project.image.pixelColor(1, 1).rgba() == gray
    assert project.image.pixelColor(0, 1).rgba() == red


def test_replace_color_command_redo_reapplies(app):
    project = ProjectModel(16, 16, 1, 1)
    project.image.setPixel(0, 0, qRgba(127, 127, 127, 255))

    cmd = ReplaceColorCommand(project, QColor(127, 127, 127),
                              QColor(0, 0, 0, 0))
    stack = CommandStack()
    stack.push(cmd)
    stack.undo()
    stack.redo()
    assert project.image.pixel(0, 0) == 0


def test_replace_color_command_with_tolerance(app):
    project = ProjectModel(16, 16, 1, 1)
    # Seed slightly off-gray pixels: within tolerance of 10.
    project.image.setPixel(0, 0, qRgba(120, 120, 120, 255))  # exact match in tolerance
    project.image.setPixel(1, 0, qRgba(135, 135, 135, 255))  # +8 each channel
    project.image.setPixel(0, 1, qRgba(200, 200, 200, 255))  # way outside tolerance
    project.image.setPixel(1, 1, qRgba(127, 127, 127, 200))  # alpha off by 55

    cmd = ReplaceColorCommand(project, QColor(127, 127, 127),
                              QColor(0, 0, 0, 0), tolerance=10)
    stack = CommandStack()
    stack.push(cmd)

    # (0, 0) and (1, 0) match (within tolerance on RGB), become transparent.
    assert project.image.pixel(0, 0) == 0
    assert project.image.pixel(1, 0) == 0
    # (0, 1) is too bright, untouched.
    assert project.image.pixelColor(0, 1).rgba() == qRgba(200, 200, 200, 255)
    # (1, 1) is off in alpha, untouched at tolerance=10.
    assert project.image.pixelColor(1, 1).rgba() == qRgba(127, 127, 127, 200)


def test_replace_color_command_with_pixels_set(app):
    project = ProjectModel(16, 16, 2, 2)
    gray = qRgba(127, 127, 127, 255)
    project.image.setPixel(0, 0, gray)  # in selection
    project.image.setPixel(1, 0, gray)  # in selection
    project.image.setPixel(0, 1, gray)  # NOT in selection -> untouched
    project.image.setPixel(1, 1, gray)  # NOT in selection -> untouched

    cmd = ReplaceColorCommand(project, QColor(127, 127, 127),
                              QColor(0, 0, 0, 0),
                              pixels={(0, 0), (1, 0)})
    stack = CommandStack()
    stack.push(cmd)

    assert project.image.pixel(0, 0) == 0
    assert project.image.pixel(1, 0) == 0
    # Outside the selection, pixels stay gray.
    assert project.image.pixelColor(0, 1).rgba() == gray
    assert project.image.pixelColor(1, 1).rgba() == gray


# --- ColorToTransparentTool -------------------------------------------------

def test_color_to_transparent_tool_default_color(app):
    tool = ColorToTransparentTool()
    assert tool.color == QColor(127, 127, 127)


def test_color_to_transparent_tool_left_click_pushes_command(app):
    project = ProjectModel(16, 16, 2, 2)
    gray = qRgba(127, 127, 127, 255)
    red = qRgba(255, 0, 0, 255)
    project.image.setPixel(0, 0, gray)
    project.image.setPixel(1, 0, gray)
    project.image.setPixel(0, 1, red)
    project.image.setPixel(1, 1, red)

    canvas = _FakeCanvas(project, zoom=1.0)
    tool = ColorToTransparentTool()
    tool.on_mouse_press(_make_left_press(0, 0), canvas)

    # Whole canvas: gray pixels are now transparent, reds untouched.
    assert project.image.pixel(0, 0) == 0
    assert project.image.pixel(1, 0) == 0
    assert project.image.pixelColor(0, 1).rgba() == red
    assert project.image.pixelColor(1, 1).rgba() == red

    # The command is on the stack and can be undone.
    assert canvas.command_stack.can_undo()
    canvas.command_stack.undo()
    assert project.image.pixelColor(0, 0).rgba() == gray
    assert project.image.pixelColor(1, 0).rgba() == gray


def test_color_to_transparent_tool_right_click_noop(app):
    project = ProjectModel(16, 16, 1, 1)
    project.image.setPixel(0, 0, qRgba(127, 127, 127, 255))

    canvas = _FakeCanvas(project, zoom=1.0)
    tool = ColorToTransparentTool()
    right_click = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(0, 0),
                              Qt.RightButton, Qt.RightButton, Qt.NoModifier)
    tool.on_mouse_press(right_click, canvas)

    # Nothing should have happened.
    assert project.image.pixelColor(0, 0).rgba() == qRgba(127, 127, 127, 255)
    assert not canvas.command_stack.can_undo()


def test_color_to_transparent_tool_with_selection(app):
    project = ProjectModel(16, 16, 2, 2)
    gray = qRgba(127, 127, 127, 255)
    project.image.setPixel(0, 0, gray)  # in selection
    project.image.setPixel(1, 0, gray)  # in selection
    project.image.setPixel(0, 1, gray)  # NOT in selection -> untouched
    project.image.setPixel(1, 1, gray)  # NOT in selection -> untouched

    canvas = _FakeCanvas(project, zoom=1.0)
    project.set_selection({(0, 0), (1, 0)})

    tool = ColorToTransparentTool()
    tool.on_mouse_press(_make_left_press(0, 0), canvas)

    # Only selected pixels were replaced.
    assert project.image.pixel(0, 0) == 0
    assert project.image.pixel(1, 0) == 0
    assert project.image.pixelColor(0, 1).rgba() == gray
    assert project.image.pixelColor(1, 1).rgba() == gray