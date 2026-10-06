import QtQuick
import ".."

Rectangle {
    id: root

    property string componentTitle: ""
    property string status: "CHECKING" // "READY", "FAILED", "CHECKING"
    property string detail: ""
    property bool isRequired: true

    implicitWidth: 600
    implicitHeight: 64

    radius: Theme.radiusSmall
    color: {
        if (status === "FAILED") return Theme.colorErrorBg
        if (status === "READY") return Theme.surfaceDark
        return Theme.surfaceDark
    }
    border.color: {
        if (status === "FAILED") return Theme.colorError
        if (status === "READY") return Theme.surfaceBorder
        return Theme.colorWarning
    }
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 16

        // Status Icon
        Image {
            id: statusIcon
            width: 32
            height: 32
            anchors.verticalCenter: parent.verticalCenter
            fillMode: Image.PreserveAspectFit
            source: {
                if (root.status === "READY") return "../assets/icons/check.svg"
                if (root.status === "FAILED") return "../assets/icons/cross.svg"
                return "../assets/icons/checking.svg"
            }
        }

        // Title and Detail Column
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            width: parent.width - statusIcon.width - badgeRect.width - 48

            Text {
                text: root.componentTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.bold: true
                elide: Text.ElideRight
                width: parent.width
            }

            Text {
                text: root.detail
                color: root.status === "FAILED" ? "#FCA5A5" : Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                elide: Text.ElideRight
                width: parent.width
                visible: root.detail !== ""
            }
        }

        // Badge on right
        Rectangle {
            id: badgeRect
            anchors.verticalCenter: parent.verticalCenter
            height: 36
            width: Math.max(90, badgeText.implicitWidth + 24)
            radius: Theme.radiusSmall
            color: {
                if (root.status === "READY") return Theme.colorSuccess
                if (root.status === "FAILED") return Theme.colorError
                return Theme.colorWarning
            }

            Text {
                id: badgeText
                anchors.centerIn: parent
                text: {
                    if (root.status === "READY") return "TAYYOR"
                    if (root.status === "FAILED") return "NOSOZ"
                    return "TEKSHIRUV..."
                }
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                font.bold: true
            }
        }
    }
}
