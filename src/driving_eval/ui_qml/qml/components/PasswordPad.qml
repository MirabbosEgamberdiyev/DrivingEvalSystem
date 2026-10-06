import QtQuick
import ".."

Item {
    id: root

    property string currentPin: ""
    property int maxDigits: 4
    property bool hasError: false
    property string errorMessage: ""
    property int lockoutRemaining: 0

    signal pinSubmitted(string pin)
    signal cancelled()

    implicitWidth: 460
    implicitHeight: 520

    Column {
        anchors.centerIn: parent
        spacing: 20

        // PIN Title & Prompt
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.lockoutRemaining > 0 
                ? "BLOKLANDI (" + root.lockoutRemaining + " soniya)" 
                : "ADMIN PIN KODINI KIRITING"
            color: root.lockoutRemaining > 0 ? Theme.colorError : Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontHeadline
            font.bold: true
        }

        // Masked PIN display dots
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 16

            Repeater {
                model: root.maxDigits
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: index < root.currentPin.length ? Theme.colorAccentHover : Theme.surfaceElevated
                    border.color: Theme.surfaceBorder
                    border.width: 2
                }
            }
        }

        // Error message text
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.errorMessage
            color: Theme.colorError
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSub
            visible: root.hasError && root.lockoutRemaining === 0
        }

        // Keypad Grid (3 columns: 1-9, then Clear, 0, Ok)
        Grid {
            id: numGrid
            anchors.horizontalCenter: parent.horizontalCenter
            columns: 3
            spacing: 14
            enabled: root.lockoutRemaining === 0

            // Keys 1 to 9
            Repeater {
                model: [ "1", "2", "3", "4", "5", "6", "7", "8", "9" ]
                BigButton {
                    minWidth: 100
                    minHeight: 72
                    variant: "secondary"
                    text: modelData
                    onClicked: {
                        root.hasError = false
                        if (root.currentPin.length < root.maxDigits) {
                            root.currentPin += modelData
                        }
                    }
                }
            }

            // Clear Button
            BigButton {
                minWidth: 100
                minHeight: 72
                variant: "danger"
                text: "C"
                onClicked: {
                    root.currentPin = ""
                    root.hasError = false
                }
            }

            // Zero Button
            BigButton {
                minWidth: 100
                minHeight: 72
                variant: "secondary"
                text: "0"
                onClicked: {
                    root.hasError = false
                    if (root.currentPin.length < root.maxDigits) {
                        root.currentPin += "0"
                    }
                }
            }

            // Submit Button
            BigButton {
                minWidth: 100
                minHeight: 72
                variant: "success"
                text: "OK"
                enabled: root.currentPin.length === root.maxDigits
                onClicked: {
                    if (root.currentPin.length === root.maxDigits) {
                        root.pinSubmitted(root.currentPin)
                        root.currentPin = ""
                    }
                }
            }
        }

        // Cancel / Back Button
        BigButton {
            anchors.horizontalCenter: parent.horizontalCenter
            minWidth: 180
            minHeight: 56
            variant: "secondary"
            text: "Bekor qilish"
            onClicked: root.cancelled()
        }
    }
}
