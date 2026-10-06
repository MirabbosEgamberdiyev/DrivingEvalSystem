import QtQuick
import ".."

Rectangle {
    id: root

    implicitWidth: 1280
    implicitHeight: 88
    color: Theme.surfaceDark
    border.color: Theme.surfaceBorder
    border.width: 1

    default property alias content: container.children

    Item {
        id: container
        anchors.fill: parent
        anchors.margins: 12
    }
}
