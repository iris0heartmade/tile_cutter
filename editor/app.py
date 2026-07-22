import sys
from PyQt5.QtWidgets import QApplication


def create_application(argv=None):
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    app.setApplicationName('TileCutter')
    app.setApplicationVersion('0.1.0')
    return app
