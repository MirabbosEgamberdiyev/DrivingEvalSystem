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

    property string mode: "STUDENT" // STUDENT, INSPECTOR, ADMIN
    property string currentTime: Qt.formatTime(new Date(), "hh:mm")

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            root.currentTime = Qt.formatTime(new Date(), "hh:mm")
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: Theme.touchPadding
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        // Mode Badge
        Rectangle {
            height: 38
            width: modeText.implicitWidth + 24
            radius: Theme.radiusSmall
            color: root.mode === "ADMIN" ? Theme.colorCriticalBg : (root.mode === "INSPECTOR" ? Theme.surfaceElevated : Theme.colorSuccessBg)
            border.color: root.mode === "ADMIN" ? Theme.colorCritical : (root.mode === "INSPECTOR" ? Theme.colorAccent : Theme.colorSuccess)
            border.width: 1
            anchors.verticalCenter: parent.verticalCenter

            Text {
                id: modeText
                anchors.centerIn: parent
                text: root.mode === "ADMIN" ? "ADMIN" : (root.mode === "INSPECTOR" ? "INSPEKTOR" : "STUDENT")
                color: root.mode === "ADMIN" ? Theme.colorError : (root.mode === "INSPECTOR" ? Theme.colorAccentHover : Theme.colorSuccess)
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                font.bold: true
            }
        }

        // Live Clock
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.currentTime
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBodySmall
            font.bold: true
        }

        // Language Selector with Flags
        Row {
            spacing: 6
            anchors.verticalCenter: parent.verticalCenter

            Repeater {
                model: [
                    { code: "uz-Latn", flag: "🇺🇿", label: "O‘zbek" },
                    { code: "uz-Cyrl", flag: "🇺🇿", label: "Ўзбек" },
                    { code: "ru",      flag: "🇷🇺", label: "Русский" }
                ]

                delegate: Rectangle {
                    id: langBtn
                    width: langRow.implicitWidth + 16
                    height: 42
                    radius: Theme.radiusSmall
                    property bool active: (typeof i18n !== "undefined" && i18n) ? i18n.currentLanguage === modelData.code : false
                    color: active ? Theme.colorAccent : Theme.surfaceElevated
                    border.color: active ? Theme.colorAccentHover : Theme.surfaceBorder
                    border.width: 1

                    Row {
                        id: langRow
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: modelData.flag
                            font.pixelSize: 14
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.label
                            color: langBtn.active ? "#FFFFFF" : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (typeof i18n !== "undefined" && i18n) {
                                i18n.set_language(modelData.code)
                            }
                        }
                    }
                }
            }
        }

        // Settings / Admin Button
        BigButton {
            id: settingsBtn
            visible: root.showSettings
            minWidth: 54
            minHeight: 46
            variant: "secondary"
            iconSource: "../assets/icons/gear.svg"
            text: ""
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.settingsClicked()
        }
    }
}
