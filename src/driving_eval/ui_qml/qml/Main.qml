import QtQuick
import QtQuick.Window
import QtQuick.Controls
import "."
import "components"
import "screens"

Window {
    id: mainWindow

    visible: true
    width: 1280
    height: 800
    minimumWidth: 1024
    minimumHeight: 600
    title: "Driving Training & Evaluation System (Offline Standalone)"
    color: Theme.backgroundDark

    // Global stack for screen management
    StackView {
        id: stackView
        anchors.fill: parent
        initialItem: homeScreenComponent

        pushEnter: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 0.0
                to: 1.0
                duration: Theme.animDurationStandard
            }
        }
        pushExit: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 1.0
                to: 0.0
                duration: Theme.animDurationFast
            }
        }
        popEnter: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 0.0
                to: 1.0
                duration: Theme.animDurationStandard
            }
        }
        popExit: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 1.0
                to: 0.0
                duration: Theme.animDurationFast
            }
        }
    }

    // Component Definitions
    Component {
        id: homeScreenComponent
        HomeScreen {
            onStartTestClicked: {
                backendBridge.startTest()
            }
            onPrecheckClicked: {
                backendBridge.startPrecheck()
                stackView.push(precheckScreenComponent)
            }
            onInspectorClicked: {
                stackView.push(inspectorScreenComponent)
            }
            onSettingsClicked: {
                stackView.push(settingsScreenComponent)
            }
        }
    }

    Component {
        id: inspectorScreenComponent
        InspectorScreen {
            onViewViolationsClicked: function(sessionId) {
                stackView.push(violationsListScreenComponent)
            }
            onViewEvidenceClicked: function(eventId) {
                stackView.push(evidenceScreenComponent, { eventId: eventId })
            }
            onBackClicked: {
                stackView.pop()
            }
        }
    }

    Component {
        id: precheckScreenComponent
        PrecheckScreen {
            onProceedClicked: {
                backendBridge.proceedToReady()
                stackView.push(systemReadyScreenComponent)
            }
            onBackClicked: {
                stackView.pop()
            }
        }
    }

    Component {
        id: systemReadyScreenComponent
        SystemReadyScreen {
            onStartTestClicked: {
                backendBridge.startTest()
            }
            onBackClicked: {
                stackView.pop()
            }
        }
    }

    Component {
        id: activeTestScreenComponent
        ActiveTestScreen {
            onFinishTestClicked: {
                backendBridge.finishTest()
            }
        }
    }

    Component {
        id: resultScreenComponent
        ResultScreen {
            onViewViolationsClicked: {
                stackView.push(violationsListScreenComponent)
            }
            onHomeClicked: {
                backendBridge.resetToHome()
                stackView.clear()
                stackView.push(homeScreenComponent)
            }
        }
    }

    Component {
        id: violationsListScreenComponent
        ViolationsListScreen {
            onEvidenceClicked: function(eventId) {
                stackView.push(evidenceScreenComponent, { eventId: eventId })
            }
            onBackClicked: {
                stackView.pop()
            }
        }
    }

    Component {
        id: evidenceScreenComponent
        EvidenceScreen {
            onBackClicked: {
                stackView.pop()
            }
        }
    }

    Component {
        id: settingsScreenComponent
        SettingsScreen {
            onBackClicked: {
                stackView.pop()
            }
            onOpenWizardRequested: {
                stackView.push(setupWizardScreenComponent)
            }
        }
    }

    Component {
        id: setupWizardScreenComponent
        SetupWizardScreen {
            onRequestSave: {
                stackView.pop()
            }
            onRequestPrev: {
                stackView.pop()
            }
        }
    }

    // --- Violation Notification Popup (Overlays across HUD) ---
    ViolationPopup {
        id: violationPopup
        anchors.fill: parent
        onCriticalViolationHandled: {
            // When critical violation popup is handled/dismissed
        }
    }

    // --- Disconnect Overlay (Appears if local backend daemon is interrupted) ---
    Rectangle {
        id: disconnectOverlay
        anchors.fill: parent
        color: Theme.overlayBackground
        visible: !backendBridge.isConnected
        z: 300

        MouseArea {
            anchors.fill: parent
            onClicked: {} // Block interaction
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 48, 640)
            implicitHeight: discCol.implicitHeight + 48
            radius: Theme.radiusLarge
            color: Theme.surfaceDark
            border.color: Theme.colorWarning
            border.width: 2

            Column {
                id: discCol
                anchors.fill: parent
                anchors.margins: 28
                spacing: 16

                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 52
                    height: 52
                    source: "assets/icons/alert.svg"
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: (typeof i18n !== "undefined" && i18n) ? i18n.t("disconnect_overlay_title") : "ALOQA TIKLANMOQDA..."
                    color: Theme.colorWarning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontTitle
                    font.bold: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: (typeof i18n !== "undefined" && i18n) ? i18n.t("disconnect_overlay_desc") : "Backend xizmati bilan aloqa yo'qoldi. Qayta ulanish kutilmoqda. Test hisobi va ma'lumotlar saqlanmoqda."
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    horizontalAlignment: Text.AlignHCenter
                    width: parent.width
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    // --- Connections to BackendBridge Lifecycle Signals ---
    Connections {
        target: backendBridge

        function onStateChanged(newState) {
            if (newState === "TEST_ACTIVE") {
                // Ensure active test screen is showing
                if (stackView.currentItem !== activeTestScreenComponent) {
                    stackView.push(activeTestScreenComponent)
                }
            } else if (newState === "RESULT_READY") {
                // Switch to result screen
                stackView.push(resultScreenComponent)
            } else if (newState === "HOME") {
                stackView.clear()
                stackView.push(homeScreenComponent)
            }
        }

        function onViolationRaised(code, title, screenText, penalty, critical) {
            violationPopup.enqueue(code, title, screenText, penalty, critical)
        }
    }
}
