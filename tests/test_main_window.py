import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox
from editor.app import create_application
from editor.main_window import MainWindow


class _FakeCloseEvent:
    def __init__(self):
        self.accepted = None

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False


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
    tool = window.tools['橡皮擦']
    window._set_tool(tool, '橡皮擦')
    assert window.canvas._tool is tool
    assert '橡皮擦' in window.options_bar.tool_label.text()


def test_export_prompts_for_godot_path(app, tmp_path, monkeypatch):
    """The Godot resource path is user-configurable: _on_export asks for it
    and passes whatever the user enters to the exporter."""
    import editor.main_window as mw

    window = MainWindow()
    png_path = tmp_path / 'tileset.png'

    monkeypatch.setattr(
        mw.QFileDialog, 'getSaveFileName',
        staticmethod(lambda *a, **k: (str(png_path), 'PNG Images (*.png)')))
    # User types a custom resource path in the input dialog (accepted = True).
    monkeypatch.setattr(
        mw.QInputDialog, 'getText',
        staticmethod(lambda *a, **k: ('res://tilesets/custom.png', True)))
    monkeypatch.setattr(mw.QMessageBox, 'information',
                        staticmethod(lambda *a, **k: None))

    captured = {}
    monkeypatch.setattr(
        mw.GodotExporter, 'export',
        staticmethod(lambda project, p, t, tex: captured.update(tex=tex)))

    window._on_export()
    assert captured['tex'] == 'res://tilesets/custom.png'


def test_export_uses_default_when_prompt_cancelled(app, tmp_path, monkeypatch):
    """If the user cancels the input dialog, the default res:// path is used."""
    import editor.main_window as mw

    window = MainWindow()
    png_path = tmp_path / 'tileset.png'

    monkeypatch.setattr(
        mw.QFileDialog, 'getSaveFileName',
        staticmethod(lambda *a, **k: (str(png_path), 'PNG Images (*.png)')))
    # Cancelled -> accepted flag False.
    monkeypatch.setattr(
        mw.QInputDialog, 'getText',
        staticmethod(lambda *a, **k: ('ignored', False)))
    monkeypatch.setattr(mw.QMessageBox, 'information',
                        staticmethod(lambda *a, **k: None))

    captured = {}
    monkeypatch.setattr(
        mw.GodotExporter, 'export',
        staticmethod(lambda project, p, t, tex: captured.update(tex=tex)))

    window._on_export()
    assert captured['tex'] == 'res://tileset.png'


def _push_dummy_command(window):
    """Push a real ResizeCanvasCommand so the stack fires can_undo_changed."""
    window.cols_spin.setValue(window.project.cols + 1)


def test_new_window_is_clean(app):
    window = MainWindow()
    assert window.dirty is False


def test_command_push_marks_dirty(app):
    window = MainWindow()
    assert window.dirty is False
    _push_dummy_command(window)
    assert window.dirty is True


def test_new_project_resets_dirty(app):
    window = MainWindow()
    _push_dummy_command(window)
    assert window.dirty is True
    window._on_new()
    assert window.dirty is False


def test_close_when_clean_accepts(app):
    window = MainWindow()
    event = _FakeCloseEvent()
    window.closeEvent(event)
    assert event.accepted is True


def test_close_dirty_discard_accepts(app, monkeypatch):
    window = MainWindow()
    _push_dummy_command(window)
    monkeypatch.setattr(QMessageBox, 'question',
                        staticmethod(lambda *a, **k: QMessageBox.No))
    event = _FakeCloseEvent()
    window.closeEvent(event)
    assert event.accepted is True


def test_close_dirty_cancel_ignores(app, monkeypatch):
    window = MainWindow()
    _push_dummy_command(window)
    monkeypatch.setattr(QMessageBox, 'question',
                        staticmethod(lambda *a, **k: QMessageBox.Cancel))
    event = _FakeCloseEvent()
    window.closeEvent(event)
    assert event.accepted is False


def test_close_dirty_save_exports_and_accepts(app, monkeypatch):
    window = MainWindow()
    _push_dummy_command(window)
    monkeypatch.setattr(QMessageBox, 'question',
                        staticmethod(lambda *a, **k: QMessageBox.Yes))
    called = []
    window._on_export = lambda: called.append('export')
    event = _FakeCloseEvent()
    window.closeEvent(event)
    assert called == ['export']
    assert event.accepted is True


def test_export_clears_dirty(app, tmp_path, monkeypatch):
    import editor.main_window as mw
    window = MainWindow()
    _push_dummy_command(window)
    assert window.dirty is True

    png_path = tmp_path / 'tileset.png'
    monkeypatch.setattr(
        mw.QFileDialog, 'getSaveFileName',
        staticmethod(lambda *a, **k: (str(png_path), 'PNG Images (*.png)')))
    monkeypatch.setattr(
        mw.QInputDialog, 'getText',
        staticmethod(lambda *a, **k: ('res://tileset.png', True)))
    monkeypatch.setattr(mw.QMessageBox, 'information',
                        staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(mw.GodotExporter, 'export',
                        staticmethod(lambda *a, **k: None))

    window._on_export()
    assert window.dirty is False
