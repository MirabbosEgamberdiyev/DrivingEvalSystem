import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property var resultData: null

    signal viewViolationsClicked()
    signal exportUsbClicked()
    signal homeClicked()

    Connections {
        target: backendBridge
        function onResultReady(data) {
            root.resultData = data
        }
        function onUsbExportFinished(success, message) {
            exportNotify.text = message
            exportNotify.visible = true
            notifyTimer.restart()
        }
    }

    Timer {
        id: notifyTimer
        interval: 4000
        onTriggered: exportNotify.visible = false
    }

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
        title: Theme.tr("result_title")
        subtitle: root.resultData ? (Theme.tr("car_id_label") + " " + (root.resultData.car_id || "CAR-01")) : ""
        carId: backendBridge.carId
        showBack: false
        showSettings: true
        onSettingsClicked: stackView.push("SettingsScreen.qml")
    }

    // Notification toast for USB Export
    Rectangle {
        id: exportNotify
        anchors.top: topBar.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - 48, 700)
        height: 52
        radius: Theme.radiusSmall
        color: Theme.colorSuccess
        visible: false
        z: 50

        property alias text: notifyLabel.text

        Text {
            id: notifyLabel
            anchors.centerIn: parent
            text: ""
            color: "#FFFFFF"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontHeadline
            font.bold: true
        }
    }

    // Main Result Card Container
    Flickable {
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        contentHeight: contentCol.implicitHeight + 20
        clip: true

        Column {
            id: contentCol
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width - 32, 860)
            spacing: 24

            // PASS / FAIL Hero Banner
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                height: 120
                radius: Theme.radiusLarge
                color: (root.resultData && root.resultData.passed) ? Theme.colorSuccessBg : Theme.colorErrorBg
                border.color: (root.resultData && root.resultData.passed) ? Theme.colorSuccess : Theme.colorError
                border.width: 2

                Row {
                    anchors.centerIn: parent
                    spacing: 20

                    Image {
                        width: 56
                        height: 56
                        source: (root.resultData && root.resultData.passed) ? "../assets/icons/check.svg" : "../assets/icons/cross.svg"
                        anchors.verticalCenter: parent.verticalCenter
                        fillMode: Image.PreserveAspectFit
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 4

                        Text {
                            text: (root.resultData && root.resultData.passed) 
                                ? Theme.tr("result_pass")
                                : Theme.tr("result_fail")
                            color: "#FFFFFF"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontTitleLarge
                            font.bold: true
                        }

                        Text {
                            text: (root.resultData && root.resultData.passed) 
                                ? Theme.tr("result_pass_desc")
                                : ((root.resultData && root.resultData.critical_count > 0) 
                                    ? Theme.tr("result_critical_desc") 
                                    : Theme.tr("result_fail_desc"))
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSub
                        }
                    }
                }
            }

            // Score and Stats Grid
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                implicitHeight: statsGrid.implicitHeight + 40
                radius: Theme.radiusMedium
                color: Theme.surfaceDark
                border.color: Theme.surfaceBorder
                border.width: 1

                Grid {
                    id: statsGrid
                    anchors.centerIn: parent
                    columns: 2
                    rowSpacing: 18
                    columnSpacing: 48

                    // Final Score
                    Text { 
                        text: Theme.tr("result_score_label")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontHeadline
                        font.family: Theme.fontFamily 
                    }
                    Text { 
                        text: root.resultData ? (root.resultData.final_score + " / " + root.resultData.start_score) : "0 / 100"
                        color: (root.resultData && root.resultData.passed) ? Theme.colorSuccess : Theme.colorError
                        font.pixelSize: Theme.fontHeadline; font.bold: true; font.family: Theme.fontFamily 
                    }

                    // Total Penalty
                    Text { 
                        text: Theme.tr("result_penalty_deducted")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontHeadline
                        font.family: Theme.fontFamily 
                    }
                    Text { 
                        text: root.resultData 
                            ? ("-" + Theme.trPlural("penalty_points_plural", root.resultData.total_penalty))
                            : "0 ball"
                        color: Theme.textPrimary; font.pixelSize: Theme.fontHeadline; font.bold: true; font.family: Theme.fontFamily 
                    }

                    // Violations Count
                    Text { 
                        text: Theme.tr("result_errors_count")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontHeadline
                        font.family: Theme.fontFamily 
                    }
                    Text { 
                        text: root.resultData 
                            ? Theme.trPlural("errors_count_plural", root.resultData.mistake_count)
                            : "0 ta"
                        color: Theme.textPrimary; font.pixelSize: Theme.fontHeadline; font.bold: true; font.family: Theme.fontFamily 
                    }

                    // Duration
                    Text { 
                        text: Theme.tr("result_duration")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontHeadline
                        font.family: Theme.fontFamily 
                    }
                    Text { 
                        text: root.resultData ? root.resultData.duration_str : "00:00"
                        color: Theme.textPrimary; font.pixelSize: Theme.fontHeadline; font.bold: true; font.family: Theme.fontFamily 
                    }
                }
            }

            // Cryptographic SHA-256 Hash
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                height: 52
                radius: Theme.radiusSmall
                color: Theme.surfaceElevated
                border.color: Theme.surfaceBorder
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 12

                    Text {
                        text: Theme.tr("result_hash_label")
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSub
                    }

                    Text {
                        text: root.resultData ? (root.resultData.hash ? root.resultData.hash.substring(0, 32) + "..." : "n/a") : ""
                        color: Theme.colorAccentHover
                        font.family: "Consolas, Courier, monospace"
                        font.pixelSize: Theme.fontSub
                        font.bold: true
                    }
                }
            }
        }
    }

    // Bottom Navigation Bar
    BottomBar {
        id: bottomBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        Row {
            anchors.centerIn: parent
            spacing: 24

            BigButton {
                minWidth: 260
                minHeight: 64
                variant: "secondary"
                iconSource: "../assets/icons/alert.svg"
                text: Theme.tr("btn_view_violations")
                onClicked: root.viewViolationsClicked()
            }

            BigButton {
                minWidth: 220
                minHeight: 64
                variant: "secondary"
                iconSource: "../assets/icons/usb.svg"
                text: Theme.tr("btn_export_usb")
                onClicked: {
                    backendBridge.exportUsb()
                    root.exportUsbClicked()
                }
            }

            BigButton {
                minWidth: 220
                minHeight: 64
                variant: "primary"
                iconSource: "../assets/icons/car.svg"
                text: Theme.tr("btn_home")
                onClicked: root.homeClicked()
            }
        }
    }
}
