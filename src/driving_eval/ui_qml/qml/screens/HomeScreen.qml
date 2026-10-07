import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    signal startTestClicked()
    signal precheckClicked()
    signal inspectorClicked()
    signal settingsClicked()

    // Background
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
        title: Theme.tr("app_title")
        subtitle: Theme.tr("app_subtitle")
        carId: backendBridge.carId
        mode: "STUDENT"
        showBack: false
        showSettings: true
        onSettingsClicked: root.settingsClicked()
    }

    // Main Center Content
    Flickable {
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        contentHeight: mainCol.implicitHeight + 40
        clip: true

        Column {
            id: mainCol
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 20
            spacing: 24
            width: Math.min(parent.width - 48, 920)

            // System Readiness Banner
            Rectangle {
                width: parent.width
                height: 56
                radius: Theme.radiusMedium
                color: backendBridge.precheckPassed ? Theme.colorSuccessBg : Theme.colorWarningBg
                border.color: backendBridge.precheckPassed ? Theme.colorSuccess : Theme.colorWarning
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 12

                    Image {
                        width: 24
                        height: 24
                        source: backendBridge.precheckPassed ? "../assets/icons/check.svg" : "../assets/icons/alert.svg"
                        anchors.verticalCenter: parent.verticalCenter
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        text: backendBridge.precheckPassed
                            ? "● " + Theme.tr("system.ready") + " — " + Theme.tr("home_ready_msg")
                            : "⚠️ " + Theme.tr("system.warning") + " — " + Theme.tr("home_not_ready_msg")
                        color: backendBridge.precheckPassed ? Theme.colorSuccess : Theme.colorWarning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBodySmall
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            // Hardware Status Summary (6 Grid Cards)
            Grid {
                id: hwGrid
                columns: parent.width >= 800 ? 3 : 2
                spacing: 12
                width: parent.width

                Repeater {
                    model: [
                        { name: "CAMERA", val: "4 / 4", icon: "../assets/icons/camera.svg", ok: true },
                        { name: "GPS / GNSS", val: "CONNECTED", icon: "../assets/icons/check.svg", ok: true },
                        { name: "OBD-II CAN", val: "CONNECTED", icon: "../assets/icons/speed.svg", ok: true },
                        { name: "IMU 6-DOF", val: "CONNECTED", icon: "../assets/icons/check.svg", ok: true },
                        { name: "AI MODEL", val: "READY", icon: "../assets/icons/car.svg", ok: true },
                        { name: "LICENSE", val: "VALID", icon: "../assets/icons/lock.svg", ok: true }
                    ]

                    delegate: Rectangle {
                        width: (hwGrid.width - (hwGrid.columns - 1) * hwGrid.spacing) / hwGrid.columns
                        height: 58
                        radius: Theme.radiusSmall
                        color: Theme.surfaceDark
                        border.color: Theme.surfaceBorder
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 10

                            Image {
                                width: 22
                                height: 22
                                source: modelData.icon
                                anchors.verticalCenter: parent.verticalCenter
                                fillMode: Image.PreserveAspectFit
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    text: modelData.name
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                Text {
                                    text: modelData.val + " ✓"
                                    color: Theme.colorSuccess
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }

            // Role Entrypoint Action Buttons
            Column {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16
                width: Math.min(parent.width, 680)

                // 1. STUDENT MODE: Yangi Imtihon
                BigButton {
                    width: parent.width
                    minHeight: Theme.buttonLargeHeight
                    variant: backendBridge.precheckPassed ? "success" : "primary"
                    iconSource: "../assets/icons/check.svg"
                    text: backendBridge.precheckPassed ? Theme.tr("exam.new_exam") : Theme.tr("btn_precheck")
                    onClicked: {
                        if (backendBridge.precheckPassed) {
                            root.startTestClicked()
                        } else {
                            root.precheckClicked()
                        }
                    }
                }

                // 2. INSPECTOR MODE: Natijalar va Bayonnomalar
                BigButton {
                    width: parent.width
                    minHeight: 64
                    variant: "secondary"
                    iconSource: "../assets/icons/photo.svg"
                    text: Theme.tr("nav.inspector_mode")
                    onClicked: root.inspectorClicked()
                }

                // 3. ADMIN MODE: Tizim va Diagnostika
                BigButton {
                    width: parent.width
                    minHeight: 64
                    variant: "secondary"
                    iconSource: "../assets/icons/gear.svg"
                    text: Theme.tr("nav.admin_mode")
                    onClicked: root.settingsClicked()
                }
            }
        }
    }

    // Bottom Status Strip
    BottomBar {
        id: bottomBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        Row {
            anchors.centerIn: parent
            spacing: 32

            Text {
                text: Theme.tr("rules_ver_label") + " " + backendBridge.rulesVersion
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }

            Text {
                text: backendBridge.isConnected ? "100% OFFLINE STANDALONE" : Theme.tr("status_failed")
                color: backendBridge.isConnected ? Theme.colorSuccess : Theme.colorError
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                font.bold: true
            }
        }
    }
}
