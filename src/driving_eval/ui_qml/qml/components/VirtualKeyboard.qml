import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    property string currentLayout: "uz-Latn" // "uz-Latn", "uz-Cyrl", "ru"
    property bool isShifted: false
    property string textValue: ""

    signal textChanged(string newText)
    signal enterPressed()
    signal cancelled()

    implicitWidth: 800
    implicitHeight: 320

    // Key definitions for the 3 layouts
    readonly property var layoutLatnRows: [
        [ "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "oʻ", "gʻ" ],
        [ "a", "s", "d", "f", "g", "h", "j", "k", "l", "sh", "ch" ],
        [ "z", "x", "c", "v", "b", "n", "m" ]
    ]

    readonly property var layoutCyrlRows: [
        [ "й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ў", "қ" ],
        [ "ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э", "ғ", "ҳ" ],
        [ "я", "ч", "с", "м", "и", "т", "ь", "б", "ю" ]
    ]

    readonly property var layoutRuRows: [
        [ "й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ъ", "ё" ],
        [ "ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э" ],
        [ "я", "ч", "с", "м", "и", "т", "ь", "б", "ю" ]
    ]

    function getCurrentRows() {
        if (root.currentLayout === "uz-Cyrl") return root.layoutCyrlRows
        if (root.currentLayout === "ru") return root.layoutRuRows
        return root.layoutLatnRows
    }

    function appendChar(c) {
        var charToAppend = root.isShifted ? c.toUpperCase() : c.toLowerCase()
        root.textValue += charToAppend
        root.textChanged(root.textValue)
    }

    function backspace() {
        if (root.textValue.length > 0) {
            root.textValue = root.textValue.substring(0, root.textValue.length - 1)
            root.textChanged(root.textValue)
        }
    }

    function clearText() {
        root.textValue = ""
        root.textChanged(root.textValue)
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.surfaceBackground
        radius: Theme.cardRadius
        border.color: Theme.surfaceBorder
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 8

            // Top control row: Language selector tabs & display preview
            Row {
                width: parent.width
                spacing: 12

                // Language pills
                Row {
                    spacing: 6
                    Rectangle {
                        width: 70
                        height: 38
                        radius: 8
                        color: root.currentLayout === "uz-Latn" ? Theme.colorAccent : Theme.surfaceElevated
                        Text {
                            anchors.centerIn: parent
                            text: "O'ZB"
                            color: root.currentLayout === "uz-Latn" ? "#FFFFFF" : Theme.textSecondary
                            font.bold: true
                            font.pixelSize: 14
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.currentLayout = "uz-Latn"
                        }
                    }
                    Rectangle {
                        width: 70
                        height: 38
                        radius: 8
                        color: root.currentLayout === "uz-Cyrl" ? Theme.colorAccent : Theme.surfaceElevated
                        Text {
                            anchors.centerIn: parent
                            text: "ЎЗБ"
                            color: root.currentLayout === "uz-Cyrl" ? "#FFFFFF" : Theme.textSecondary
                            font.bold: true
                            font.pixelSize: 14
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.currentLayout = "uz-Cyrl"
                        }
                    }
                    Rectangle {
                        width: 70
                        height: 38
                        radius: 8
                        color: root.currentLayout === "ru" ? Theme.colorAccent : Theme.surfaceElevated
                        Text {
                            anchors.centerIn: parent
                            text: "РУС"
                            color: root.currentLayout === "ru" ? "#FFFFFF" : Theme.textSecondary
                            font.bold: true
                            font.pixelSize: 14
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.currentLayout = "ru"
                        }
                    }
                }

                // Text Display Field
                Rectangle {
                    width: parent.width - 240
                    height: 38
                    radius: 8
                    color: Theme.surfaceElevated
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.textValue.length > 0 ? root.textValue : "..."
                        color: root.textValue.length > 0 ? Theme.textPrimary : Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 18
                        elide: Text.ElideLeft
                        width: parent.width - 24
                    }
                }
            }

            // Keyboard rows repeater
            Repeater {
                id: rowsRepeater
                model: root.getCurrentRows()

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 6

                    Repeater {
                        model: modelData
                        Rectangle {
                            width: 52
                            height: 48
                            radius: 8
                            color: keyMouse.pressed ? Theme.surfaceElevated : Theme.cardBackground
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: root.isShifted ? modelData.toUpperCase() : modelData.toLowerCase()
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: 20
                                font.bold: true
                            }

                            MouseArea {
                                id: keyMouse
                                anchors.fill: parent
                                onClicked: root.appendChar(modelData)
                            }
                        }
                    }
                }
            }

            // Bottom action row: Shift, Space, Backspace, Clear, Enter
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8

                // Shift key
                Rectangle {
                    width: 70
                    height: 48
                    radius: 8
                    color: root.isShifted ? Theme.colorAccent : Theme.surfaceElevated
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "⇧ SHIFT"
                        color: root.isShifted ? "#FFFFFF" : Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.isShifted = !root.isShifted
                    }
                }

                // Space bar
                Rectangle {
                    width: 320
                    height: 48
                    radius: 8
                    color: spaceMouse.pressed ? Theme.surfaceElevated : Theme.cardBackground
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "SPACE"
                        color: Theme.textSecondary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    MouseArea {
                        id: spaceMouse
                        anchors.fill: parent
                        onClicked: root.appendChar(" ")
                    }
                }

                // Backspace
                Rectangle {
                    width: 70
                    height: 48
                    radius: 8
                    color: bkMouse.pressed ? Theme.surfaceElevated : Theme.surfaceElevated
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "⌫"
                        color: Theme.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                    }
                    MouseArea {
                        id: bkMouse
                        anchors.fill: parent
                        onClicked: root.backspace()
                    }
                }

                // Clear
                Rectangle {
                    width: 65
                    height: 48
                    radius: 8
                    color: Theme.colorDanger
                    opacity: clrMouse.pressed ? 0.7 : 1.0

                    Text {
                        anchors.centerIn: parent
                        text: "CLR"
                        color: "#FFFFFF"
                        font.pixelSize: 14
                        font.bold: true
                    }
                    MouseArea {
                        id: clrMouse
                        anchors.fill: parent
                        onClicked: root.clearText()
                    }
                }

                // Enter / Submit
                Rectangle {
                    width: 100
                    height: 48
                    radius: 8
                    color: Theme.colorSuccess
                    opacity: okMouse.pressed ? 0.7 : 1.0

                    Text {
                        anchors.centerIn: parent
                        text: "OK"
                        color: "#FFFFFF"
                        font.pixelSize: 16
                        font.bold: true
                    }
                    MouseArea {
                        id: okMouse
                        anchors.fill: parent
                        onClicked: root.enterPressed()
                    }
                }
            }
        }
    }
}
