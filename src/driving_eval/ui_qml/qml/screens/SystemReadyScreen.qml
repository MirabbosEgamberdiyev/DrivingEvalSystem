import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    signal startTestClicked()
    signal startTrainingClicked()
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
        spacing: 24
        width: Math.min(parent.width - 64, 820)

        // Green Success Badge Icon
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 88
            height: 88
            radius: 44
            color: Theme.colorSuccessBg
            border.color: Theme.colorSuccess
            border.width: 3

            Image {
                anchors.centerIn: parent
                width: 48
                height: 48
                source: "../assets/icons/check.svg"
                fillMode: Image.PreserveAspectFit
            }
        }

        // Announcement
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

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

        // Action Buttons: Assessment vs Training
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 12
            width: Math.min(parent.width, 560)

            // 1. Official Assessment (Rasmiy Imtihon)
            BigButton {
                width: parent.width
                minHeight: Theme.buttonLargeHeight
                variant: "success"
                iconSource: "../assets/icons/check.svg"
                text: Theme.tr("exam.start_assessment")
                onClicked: {
                    backendBridge.setExamMode("ASSESSMENT")
                    root.startTestClicked()
                }
            }

            // 2. Training / Practice Mode (Mashg'ulot Rejimi)
            BigButton {
                width: parent.width
                minHeight: 56
                variant: "secondary"
                iconSource: "../assets/icons/play.svg"
                text: Theme.tr("exam.start_training")
                onClicked: {
                    backendBridge.setExamMode("TRAINING")
                    root.startTrainingClicked()
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Theme.tr("exam.training_notice")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                horizontalAlignment: Text.AlignHCenter
                width: parent.width - 40
                wrapMode: Text.WordWrap
            }
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
