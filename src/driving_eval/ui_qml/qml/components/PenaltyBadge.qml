import QtQuick
import ".."

Rectangle {
    id: root

    property int penalty: 0
    property bool isCritical: false
    property bool isSuspect: false

    implicitHeight: 38
    implicitWidth: Math.max(90, badgeText.implicitWidth + 24)
    radius: Theme.radiusSmall

    color: {
        if (root.isCritical) return Theme.colorCritical
        if (root.isSuspect) return Theme.colorWarning
        if (root.penalty > 0) return Theme.colorError
        return Theme.colorSuccess
    }

    Text {
        id: badgeText
        anchors.centerIn: parent
        text: {
            if (root.isCritical) return "KRITIK XATO"
            if (root.isSuspect) return "SHUBHALI"
            if (root.penalty > 0) return "-" + root.penalty + " BALL"
            return "0 BALL"
        }
        color: "#FFFFFF"
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSub
        font.bold: true
    }
}
