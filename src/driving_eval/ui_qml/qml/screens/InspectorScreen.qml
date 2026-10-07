import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    signal backClicked()
    signal viewViolationsClicked(string sessionId)
    signal viewEvidenceClicked(string eventId)

    property var sessions: []
    property string activeFilter: "ALL" // ALL, PASS, FAIL, SUSPECT
    property string searchQuery: ""
    property string toastMessage: ""
    property bool toastVisible: false

    Component.onCompleted: {
        backendBridge.requestSessions()
    }

    Connections {
        target: backendBridge
        function onSessionsListReady(list) {
            root.sessions = list
        }
        function onHashVerificationFinished(sessionId, valid, msg) {
            root.toastMessage = msg
            root.toastVisible = true
            toastTimer.restart()
        }
        function onReportExportFinished(success, msg) {
            root.toastMessage = msg
            root.toastVisible = true
            toastTimer.restart()
        }
    }

    Timer {
        id: toastTimer
        interval: 3500
        onTriggered: root.toastVisible = false
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
        title: Theme.tr("inspector.title")
        subtitle: Theme.tr("inspector.subtitle")
        carId: backendBridge.carId
        mode: "INSPECTOR"
        showBack: true
        showSettings: false
        onBackClicked: root.backClicked()
    }

    // Toast Notification Banner
    Rectangle {
        id: toastBanner
        anchors.top: topBar.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - 48, 700)
        height: 48
        radius: Theme.radiusSmall
        color: Theme.colorSuccess
        visible: root.toastVisible
        z: 90

        Row {
            anchors.centerIn: parent
            spacing: 12
            Image {
                width: 24
                height: 24
                source: "../assets/icons/check.svg"
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
            }
            Text {
                text: root.toastMessage
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBodySmall
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // Main Content
    Column {
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 16

        // Filter Strip & Search Row
        Row {
            width: parent.width
            spacing: 16

            // Filter Chips
            Row {
                spacing: 8
                anchors.verticalCenter: parent.verticalCenter

                Repeater {
                    model: [
                        { key: "ALL", label: Theme.tr("inspector.filter_all") },
                        { key: "PASS", label: Theme.tr("inspector.filter_pass") },
                        { key: "FAIL", label: Theme.tr("inspector.filter_fail") },
                        { key: "SUSPECT", label: Theme.tr("inspector.filter_suspect") }
                    ]

                    delegate: Rectangle {
                        width: chipText.implicitWidth + 28
                        height: 42
                        radius: Theme.radiusSmall
                        property bool active: root.activeFilter === modelData.key
                        color: active ? Theme.colorAccent : Theme.surfaceElevated
                        border.color: active ? Theme.colorAccentHover : Theme.surfaceBorder
                        border.width: 1

                        Text {
                            id: chipText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.active ? "#FFFFFF" : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBodySmall
                            font.bold: true
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.activeFilter = modelData.key
                        }
                    }
                }
            }

            // Refresh Button
            BigButton {
                minWidth: 120
                minHeight: 42
                variant: "secondary"
                iconSource: "../assets/icons/refresh.svg"
                text: Theme.tr("common.refresh")
                anchors.verticalCenter: parent.verticalCenter
                onClicked: backendBridge.requestSessions()
            }
        }

        // Table Header
        Rectangle {
            width: parent.width
            height: 42
            radius: Theme.radiusSmall
            color: Theme.surfaceDark
            border.color: Theme.surfaceBorder
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                Text { text: Theme.tr("inspector.col_session"); width: 140; color: Theme.textMuted; font.bold: true; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                Text { text: Theme.tr("inspector.col_candidate"); width: 220; color: Theme.textMuted; font.bold: true; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                Text { text: Theme.tr("inspector.col_date"); width: 160; color: Theme.textMuted; font.bold: true; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                Text { text: Theme.tr("inspector.col_score"); width: 90; color: Theme.textMuted; font.bold: true; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                Text { text: Theme.tr("inspector.col_status"); width: 120; color: Theme.textMuted; font.bold: true; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                Text { text: Theme.tr("inspector.col_actions"); width: 280; color: Theme.textMuted; font.bold: true; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
            }
        }

        // Sessions List View
        ListView {
            id: sessionsList
            width: parent.width
            height: parent.height - 120
            clip: true
            spacing: 8

            model: {
                if (!root.sessions) return []
                var result = []
                for (var i = 0; i < root.sessions.length; i++) {
                    var s = root.sessions[i]
                    if (root.activeFilter === "PASS" && s.result !== "PASS") continue
                    if (root.activeFilter === "FAIL" && s.result !== "FAIL") continue
                    if (root.activeFilter === "SUSPECT" && (s.suspect_count || 0) === 0) continue
                    result.push(s)
                }
                return result
            }

            delegate: Rectangle {
                width: sessionsList.width
                height: 64
                radius: Theme.radiusSmall
                color: Theme.surfaceDark
                border.color: Theme.surfaceBorder
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 12

                    // Session ID
                    Text {
                        text: modelData.id
                        width: 140
                        color: Theme.colorAccentHover
                        font.family: "Consolas, Courier, monospace"
                        font.pixelSize: Theme.fontBodySmall
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    // Candidate Passport & Name
                    Column {
                        width: 220
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text {
                            text: (modelData.passport_id || "AA1234567")
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBodySmall
                            font.bold: true
                        }
                        Text {
                            text: ((modelData.first_name || "") + " " + (modelData.last_name || ""))
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                        }
                    }

                    // Date & Time
                    Text {
                        text: (modelData.created_at || "2026-10-07 09:00").substring(0, 16)
                        width: 160
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    // Score Badge
                    Text {
                        text: (modelData.final_score !== undefined ? modelData.final_score : 100) + " b"
                        width: 90
                        color: (modelData.result === "PASS") ? Theme.colorSuccess : Theme.colorError
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBodySmall
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    // Verdict Pill
                    Rectangle {
                        width: 100
                        height: 32
                        radius: Theme.radiusSmall
                        color: (modelData.result === "PASS") ? Theme.colorSuccessBg : Theme.colorErrorBg
                        border.color: (modelData.result === "PASS") ? Theme.colorSuccess : Theme.colorError
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: (modelData.result === "PASS") ? "O'TDI" : "YIQILDI"
                            color: (modelData.result === "PASS") ? Theme.colorSuccess : Theme.colorError
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }

                    // Row Action Buttons
                    Row {
                        width: 280
                        spacing: 8
                        anchors.verticalCenter: parent.verticalCenter

                        BigButton {
                            minWidth: 80
                            minHeight: 38
                            variant: "primary"
                            iconSource: "../assets/icons/alert.svg"
                            text: "Xatolar"
                            onClicked: {
                                backendBridge.requestViolations()
                                root.viewViolationsClicked(modelData.id)
                            }
                        }

                        BigButton {
                            minWidth: 80
                            minHeight: 38
                            variant: "secondary"
                            iconSource: "../assets/icons/photo.svg"
                            text: "PDF"
                            onClicked: {
                                backendBridge.exportSessionPdf(modelData.id)
                            }
                        }

                        BigButton {
                            minWidth: 80
                            minHeight: 38
                            variant: "secondary"
                            iconSource: "../assets/icons/check.svg"
                            text: "Xesh"
                            onClicked: {
                                backendBridge.verifySessionHash(modelData.id)
                            }
                        }
                    }
                }
            }

            // Empty State
            Rectangle {
                anchors.centerIn: parent
                width: Math.min(parent.width - 48, 500)
                height: 180
                radius: Theme.radiusMedium
                color: Theme.surfaceDark
                border.color: Theme.surfaceBorder
                border.width: 1
                visible: sessionsList.count === 0

                Column {
                    anchors.centerIn: parent
                    spacing: 12

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 48
                        height: 48
                        source: "../assets/icons/car.svg"
                        fillMode: Image.PreserveAspectFit
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: Theme.tr("empty.no_sessions")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBodySmall
                    }
                }
            }
        }
    }
}
