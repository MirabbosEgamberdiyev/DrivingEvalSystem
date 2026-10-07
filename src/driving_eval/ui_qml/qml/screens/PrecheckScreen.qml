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
        title: Theme.tr("precheck_title")
        subtitle: backendBridge.precheckPassed 
            ? Theme.tr("precheck_passed")
            : Theme.tr("precheck_in_progress")
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
                text: Theme.tr("precheck_blocked_title") + ": " + backendBridge.precheckBlockedReason
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
            componentTitle: (modelData.id ? Theme.tr(modelData.id) : (modelData.title || ""))
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
                text: Theme.tr("btn_back")
                onClicked: root.backClicked()
            }

            BigButton {
                minWidth: 240
                minHeight: 64
                variant: backendBridge.precheckPassed ? "secondary" : "warning"
                iconSource: "../assets/icons/refresh.svg"
                text: Theme.tr("btn_recheck")
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
                text: Theme.tr("btn_proceed")
                enabled: backendBridge.precheckPassed
                onClicked: root.proceedClicked()
            }
        }
    }
}
