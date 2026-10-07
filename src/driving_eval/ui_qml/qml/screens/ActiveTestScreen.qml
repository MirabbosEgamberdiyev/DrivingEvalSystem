import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property int elapsedSeconds: 0
    property real currentSpeed: 0.0
    property string currentExercise: "ESTAKADA"
    property int currentExerciseIdx: 1 // 0 to 7
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

            // Map exercise name to index
            var exUpper = exerciseName.toUpperCase()
            if (exUpper.indexOf("START") !== -1 || exUpper.indexOf("BOSH") !== -1) root.currentExerciseIdx = 0
            else if (exUpper.indexOf("ESTAK") !== -1) root.currentExerciseIdx = 1
            else if (exUpper.indexOf("ZMEI") !== -1 || exUpper.indexOf("ILON") !== -1) root.currentExerciseIdx = 2
            else if (exUpper.indexOf("TURN") !== -1 || exUpper.indexOf("90") !== -1) root.currentExerciseIdx = 3
            else if (exUpper.indexOf("PARALLEL") !== -1) root.currentExerciseIdx = 4
            else if (exUpper.indexOf("GARAG") !== -1 || exUpper.indexOf("BOKS") !== -1) root.currentExerciseIdx = 5
            else if (exUpper.indexOf("STOP") !== -1) root.currentExerciseIdx = 6
            else if (exUpper.indexOf("FINISH") !== -1 || exUpper.indexOf("YAKUN") !== -1) root.currentExerciseIdx = 7
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.backgroundDark
    }

    // --- Top Status Header ---
    Rectangle {
        id: hudHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 64
        color: Theme.surfaceDark
        border.color: Theme.surfaceBorder
        border.width: 1

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Rectangle {
                width: 14
                height: 14
                radius: 7
                color: Theme.colorSuccess
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: Theme.tr("hud_test_active")
                color: Theme.colorSuccess
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBodySmall
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "•  " + backendBridge.carId
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Live Clock / Elapsed Timer
        Row {
            anchors.right: parent.right
            anchors.rightMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            Text {
                text: Theme.tr("hud_time_label")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBodySmall
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
                font.family: "Consolas, Courier, monospace"
                font.pixelSize: Theme.fontTitle
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // --- Exercise Progress Strip (8 Exercises) ---
    Rectangle {
        id: progressStrip
        anchors.top: hudHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 48
        color: Theme.surfaceElevated
        border.color: Theme.surfaceBorder
        border.width: 1

        Row {
            anchors.centerIn: parent
            spacing: Math.max(6, Math.min(16, (parent.width - 780) / 8))

            Repeater {
                model: [
                    { name: "START", idx: 0 },
                    { name: "ESTAKADA", idx: 1 },
                    { name: "ZMEIKA", idx: 2 },
                    { name: "TURN 90°", idx: 3 },
                    { name: "PARALLEL", idx: 4 },
                    { name: "GARAGE", idx: 5 },
                    { name: "STOP", idx: 6 },
                    { name: "FINISH", idx: 7 }
                ]

                delegate: Row {
                    spacing: 4
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: {
                            if (modelData.idx < root.currentExerciseIdx) return "✓"
                            if (modelData.idx === root.currentExerciseIdx) return "●"
                            return "○"
                        }
                        color: {
                            if (modelData.idx < root.currentExerciseIdx) return Theme.colorSuccess
                            if (modelData.idx === root.currentExerciseIdx) return Theme.colorAccentHover
                            return Theme.textMuted
                        }
                        font.pixelSize: 14
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: modelData.name
                        color: {
                            if (modelData.idx < root.currentExerciseIdx) return Theme.textSecondary
                            if (modelData.idx === root.currentExerciseIdx) return "#FFFFFF"
                            return Theme.textMuted
                        }
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        font.bold: modelData.idx === root.currentExerciseIdx
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }

    // --- Center Stage: Live Camera HUD & Speedometer ---
    Item {
        anchors.top: progressStrip.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16

        Row {
            anchors.fill: parent
            spacing: 20

            // Left Panel: Big Speedometer & Penalties Card
            Rectangle {
                width: 280
                height: parent.height
                radius: Theme.radiusMedium
                color: Theme.surfaceDark
                border.color: Theme.surfaceBorder
                border.width: 1

                Column {
                    anchors.centerIn: parent
                    spacing: 20
                    width: parent.width - 32

                    // Exercise Badge
                    Rectangle {
                        width: parent.width
                        height: 48
                        radius: Theme.radiusSmall
                        color: Theme.surfaceElevated
                        border.color: Theme.colorAccent
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: root.currentExercise
                            color: Theme.colorAccentHover
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontHeadline
                            font.bold: true
                        }
                    }

                    // Speedometer Display
                    Column {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 2

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: Math.round(root.currentSpeed).toString()
                            color: root.currentSpeed > 20.0 ? Theme.colorWarning : "#FFFFFF"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontDisplay
                            font.bold: true
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: Theme.tr("hud_speed_unit")
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBodySmall
                            font.bold: true
                        }
                    }

                    // Penalty Counter Pill
                    Rectangle {
                        width: parent.width
                        height: 48
                        radius: Theme.radiusSmall
                        color: root.totalPenalty > 0 ? Theme.colorErrorBg : Theme.surfaceElevated
                        border.color: root.totalPenalty > 0 ? Theme.colorError : Theme.surfaceBorder
                        border.width: 1

                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Text {
                                text: Theme.tr("hud_penalty_label")
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBodySmall
                            }
                            Text {
                                text: Theme.trPlural("penalty_points_plural", root.totalPenalty)
                                color: root.totalPenalty > 0 ? Theme.colorError : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBodySmall
                                font.bold: true
                            }
                        }
                    }
                }
            }

            // Right Panel: Live Camera Feed with BEV HUD Container
            Rectangle {
                width: parent.width - 300
                height: parent.height
                radius: Theme.radiusMedium
                color: "#050811"
                border.color: Theme.surfaceBorder
                border.width: 1
                clip: true

                // Camera feed placeholder simulation / overlay
                Image {
                    id: cameraBg
                    anchors.fill: parent
                    source: "../assets/icons/car.svg"
                    fillMode: Image.PreserveAspectFit
                    opacity: 0.12
                }

                // Grid lines representing Computer Vision BEV Homography
                Canvas {
                    anchors.fill: parent
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.strokeStyle = "rgba(37, 99, 235, 0.25)"
                        ctx.lineWidth = 1.5

                        // Perspective corridor lines
                        ctx.beginPath()
                        ctx.moveTo(width * 0.25, height)
                        ctx.lineTo(width * 0.40, height * 0.45)
                        ctx.stroke()

                        ctx.beginPath()
                        ctx.moveTo(width * 0.75, height)
                        ctx.lineTo(width * 0.60, height * 0.45)
                        ctx.stroke()

                        // Stop line projection
                        ctx.strokeStyle = "rgba(22, 163, 74, 0.4)"
                        ctx.beginPath()
                        ctx.moveTo(width * 0.35, height * 0.65)
                        ctx.lineTo(width * 0.65, height * 0.65)
                        ctx.stroke()
                    }
                }

                // Top Left Camera Tag
                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.margins: 14
                    width: 130
                    height: 32
                    radius: Theme.radiusSmall
                    color: Theme.surfaceDark
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Row {
                        anchors.centerIn: parent
                        spacing: 6
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: Theme.colorSuccess
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: "FRONT CAM • 30 FPS"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }

                // Bottom Overlay: Telemetry Telemetry Strip
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 40
                    color: Theme.surfaceDark
                    opacity: 0.92

                    Row {
                        anchors.centerIn: parent
                        spacing: 24

                        Text { text: "🚗 " + Math.round(root.currentSpeed) + " km/h"; color: Theme.textPrimary; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily }
                        Text { text: "🛰 GPS (14 SAT) ✓"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily }
                        Text { text: "🔌 OBD-II CAN ✓"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily }
                        Text { text: "📷 4/4 SYNC ✓"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily }
                    }
                }
            }
        }
    }

    // --- Bottom Gated Action Bar ---
    BottomBar {
        id: bottomBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        // Prompt when driving
        Text {
            objectName: "movingPrompt"
            anchors.centerIn: parent
            visible: !backendBridge.finishReady
            text: Theme.tr("hud_moving_prompt")
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBodySmall
        }

        // Finish Ready Container (Only visible when finishReady == true!)
        Row {
            objectName: "finishContainer"
            anchors.centerIn: parent
            spacing: 24
            visible: backendBridge.finishReady


            Text {
                text: Theme.tr("hud_finish_prompt")
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
                text: Theme.tr("btn_finish_test")
                anchors.verticalCenter: parent.verticalCenter
                onClicked: root.finishTestClicked()
            }
        }
    }
}
