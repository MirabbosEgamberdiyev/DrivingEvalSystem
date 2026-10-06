import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property var violations: []

    signal backClicked()
    signal evidenceClicked(string eventId)

    Connections {
        target: backendBridge
        function onViolationsListReady(items) {
            root.violations = items
        }
    }

    Component.onCompleted: {
        backendBridge.requestViolations()
    }

    // Helper functions to partition violations into confirmed and suspect
    readonly property var confirmedList: {
        var res = []
        for (var i = 0; i < root.violations.length; i++) {
            if (!root.violations[i].suspect) res.push(root.violations[i])
        }
        return res
    }

    readonly property var suspectList: {
        var res = []
        for (var i = 0; i < root.violations.length; i++) {
            if (root.violations[i].suspect) res.push(root.violations[i])
        }
        return res
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
        title: (typeof i18n !== "undefined" && i18n) ? i18n.t("violations_list_title") : "QAYD ETILGAN QOIDABUZARLIKLAR"
        subtitle: (typeof i18n !== "undefined" && i18n) ? i18n.tf("violations_list_subtitle", root.violations.length) : ("Jami: " + root.violations.length + " ta hodisa")
        carId: backendBridge.carId
        showBack: true
        showSettings: false
        onBackClicked: root.backClicked()
    }

    // Empty state if no violations
    Item {
        anchors.centerIn: parent
        visible: root.violations.length === 0
        width: 600
        height: 200

        Column {
            anchors.centerIn: parent
            spacing: 16

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 64
                height: 64
                source: "../assets/icons/check.svg"
                fillMode: Image.PreserveAspectFit
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: (typeof i18n !== "undefined" && i18n) ? i18n.t("violations_empty_title") : "Hech qanday qoidabuzarlik qayd etilmadi!"
                color: Theme.colorSuccess
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: (typeof i18n !== "undefined" && i18n) ? i18n.t("violations_empty_desc") : "Barcha talablar namunali darajada bajarildi."
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
            }
        }
    }

    // Scrollable Content
    Flickable {
        id: flickableArea
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        contentHeight: listCol.implicitHeight + 32
        clip: true
        visible: root.violations.length > 0

        Column {
            id: listCol
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width - 24, 880)
            spacing: 24

            // Section 1: Confirmed Violations
            Column {
                width: parent.width
                spacing: 12
                visible: root.confirmedList.length > 0

                Text {
                    text: (typeof i18n !== "undefined" && i18n) ? i18n.t("violations_confirmed_header") : "TASDIQLANGAN JARIMALAR (BALLDAN AYRILGAN):"
                    color: Theme.colorError
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontHeadline
                    font.bold: true
                }

                Repeater {
                    model: root.confirmedList
                    ViolationCard {
                        width: parent.width
                        eventId: modelData.id || ""
                        code: modelData.code || ""
                        title: modelData.title || ""
                        screenText: modelData.screen_text || ""
                        exercise: modelData.exercise || ""
                        timestamp: modelData.timestamp || ""
                        penalty: modelData.penalty || 0
                        isCritical: modelData.critical || false
                        isSuspect: false
                        onEvidenceRequested: function(id) {
                            root.evidenceClicked(id)
                        }
                    }
                }
            }

            // Section 2: Suspect Events (Inspector Review)
            Column {
                width: parent.width
                spacing: 12
                visible: root.suspectList.length > 0

                Text {
                    text: (typeof i18n !== "undefined" && i18n) ? i18n.t("violations_suspect_header") : "SHUBHALI (SUSPECT) HODISALAR (JARIMA OLINMAGAN, INSPEKTOR KO'RISHI UCHUN):"
                    color: Theme.colorWarning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontHeadline
                    font.bold: true
                }

                Repeater {
                    model: root.suspectList
                    ViolationCard {
                        width: parent.width
                        eventId: modelData.id || ""
                        code: modelData.code || ""
                        title: modelData.title || ""
                        screenText: modelData.screen_text || ""
                        exercise: modelData.exercise || ""
                        timestamp: modelData.timestamp || ""
                        penalty: 0
                        isCritical: false
                        isSuspect: true
                        onEvidenceRequested: function(id) {
                            root.evidenceClicked(id)
                        }
                    }
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
                minWidth: 240
                minHeight: 64
                variant: "secondary"
                iconSource: "../assets/icons/back.svg"
                text: (typeof i18n !== "undefined" && i18n) ? i18n.t("btn_back") : "ORQAGA"
                onClicked: root.backClicked()
            }
        }
    }
}
