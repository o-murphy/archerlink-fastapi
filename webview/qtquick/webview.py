import sys
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWebEngineQuick import QtWebEngineQuick


def main():
    app = QGuiApplication(sys.argv)
    QtWebEngineQuick.initialize()

    engine = QQmlApplicationEngine()
    engine.load('webview.qml')

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
