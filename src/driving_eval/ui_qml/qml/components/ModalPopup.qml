import QtQuick
import ".."

Item {
    id: root

    property string title: ""
    property bool visible: false

    signal closed()

    anchors.fill: parent
    visible: false
    z: 100

    // Semi-transparent backdrop
    Rectangle {
        anchors.fill: parent
        color: Theme.overlayBackground

        MouseArea {
            anchors.fill: parent
            // Eat touch events so background cannot be clicked through
            onClicked: {}
        }
    }

    Rectangle {
        id: dialogBox
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 680)
        implicitHeight: dialogColumn.implicitHeight + 48
        radius: Theme.radiusLarge
        color: Theme.surfaceDark
        border.color: Theme.surfaceBorder
        border.width: 2

        Column {
            id: dialogColumn
            anchors.fill: parent
            anchors.margins: 24
            spacing: 20

            Text {
                text: root.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Item {
                id: customContentArea
                width: parent.width
                implicitHeight: 120
            }

            BigButton {
                anchors.right: parent.right
                minWidth: 140
                minHeight: 56
                variant: "secondary"
                text: "Yopish"
                onClicked: {
                    root.visible = false
                    root.closed()
                }
            }
        }
    }
}
