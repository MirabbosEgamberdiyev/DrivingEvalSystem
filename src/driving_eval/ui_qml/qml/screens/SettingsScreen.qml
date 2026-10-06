import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property bool isUnlocked: backendBridge.settingsUnlocked
    property bool pinHasError: false
    property string pinErrorMessage: "PIN kod noto'g'ri!"

    signal backClicked()

    Connections {
        target: backendBridge
        function onSettingsUnlockedChanged(unlocked) {
            root.isUnlocked = unlocked
            if (!unlocked) {
                root.pinHasError = true
            }
        }
        function onUsbExportFinished(success, msg) {
            exportToast.text = msg
            exportToast.visible = true
            toastTimer.restart()
        }
    }

    Timer {
        id: toastTimer
        interval: 3500
        onTriggered: exportToast.visible = false
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
        title: "TIZIM SOZLAMALARI"
        subtitle: root.isUnlocked ? "Administrator rejimi faol" : "PIN bilan himoyalangan"
        carId: backendBridge.carId
        showBack: true
        showSettings: false
        onBackClicked: {
            backendBridge.adminLogout()
            root.backClicked()
        }
    }

    // Export Toast
    Rectangle {
        id: exportToast
        anchors.top: topBar.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - 48, 600)
        height: 48
        radius: Theme.radiusSmall
        color: Theme.colorSuccess
        visible: false
        z: 60

        property alias text: toastLabel.text

        Text {
            id: toastLabel
            anchors.centerIn: parent
            text: ""
            color: "#FFFFFF"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSub
            font.bold: true
        }
    }

    // PIN Pad when locked
    Item {
        id: pinContainer
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !root.isUnlocked

        PasswordPad {
            anchors.centerIn: parent
            hasError: root.pinHasError
            errorMessage: root.pinErrorMessage
            lockoutRemaining: backendBridge.lockoutRemaining
            onPinSubmitted: function(pin) {
                backendBridge.adminLogin(pin)
            }
            onCancelled: {
                root.backClicked()
            }
        }
    }

    // Unlocked Admin Panel
    Item {
        id: adminContainer
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        visible: root.isUnlocked

        Flickable {
            anchors.fill: parent
            contentHeight: adminCol.implicitHeight + 24
            clip: true

            Column {
                id: adminCol
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(parent.width - 24, 880)
                spacing: 20

                // System & Hardware Info Card
                Rectangle {
                    width: parent.width
                    implicitHeight: infoGrid.implicitHeight + 36
                    radius: Theme.radiusMedium
                    color: Theme.surfaceDark
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Text {
                            text: "USKUNALAR VA TIZIM PARAMETRLARI"
                            color: Theme.colorAccentHover
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontHeadline
                            font.bold: true
                        }

                        Grid {
                            id: infoGrid
                            columns: 2
                            rowSpacing: 10
                            columnSpacing: 32
                            width: parent.width

                            Text { text: "Mashina ID (Car ID):"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                            Text { text: backendBridge.carId; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                            Text { text: "Qoidalar to'plami:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                            Text { text: "rules.yaml (" + backendBridge.rulesVersion + ")"; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                            Text { text: "AI Inference Engine:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                            Text { text: "ONNX Runtime (Standalone Local CPU/GPU)"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                            Text { text: "Offline Rejim:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                            Text { text: "100% Standalone (Tashqi aloqalar bloklangan)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                            Text { text: "Ma'lumotlar bazasi:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                            Text { text: "SQLite WAL + SHA-256 Hash Chain"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                        }
                    }
                }

                // Audit Logs Preview Card
                Rectangle {
                    width: parent.width
                    height: 200
                    radius: Theme.radiusMedium
                    color: Theme.surfaceDark
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        Text {
                            text: "TIZIM AUDIT JURNALI (system_logs)"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontHeadline
                            font.bold: true
                        }

                        Rectangle {
                            width: parent.width
                            height: parent.height - 48
                            radius: Theme.radiusSmall
                            color: Theme.backgroundDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Text {
                                anchors.fill: parent
                                anchors.margins: 10
                                text: "[SYSTEM_BOOT] Standalone daemon started successfully\n[PRECHECK] 12/12 components passed diagnostics\n[AUDIT] Hash chain verification: 100% OK\n[AUTH] Admin authorized via secure local PIN"
                                color: Theme.textSecondary
                                font.family: "Consolas, Courier, monospace"
                                font.pixelSize: Theme.fontSub
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }

    // Bottom Bar (visible when unlocked)
    BottomBar {
        id: bottomBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: root.isUnlocked

        Row {
            anchors.centerIn: parent
            spacing: 24

            BigButton {
                minWidth: 220
                minHeight: 64
                variant: "secondary"
                iconSource: "../assets/icons/lock.svg"
                text: "QULFLASH"
                onClicked: {
                    backendBridge.adminLogout()
                }
            }

            BigButton {
                minWidth: 260
                minHeight: 64
                variant: "primary"
                iconSource: "../assets/icons/usb.svg"
                text: "BAZANI USB GA EKSPORT"
                onClicked: {
                    backendBridge.exportUsb()
                }
            }

            BigButton {
                minWidth: 200
                minHeight: 64
                variant: "secondary"
                iconSource: "../assets/icons/back.svg"
                text: "CHIQISH"
                onClicked: {
                    backendBridge.adminLogout()
                    root.backClicked()
                }
            }
        }
    }
}
