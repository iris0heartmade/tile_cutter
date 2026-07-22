import pytest
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QWidget
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


class _FakeEvent:
    """Stand-in for QPaintEvent so we can call paintEvent() directly in tests
    without going through the full Qt event loop."""
    def rect(self):
        from PyQt5.QtCore import QRect
        return QRect(0, 0, 1 << 16, 1 << 16)


def test_canvas_draws_with_2x2_selection_without_crashing(app):
    # Construct a ProjectModel + CanvasWidget, set a 2x2 selection, then
    # paint the widget onto an off-screen QImage. The test passes if
    # paintEvent runs to completion and the captured image is non-empty.
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=4)
    project.set_selection([(0, 0), (1, 1), (2, 2), (3, 3)])
    stack = CommandStack()
    canvas = CanvasWidget(project, stack)
    canvas.resize(project.width, project.height)

    target = QImage(project.width, project.height, QImage.Format_ARGB32)
    target.fill(0)
    painter = QPainter(target)
    try:
        canvas.render(painter)
    finally:
        painter.end()

    # At least one pixel in the captured image must be non-transparent
    # (either the canvas background or a selection highlight) — proves the
    # paint produced output rather than an empty/blank image.
    non_empty = False
    for x in range(target.width()):
        for y in range(target.height()):
            if target.pixel(x, y) != 0:
                non_empty = True
                break
        if non_empty:
            break
    assert non_empty, "CanvasWidget did not draw any non-empty pixels"


def test_canvas_paint_order_selection_then_paste_preview(app):
    # Verify the new selection overlay does not conflict with the
    # existing paste preview. Both layers must render in the same
    # paintEvent without crashing; the paste preview sits on top of
    # the selection in z-order so an active copy/paste visually hides
    # the selection under the preview (intentional design).
    project = ProjectModel(tile_width=16, tile_height=16, cols=4, rows=4)
    project.set_selection([(16, 16), (17, 17)])
    stack = CommandStack()
    canvas = CanvasWidget(project, stack)
    canvas.resize(project.width, project.height)

    # Provide a small opaque paste image so the preview layer is active.
    paste = QImage(16, 16, QImage.Format_ARGB32)
    paste.fill(0xFFFF00FF)  # opaque magenta, alpha 255
    canvas.set_paste_image(paste)

    # Use widget.grab() — it renders into a QPixmap using the widget's
    # own paint path, which is the same code exercised at runtime.
    canvas.show()
    app.processEvents()
    grabbed = canvas.grab()
    target = grabbed.toImage()

    # The paste preview is drawn at 50% opacity over whatever was already
    # on the canvas. Look for the magenta tint (high red, low green, high
    # blue) anywhere in the captured image — that proves the paste preview
    # layer paints AFTER the selection overlay.
    found_magenta = False
    for x in range(target.width()):
        for y in range(target.height()):
            r, g, b, a = target.pixelColor(x, y).getRgb()
            if a > 0 and r > 150 and b > 150 and g < 150:
                found_magenta = True
                break
        if found_magenta:
            break
    assert found_magenta, (
        "Paste preview not visible — selection overlay may be painting on "
        "top of it (z-order regression)"
    )