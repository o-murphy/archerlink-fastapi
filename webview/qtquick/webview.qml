import QtQuick 2.15
import QtQuick.Controls 2.15
import QtWebEngine 1.15

ApplicationWindow {
    visible: true
    width: 800
    height: 600

    WebEngineView {
        id: webview
        anchors.fill: parent
        url: "http://127.0.0.1:15010"
    }
}
