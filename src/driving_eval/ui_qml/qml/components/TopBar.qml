import QtQuick
import ".."

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property bool showBack: false
    property bool showSettings: true
    property string carId: "CAR-01"

    signal backClicked()
    signal settingsClicked()

    implicitWidth: 1280
    implicitHeight: 76
    color: Theme.surfaceDark
    border.color: Theme.surfaceBorder
    border.width: 1

    Row {
        anchors.left: parent.left
        anchors.leftMargin: Theme.touchPadding
        anchors.verticalCenter: parent.verticalCenter
        spacing: 16

        // Back Button
        BigButton {
            id: backBtn
            visible: root.showBack
            minWidth: 96
            minHeight: 52
            variant: "secondary"
            iconSource: "../assets/icons/back.svg"
            text: ""
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.backClicked()
        }

        Image {
            id: logoIcon
            width: 32
            height: 32
            source: "../assets/icons/car.svg"
            anchors.verticalCenter: parent.verticalCenter
            fillMode: Image.PreserveAspectFit
            visible: !root.showBack
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: root.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
            }

            Text {
                text: root.subtitle
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                visible: root.subtitle !== ""
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: Theme.touchPadding
        anchors.verticalCenter: parent.verticalCenter
        spacing: 16

        // Car ID Badge
        Rectangle {
            height: 40
            width: Math.max(90, carLabel.implicitWidth + 24)
            radius: Theme.radiusSmall
            color: Theme.surfaceElevated
            border.color: Theme.surfaceBorder
            border.width: 1
            anchors.verticalCenter: parent.verticalCenter

            Text {
                id: carLabel
                anchors.centerIn: parent
                text: root.carId
                color: Theme.colorAccentHover
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                font.bold: true
            }
        }

        // Settings Button
        BigButton {
            id: settingsBtn
            visible: root.showSettings
            minWidth: 64
            minHeight: 52
            variant: "secondary"
            iconSource: "../assets/icons/gear.svg"
            text: ""
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.settingsClicked()
        }
    }
}
