import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property var precheckItems: []

    signal proceedClicked()
    signal retryClicked()
    signal backClicked()

    Connections {
        target: backendBridge
        function onPrecheckUpdated(items) {
            root.precheckItems = items
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
        title: (typeof i18n !== "undefined" && i18n) ? i18n.t("precheck_title") : "USKUNALAR VA TIZIM PRE-CHECK"
        subtitle: backendBridge.precheckPassed 
            ? ((typeof i18n !== "undefined" && i18n) ? i18n.t("precheck_passed") : "Barcha 12 ta majburiy komponent muvaffaqiyatli tekshirildi.")
            : ((typeof i18n !== "undefined" && i18n) ? i18n.t("precheck_in_progress") : "Diagnostika o'tkazilmoqda...")
        carId: backendBridge.carId
        showBack: true
        showSettings: false
        onBackClicked: root.backClicked()
    }

    // Blocked Banner (if any required component failed)
    Rectangle {
        id: blockedBanner
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 64
        color: Theme.colorErrorBg
        border.color: Theme.colorError
        border.width: 1
        visible: !backendBridge.precheckPassed && backendBridge.precheckBlockedReason !== ""

        Row {
            anchors.centerIn: parent
            spacing: 16

            Image {
                width: 28
                height: 28
                source: "../assets/icons/alert.svg"
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
            }

            Text {
                text: ((typeof i18n !== "undefined" && i18n) ? i18n.t("precheck_blocked_title") : "TEST START BLOCKED") + ": " + backendBridge.precheckBlockedReason
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontHeadline
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // Component Status List
    ListView {
        id: statusList
        anchors.top: blockedBanner.visible ? blockedBanner.bottom : topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        clip: true
        spacing: 10
        model: root.precheckItems

        delegate: StatusRow {
            width: statusList.width - 12
            componentTitle: (typeof i18n !== "undefined" && i18n && modelData.id) ? i18n.t(modelData.id) : (modelData.title || "")
            status: modelData.status || "CHECKING"
            detail: modelData.detail || ""
            isRequired: modelData.required !== undefined ? modelData.required : true
        }
    }

    // Bottom Action Bar
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
                text: (typeof i18n !== "undefined" && i18n) ? i18n.t("btn_back") : "ORQAGA"
                onClicked: root.backClicked()
            }

            BigButton {
                minWidth: 240
                minHeight: 64
                variant: backendBridge.precheckPassed ? "secondary" : "warning"
                iconSource: "../assets/icons/refresh.svg"
                text: (typeof i18n !== "undefined" && i18n) ? i18n.t("btn_recheck") : "QAYTA TEKSHIRISH"
                onClicked: {
                    backendBridge.retryPrecheck()
                    root.retryClicked()
                }
            }

            BigButton {
                minWidth: 260
                minHeight: 64
                variant: "success"
                iconSource: "../assets/icons/check.svg"
                text: (typeof i18n !== "undefined" && i18n) ? i18n.t("btn_proceed") : "DAVOM ETISH"
                enabled: backendBridge.precheckPassed
                onClicked: root.proceedClicked()
            }
        }
    }
}
