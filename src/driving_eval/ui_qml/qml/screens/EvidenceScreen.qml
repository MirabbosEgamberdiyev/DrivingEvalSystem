import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property string eventId: ""
    property var evidenceData: null
    property string activeTab: "event" // "before", "event", "after", "video"

    signal backClicked()
    signal exportUsbClicked()

    Connections {
        target: backendBridge
        function onEvidenceReady(data) {
            root.evidenceData = data
        }
    }

    Component.onCompleted: {
        if (root.eventId !== "") {
            backendBridge.openEvidence(root.eventId)
        }
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
        title: Theme.tr("evidence_title")
        subtitle: Theme.trf("evidence_subtitle", (root.evidenceData ? root.evidenceData.event_id : root.eventId))
        carId: backendBridge.carId
        showBack: true
        showSettings: false
        onBackClicked: root.backClicked()
    }

    // Main Area: Left Viewer, Right Metadata
    Row {
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        spacing: 16

        // Left Media Box
        Column {
            width: parent.width * 0.65
            height: parent.height
            spacing: 12

            // Tab Selector
            Row {
                spacing: 12
                width: parent.width

                BigButton {
                    minWidth: 130
                    minHeight: 52
                    variant: root.activeTab === "before" ? "primary" : "secondary"
                    text: Theme.tr("evidence_tab_before")
                    onClicked: root.activeTab = "before"
                }

                BigButton {
                    minWidth: 130
                    minHeight: 52
                    variant: root.activeTab === "event" ? "primary" : "secondary"
                    text: Theme.tr("evidence_tab_event")
                    onClicked: root.activeTab = "event"
                }

                BigButton {
                    minWidth: 130
                    minHeight: 52
                    variant: root.activeTab === "after" ? "primary" : "secondary"
                    text: Theme.tr("evidence_tab_after")
                    onClicked: root.activeTab = "after"
                }

                BigButton {
                    minWidth: 130
                    minHeight: 52
                    variant: root.activeTab === "video" ? "primary" : "secondary"
                    iconSource: "../assets/icons/video.svg"
                    text: Theme.tr("evidence_tab_video")
                    onClicked: root.activeTab = "video"
                }
            }

            // Media Preview Frame
            Rectangle {
                width: parent.width
                height: parent.height - 64
                radius: Theme.radiusMedium
                color: Theme.surfaceDark
                border.color: Theme.surfaceBorder
                border.width: 1
                clip: true

                // Media display frame
                Column {
                    anchors.centerIn: parent
                    spacing: 16

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 72
                        height: 72
                        source: root.activeTab === "video" ? "../assets/icons/video.svg" : "../assets/icons/photo.svg"
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: {
                            if (root.activeTab === "video") return "event.mp4"
                            if (root.activeTab === "before") return "before.jpg"
                            if (root.activeTab === "after") return "after.jpg"
                            return "event.jpg"
                        }
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontHeadline
                        font.bold: true
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: Theme.tr("evidence_ring_desc")
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSub
                    }
                }
            }
        }

        // Right Metadata Panel
        Rectangle {
            width: parent.width * 0.35 - 16
            height: parent.height
            radius: Theme.radiusMedium
            color: Theme.surfaceDark
            border.color: Theme.surfaceBorder
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                Text {
                    text: Theme.tr("evidence_meta_title")
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontHeadline
                    font.bold: true
                }

                Rectangle { width: parent.width; height: 1; color: Theme.surfaceBorder }

                Grid {
                    columns: 2
                    rowSpacing: 14
                    columnSpacing: 16
                    width: parent.width

                    Text { text: Theme.tr("evidence_meta_event_id"); color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    Text { text: root.evidenceData ? root.evidenceData.event_id : root.eventId; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                    Text { text: Theme.tr("evidence_meta_rule_code"); color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    Text { text: root.evidenceData ? (root.evidenceData.code || "CONE_TOUCH") : "CONE_TOUCH"; color: Theme.colorAccentHover; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                    Text { text: Theme.tr("evidence_meta_time"); color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    Text { text: root.evidenceData ? (root.evidenceData.timestamp || "00:05") : "00:05"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                    Text { text: Theme.tr("evidence_meta_exercise"); color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    Text { text: root.evidenceData ? (root.evidenceData.exercise || "ZMEIKA") : "ZMEIKA"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                    Text { text: Theme.tr("evidence_meta_speed"); color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    Text { text: "16.4 km/h"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                    Text { text: Theme.tr("evidence_meta_confidence"); color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    Text { text: "94.2% (" + Theme.tr("evidence_status_confirmed") + ")"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                }
            }
        }
    }

    // Bottom Bar
    BottomBar {
        id: bottomBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        Row {
            anchors.centerIn: parent
            spacing: 24

            BigButton {
                minWidth: 200
                minHeight: 64
                variant: "secondary"
                iconSource: "../assets/icons/back.svg"
                text: Theme.tr("btn_back")
                onClicked: root.backClicked()
            }

            BigButton {
                minWidth: 240
                minHeight: 64
                variant: "primary"
                iconSource: "../assets/icons/usb.svg"
                text: Theme.tr("btn_export_usb")
                onClicked: {
                    backendBridge.exportUsb()
                    root.exportUsbClicked()
                }
            }
        }
    }
}
