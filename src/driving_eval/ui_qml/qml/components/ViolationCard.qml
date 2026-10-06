import QtQuick
import ".."

Rectangle {
    id: root

    property string eventId: ""
    property string code: ""
    property string title: ""
    property string screenText: ""
    property string exercise: ""
    property string timestamp: ""
    property int penalty: 0
    property bool isCritical: false
    property bool isSuspect: false

    signal evidenceRequested(string eventId)

    implicitWidth: 700
    implicitHeight: 96
    radius: Theme.radiusMedium
    color: root.isCritical ? Theme.colorCriticalBg : (root.isSuspect ? Theme.surfaceElevated : Theme.surfaceDark)
    border.color: root.isCritical ? Theme.colorCritical : (root.isSuspect ? Theme.colorWarning : Theme.surfaceBorder)
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // Left Icon
        Image {
            id: icon
            width: 36
            height: 36
            anchors.verticalCenter: parent.verticalCenter
            fillMode: Image.PreserveAspectFit
            source: {
                if (root.isCritical) return "../assets/icons/cross.svg"
                if (root.isSuspect) return "../assets/icons/alert.svg"
                return "../assets/icons/alert.svg"
            }
        }

        // Information Column
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            width: parent.width - icon.width - badge.width - evidenceBtn.width - 64

            Row {
                spacing: 12
                Text {
                    text: root.code
                    color: Theme.colorAccentHover
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSub
                    font.bold: true
                }
                Text {
                    text: "•  " + root.timestamp + "  •  " + root.exercise
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSub
                }
            }

            Text {
                text: root.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                elide: Text.ElideRight
                width: parent.width
            }

            Text {
                text: root.screenText
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                elide: Text.ElideRight
                width: parent.width
                visible: root.screenText !== ""
            }
        }

        // Penalty Badge
        PenaltyBadge {
            id: badge
            anchors.verticalCenter: parent.verticalCenter
            penalty: root.penalty
            isCritical: root.isCritical
            isSuspect: root.isSuspect
        }

        // View Evidence Button
        BigButton {
            id: evidenceBtn
            anchors.verticalCenter: parent.verticalCenter
            minWidth: 120
            minHeight: 56
            variant: "secondary"
            text: "Dalil"
            iconSource: "../assets/icons/photo.svg"
            onClicked: root.evidenceRequested(root.eventId)
        }
    }
}
