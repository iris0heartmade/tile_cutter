from PyQt5.QtGui import qRgba

from editor.commands.base_command import CommandStack
from editor.commands.resize_canvas_command import ResizeCanvasCommand
from editor.models.project_model import ProjectModel

RED = qRgba(255, 0, 0, 255)


def make_project(cols=2, rows=2):
    return ProjectModel(tile_width=8, tile_height=8, cols=cols, rows=rows)


def test_resize_canvas_command_do_increases_cols():
    project = make_project(cols=2, rows=2)
    cmd = ResizeCanvasCommand(project, delta_cols=1, delta_rows=0)
    cmd.do()
    assert project.cols == 3
    assert project.rows == 2
    assert project.width == 3 * 8


def test_resize_canvas_command_undo():
    project = make_project(cols=2, rows=2)
    # Paint a pixel so we can verify content is restored, not just size.
    project.image.setPixel(3, 3, RED)
    old_w, old_h = project.width, project.height

    cmd = ResizeCanvasCommand(project, delta_cols=1, delta_rows=1)
    cmd.do()
    assert project.cols == 3
    assert project.rows == 3

    cmd.undo()
    assert project.cols == 2
    assert project.rows == 2
    assert project.width == old_w
    assert project.height == old_h
    assert project.image.pixel(3, 3) == RED


def test_resize_canvas_command_shrink_does_not_crash():
    project = make_project(cols=3, rows=2)
    project.image.setPixel(1, 1, RED)
    cmd = ResizeCanvasCommand(project, delta_cols=-1, delta_rows=0)
    cmd.do()
    assert project.cols == 2
    assert project.rows == 2
    # Undo restores the wider canvas and its content.
    cmd.undo()
    assert project.cols == 3
    assert project.width == 3 * 8
    assert project.image.pixel(1, 1) == RED


def test_resize_canvas_command_redo_reapplies():
    project = make_project(cols=2, rows=2)
    stack = CommandStack()
    stack.push(ResizeCanvasCommand(project, delta_cols=2, delta_rows=1))
    assert (project.cols, project.rows) == (4, 3)
    stack.undo()
    assert (project.cols, project.rows) == (2, 2)
    stack.redo()
    assert (project.cols, project.rows) == (4, 3)
    assert project.width == 4 * 8
    assert project.height == 3 * 8


def test_resize_canvas_command_shrink_clamps_to_one():
    project = make_project(cols=2, rows=2)
    cmd = ResizeCanvasCommand(project, delta_cols=-5, delta_rows=-5)
    cmd.do()
    assert (project.cols, project.rows) == (1, 1)
    cmd.undo()
    assert (project.cols, project.rows) == (2, 2)
