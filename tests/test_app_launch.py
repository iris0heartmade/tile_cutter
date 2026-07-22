import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt5.QtWidgets import QApplication
from editor.app import create_application
from editor.main_window import MainWindow


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or create_application([])


def test_app_launches_without_exception(app):
    """Smoke test: the full window should construct, show, and process
    events without raising. This exercises the whole widget tree (menus,
    toolbar, options/status bars, source library, canvas) wired together.
    """
    window = MainWindow()
    try:
        window.show()
        # Pump the event loop so any deferred paint/layout work runs.
        app.processEvents()
        assert window.isVisible()
        assert window.canvas is not None
    finally:
        window.close()
