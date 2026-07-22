import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt5.QtWidgets import QApplication
from editor.app import create_application
from editor.main_window import MainWindow


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or create_application([])


def test_main_window_creates_widgets(app):
    window = MainWindow()
    assert window.canvas is not None
    assert window.source_library is not None
    assert window.options_bar is not None
    assert window.status_bar is not None


def test_spinbox_resize_pushes_command(app):
    window = MainWindow()
    old_cols = window.project.cols
    window.cols_spin.setValue(old_cols + 2)
    assert window.project.cols == old_cols + 2
    assert window.command_stack.can_undo()
    window.command_stack.undo()
    assert window.project.cols == old_cols


def test_new_project_replaces_model(app):
    window = MainWindow()
    old_project = window.project
    window._on_new()
    assert window.project is not old_project
    assert window.canvas.project is window.project
    assert window.source_library.project is window.project


def test_canvas_mouse_moved_updates_status(app):
    window = MainWindow()
    window._on_canvas_mouse_moved(3, 5)
    assert '3' in window.status_bar.coords_label.text()
    assert '5' in window.status_bar.coords_label.text()


def test_set_tool_updates_canvas_and_options(app):
    window = MainWindow()
    tool = window.tools['Eraser']
    window._set_tool(tool, 'Eraser')
    assert window.canvas._tool is tool
    assert 'Eraser' in window.options_bar.tool_label.text()
