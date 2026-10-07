import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    signal startTestClicked()
    signal backClicked()

    Rectangle {
        anchors.fill: parent
        color: Theme.backgroundDark
    }

    // Top Bar
    TopBar {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: Theme.tr("system_ready_title")
        subtitle: Theme.tr("precheck_passed")
        carId: backendBridge.carId
        showBack: true
        showSettings: false
        onBackClicked: root.backClicked()
    }

    // Center Hero
    Column {
        anchors.centerIn: parent
        spacing: 32
        width: Math.min(parent.width - 64, 820)

        // Green Success Badge Icon
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 100
            height: 100
            radius: 50
            color: Theme.colorSuccessBg
            border.color: Theme.colorSuccess
            border.width: 3

            Image {
                anchors.centerIn: parent
                width: 52
                height: 52
                source: "../assets/icons/check.svg"
                fillMode: Image.PreserveAspectFit
            }
        }

        // Announcement
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 12

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Theme.tr("system_ready_title")
                color: Theme.colorSuccess
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitleLarge
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Theme.tr("system_ready_desc")
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
                wrapMode: Text.WordWrap
            }
        }

        // Action Button
        BigButton {
            anchors.horizontalCenter: parent.horizontalCenter
            minWidth: Theme.buttonLargeWidth + 80
            minHeight: Theme.buttonLargeHeight + 8
            variant: "success"
            iconSource: "../assets/icons/check.svg"
            text: Theme.tr("btn_start_test")
            onClicked: root.startTestClicked()
        }
    }

    // Bottom Bar
    BottomBar {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        Row {
            anchors.centerIn: parent
            spacing: 32

            Text {
                text: "⚠️ " + Theme.tr("system_ready_warning")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
            }
        }
    }
}
