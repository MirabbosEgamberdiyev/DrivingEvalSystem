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

    Row {
        anchors.right: parent.right
        anchors.rightMargin: Theme.touchPadding
        anchors.verticalCenter: parent.verticalCenter
        spacing: 16

        // Language Selector Pills
        Row {
            spacing: 6
            anchors.verticalCenter: parent.verticalCenter

            Repeater {
                model: [
                    { code: "uz-Latn", label: "O'ZB" },
                    { code: "uz-Cyrl", label: "ЎЗБ" },
                    { code: "ru",      label: "РУС" }
                ]

                delegate: Rectangle {
                    id: langBtn
                    width: 58
                    height: 40
                    radius: Theme.radiusSmall
                    property bool active: (typeof i18n !== "undefined" && i18n) ? i18n.currentLanguage === modelData.code : false
                    color: active ? Theme.colorAccent : Theme.surfaceElevated
                    border.color: active ? Theme.colorAccentHover : Theme.surfaceBorder
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: langBtn.active ? "#FFFFFF" : Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 15
                        font.bold: true
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

        // Settings Button
        BigButton {
            id: settingsBtn
            visible: root.showSettings
            minWidth: 64
            minHeight: 52
            variant: "secondary"
            iconSource: "../assets/icons/gear.svg"
            text: ""
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.settingsClicked()
        }
    }
}
