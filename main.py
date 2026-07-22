import sys
from editor.app import create_application


def main():
    app = create_application(sys.argv)
    # MainWindow will be added in a later task
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
