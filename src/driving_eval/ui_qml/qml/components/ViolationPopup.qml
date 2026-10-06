import QtQuick
import ".."

Item {
    id: root

    property var queue: []
    property bool isShowing: false
    property var currentItem: null

    signal criticalViolationHandled()

    anchors.fill: parent
    visible: root.isShowing
    z: 200

    Timer {
        id: displayTimer
        interval: Theme.popupDurationMs
        repeat: false
        onTriggered: root.dismissCurrent()
    }

    function enqueue(code, title, screenText, penalty, critical) {
        var item = {
            code: code,
            title: title,
            screenText: screenText,
            penalty: penalty,
            critical: critical
        }
        var newQueue = root.queue.slice()
        newQueue.push(item)
        root.queue = newQueue

        if (!root.isShowing) {
            showNext()
        }
    }

    function showNext() {
        if (root.queue.length === 0) {
            root.isShowing = false
            root.currentItem = null
            return
        }

        var newQueue = root.queue.slice()
        root.currentItem = newQueue.shift()
        root.queue = newQueue
        root.isShowing = true
        displayTimer.restart()
    }

    function dismissCurrent() {
        displayTimer.stop()
        if (root.currentItem && root.currentItem.critical) {
            root.criticalViolationHandled()
        }
        showNext()
    }

    // Semi-transparent backdrop allowing underlying HUD to be faintly visible
    Rectangle {
        anchors.fill: parent
        color: root.currentItem && root.currentItem.critical ? Qt.rgba(0.4, 0.05, 0.05, 0.85) : Qt.rgba(0.04, 0.06, 0.1, 0.75)

        MouseArea {
            anchors.fill: parent
            onClicked: root.dismissCurrent()
        }
    }

    // Popup Card in center
    Rectangle {
        id: popupCard
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 760)
        implicitHeight: contentCol.implicitHeight + 48
        radius: Theme.radiusLarge
        color: root.currentItem && root.currentItem.critical ? Theme.colorCriticalBg : Theme.surfaceDark
        border.color: root.currentItem && root.currentItem.critical ? Theme.colorError : Theme.colorWarning
        border.width: 3

        Column {
            id: contentCol
            anchors.fill: parent
            anchors.margins: 28
            spacing: 18

            // Header Row
            Row {
                spacing: 16
                anchors.horizontalCenter: parent.horizontalCenter

                Image {
                    width: 40
                    height: 40
                    anchors.verticalCenter: parent.verticalCenter
                    fillMode: Image.PreserveAspectFit
                    source: root.currentItem && root.currentItem.critical ? "../assets/icons/cross.svg" : "../assets/icons/alert.svg"
                }

                Text {
                    text: root.currentItem && root.currentItem.critical ? "KRITIK QOIDABUZARLIK!" : "QOIDABUZARLIK QAYD ETILDI"
                    color: root.currentItem && root.currentItem.critical ? Theme.colorError : Theme.colorWarning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontTitle
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // Violation Code
            Text {
                text: root.currentItem ? root.currentItem.code : ""
                color: Theme.colorAccentHover
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // Description / Screen Text
            Text {
                text: root.currentItem ? root.currentItem.screenText : ""
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
                wrapMode: Text.WordWrap
            }

            // Penalty Badge
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16

                PenaltyBadge {
                    penalty: root.currentItem ? root.currentItem.penalty : 0
                    isCritical: root.currentItem ? root.currentItem.critical : false
                }
            }

            // Queue count indicator if multiple violations are queued
            Text {
                text: "Navbatda yana: " + root.queue.length + " ta"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root.queue.length > 0
            }
        }
    }
}
