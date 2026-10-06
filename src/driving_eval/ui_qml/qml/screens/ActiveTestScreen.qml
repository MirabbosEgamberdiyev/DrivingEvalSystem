import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property int elapsedSeconds: 0
    property real currentSpeed: 0.0
    property string currentExercise: "BOSHLASH"
    property int totalPenalty: 0
    property int mistakeCount: 0

    signal finishTestClicked()

    Connections {
        target: backendBridge
        function onLiveStatusUpdated(timeSec, speedKmh, exerciseName, penalty, count) {
            root.elapsedSeconds = timeSec
            root.currentSpeed = speedKmh
            root.currentExercise = exerciseName
            root.totalPenalty = penalty
            root.mistakeCount = count
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.backgroundDark
    }

    // --- Minimal Top Status Header ---
    Rectangle {
        id: hudHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 72
        color: Theme.surfaceDark
        border.color: Theme.surfaceBorder
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 14

            Rectangle {
                width: 16
                height: 16
                radius: 8
                color: Theme.colorSuccess
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "TEST JARAYONDA"
                color: Theme.colorSuccess
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Live Clock / Elapsed Timer
        Row {
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Text {
                text: "VAQT:"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: {
                    var m = Math.floor(root.elapsedSeconds / 60)
                    var s = root.elapsedSeconds % 60
                    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s
                }
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitle
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // --- Center HUD: Giant Speed and Exercise Title ---
    Column {
        anchors.centerIn: parent
        spacing: 24
        width: Math.min(parent.width - 64, 880)

        // Exercise Banner
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            height: 60
            width: Math.max(340, exerciseText.implicitWidth + 48)
            radius: Theme.radiusMedium
            color: Theme.surfaceElevated
            border.color: Theme.surfaceBorder
            border.width: 1

            Text {
                id: exerciseText
                anchors.centerIn: parent
                text: root.currentExercise
                color: Theme.colorAccentHover
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }
        }

        // Massive Speed Readout
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 16

            Text {
                text: Math.round(root.currentSpeed).toString()
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontDisplay
                font.bold: true
                anchors.baseline: speedUnit.baseline
            }

            Text {
                id: speedUnit
                text: "km/h"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }
        }

        // Penalty and Mistake Summary Badges
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 32

            Rectangle {
                height: 52
                width: Math.max(180, penText.implicitWidth + 32)
                radius: Theme.radiusSmall
                color: root.totalPenalty > 0 ? Theme.colorErrorBg : Theme.surfaceElevated
                border.color: root.totalPenalty > 0 ? Theme.colorError : Theme.surfaceBorder
                border.width: 1

                Row {
                    id: penText
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        text: "Jarima:"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontHeadline
                    }
                    Text {
                        text: root.totalPenalty + " ball"
                        color: root.totalPenalty > 0 ? Theme.colorError : Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontHeadline
                        font.bold: true
                    }
                }
            }

            Rectangle {
                height: 52
                width: Math.max(180, errText.implicitWidth + 32)
                radius: Theme.radiusSmall
                color: Theme.surfaceElevated
                border.color: Theme.surfaceBorder
                border.width: 1

                Row {
                    id: errText
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        text: "Xatolar:"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontHeadline
                    }
                    Text {
                        text: root.mistakeCount.toString()
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontHeadline
                        font.bold: true
                    }
                }
            }
        }
    }

    // --- Bottom Gated Action Bar ---
    BottomBar {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        // Prompt when driving
        Text {
            anchors.centerIn: parent
            visible: !backendBridge.finishReady
            text: "Mashq bajarilmoqda. Belgilangan chiziqlarga e'tibor bering."
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
        }

        // Finish Ready Container (Only visible when finishReady == true!)
        Row {
            anchors.centerIn: parent
            spacing: 24
            visible: backendBridge.finishReady

            Text {
                text: "Avtomobil to'xtadi. Testni yakunlashingiz mumkin."
                color: Theme.colorSuccess
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            BigButton {
                minWidth: 260
                minHeight: 64
                variant: "danger"
                iconSource: "../assets/icons/finish.svg"
                text: "TESTNI YAKUNLASH"
                anchors.verticalCenter: parent.verticalCenter
                onClicked: root.finishTestClicked()
            }
        }
    }
}
