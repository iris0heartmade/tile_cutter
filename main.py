import sys
from editor.app import create_application
from editor.main_window import MainWindow


def main():
    app = create_application(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
