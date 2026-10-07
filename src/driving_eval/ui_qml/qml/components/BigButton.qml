import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root

    property string text: ""
    property string iconSource: ""
    property string variant: "primary" // "primary", "secondary", "success", "danger", "warning"
    property int minWidth: Theme.buttonMinWidth
    property int minHeight: Theme.buttonMinHeight

    signal clicked()

    implicitWidth: Math.max(minWidth, contentRow.implicitWidth + Theme.touchPadding * 2)
    implicitHeight: Math.max(minHeight, contentRow.implicitHeight + Theme.touchPadding * 2)

    // Debounce timer against accidental double taps in vibrating vehicle
    property bool _isDebounced: false
    Timer {
        id: debounceTimer
        interval: Theme.debounceDelayMs
        onTriggered: root._isDebounced = false
    }

    // Color resolution based on variant and state
    readonly property color buttonBgColor: {
        if (!root.enabled) return Theme.colorDisabled
        if (mouseArea.pressed) {
            if (root.variant === "success") return Qt.darker(Theme.colorSuccess, 1.2)
            if (root.variant === "danger") return Qt.darker(Theme.colorError, 1.2)
            if (root.variant === "warning") return Qt.darker(Theme.colorWarning, 1.2)
            if (root.variant === "secondary") return Theme.surfaceDark
            return Qt.darker(Theme.colorAccent, 1.2)
        }
        if (root.variant === "success") return Theme.colorSuccess
        if (root.variant === "danger") return Theme.colorError
        if (root.variant === "warning") return Theme.colorWarning
        if (root.variant === "secondary") return Theme.surfaceElevated
        return Theme.colorAccent
    }

    readonly property color buttonBorderColor: {
        if (!root.enabled) return "transparent"
        if (root.variant === "secondary") return Theme.surfaceBorder
        return "transparent"
    }

    readonly property color labelColor: {
        if (!root.enabled) return Theme.textMuted
        return Theme.textPrimary
    }

    Rectangle {
        id: bgRect
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: root.buttonBgColor
        border.color: root.buttonBorderColor
        border.width: root.variant === "secondary" ? 2 : 0

        scale: mouseArea.pressed ? 0.98 : 1.0
        Behavior on scale { NumberAnimation { duration: Theme.animDurationFast } }
        Behavior on color { ColorAnimation { duration: Theme.animDurationFast } }

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 12

            Image {
                id: btnIcon
                width: 28
                height: 28
                source: root.iconSource
                visible: root.iconSource !== ""
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
            }

            Text {
                id: btnText
                text: root.text
                color: root.labelColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    function triggerClick() {
        if (!root._isDebounced && root.enabled) {
            root._isDebounced = true
            debounceTimer.start()
            root.clicked()
        }
    }

    MouseArea {
        id: mouseArea
        objectName: "mouseArea"
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.triggerClick()
    }
}

