import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

Rectangle {
    id: root
    color: Theme.backgroundDark
    anchors.fill: parent

    // Properties
    property int currentStepIndex: 0
    property int totalSteps: 7
    property bool canProceed: false
    property string selectedLanguage: "uz-Latn"
    property bool eulaAgreed: false

    // Hardware Telemetry state
    property string cpuInfo: "8 Cores (Intel/AMD)"
    property string ramInfo: "16.0 GB DDR4"
    property string diskInfo: "45.2 GB Free"
    property string gpuInfo: "DirectML (DirectX 12 GPU)"
    property bool isUsbSafe: true
    property double maxDriftCm: 2.4
    property bool isCalibValid: true
    property bool audioPlayed: false

    // Signals
    signal requestNext()
    signal requestPrev()
    signal requestSave()
    signal languageSelected(string lang)
    signal audioTestRequested()
    signal hardwareScanRequested()
    signal calibrationCheckRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // 1. Wizard Header & Stepper
        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            Text {
                text: Theme.tr("wizard.title")
                color: Theme.colorAccent
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitleLarge
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            // Stepper pills (1..7)
            Row {
                spacing: 8
                Repeater {
                    model: root.totalSteps
                    Rectangle {
                        width: 36
                        height: 36
                        radius: 18
                        color: index === root.currentStepIndex ? Theme.colorAccent :
                               (index < root.currentStepIndex ? Theme.colorSuccess : Theme.surfaceElevated)
                        border.color: index === root.currentStepIndex ? Theme.textPrimary : Theme.surfaceBorder
                        border.width: index === root.currentStepIndex ? 2 : 1

                        Text {
                            anchors.centerIn: parent
                            text: (index + 1).toString()
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.bold: true
                            font.pixelSize: 16
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.surfaceBorder
        }

        // 2. Step Content View
        StackLayout {
            id: stepStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentStepIndex

            // Step 0: Language & EULA
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step1")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                    }

                    RowLayout {
                        spacing: 16
                        BigButton {
                            text: "O'ZBEKCHA (LOTIN)"
                            variant: root.selectedLanguage === "uz-Latn" ? "primary" : "secondary"
                            onClicked: {
                                root.selectedLanguage = "uz-Latn"
                                root.languageSelected("uz-Latn")
                                if (typeof i18n !== "undefined" && i18n) i18n.set_language("uz-Latn")
                            }
                        }
                        BigButton {
                            text: "ЎЗБЕКЧА (КИРИЛЛ)"
                            variant: root.selectedLanguage === "uz-Cyrl" ? "primary" : "secondary"
                            onClicked: {
                                root.selectedLanguage = "uz-Cyrl"
                                root.languageSelected("uz-Cyrl")
                                if (typeof i18n !== "undefined" && i18n) i18n.set_language("uz-Cyrl")
                            }
                        }
                        BigButton {
                            text: "РУССКИЙ"
                            variant: root.selectedLanguage === "ru" ? "primary" : "secondary"
                            onClicked: {
                                root.selectedLanguage = "ru"
                                root.languageSelected("ru")
                                if (typeof i18n !== "undefined" && i18n) i18n.set_language("ru")
                            }
                        }
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        Text {
                            width: parent.width - 20
                            wrapMode: Text.Wrap
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            text: Theme.tr("wizard.eula_terms")
                        }

                    }

                    RowLayout {
                        spacing: 12
                        CheckBox {
                            id: eulaCheck
                            checked: root.eulaAgreed
                            onCheckedChanged: {
                                root.eulaAgreed = checked
                                root.canProceed = checked
                            }
                        }
                        Text {
                            text: Theme.tr("wizard.eula_agree")
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                        }
                    }
                }
            }

            // Step 1: Hardware & USB Topology
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step2")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 20
                        rowSpacing: 16
                        Layout.fillWidth: true

                        StatusRow {
                            componentTitle: "Protsessor (CPU):"
                            detail: root.cpuInfo
                            status: "READY"
                        }
                        StatusRow {
                            componentTitle: "Operativ Xotira (RAM):"
                            detail: root.ramInfo
                            status: "READY"
                        }
                        StatusRow {
                            componentTitle: "SSD Bo'sh Joy:"
                            detail: root.diskInfo
                            status: "READY"
                        }
                        StatusRow {
                            componentTitle: "AI Dvigateli (GPU):"
                            detail: root.gpuInfo
                            status: "READY"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 80
                        radius: Theme.radiusMedium
                        color: root.isUsbSafe ? "#14532D" : "#78350F"
                        border.color: root.isUsbSafe ? Theme.colorSuccess : Theme.colorWarning
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12

                            Text {
                                text: root.isUsbSafe ? "✅ USB Host Topologiyasi: Barqaror" : "⚠️ USB Diqqat"
                                color: root.isUsbSafe ? Theme.colorSuccess : Theme.colorWarning
                                font.family: Theme.fontFamily
                                font.bold: true
                                font.pixelSize: Theme.fontHeadline
                            }

                            Text {
                                text: root.isUsbSafe ? "4 ta kamera alohida USB 3.0 kontrollerlariga muvaffaqiyatli taqsimlangan." :
                                                      "Barcha kameralar bitta hubga ulangan. Bandwidth tushishi mumkin."
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    BigButton {
                        text: Theme.tr("wizard.btn_rescan")
                        variant: "secondary"
                        onClicked: {
                            root.hardwareScanRequested()
                            root.canProceed = true
                        }
                    }
                }
            }

            // Step 2: 4 Camera Streams & Orientation
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step3")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                    }

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columnSpacing: 16
                        rowSpacing: 16

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Theme.surfaceElevated
                            radius: Theme.radiusSmall
                            ColumnLayout {
                                anchors.centerIn: parent
                                Text { text: "📷 " + Theme.tr("wizard.camera_front_label"); color: Theme.colorAccent; font.bold: true }
                                Text { text: "1920x1080 @ 30 FPS [MJPEG]"; color: Theme.colorSuccess }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Theme.surfaceElevated
                            radius: Theme.radiusSmall
                            ColumnLayout {
                                anchors.centerIn: parent
                                Text { text: "📷 " + Theme.tr("wizard.camera_rear_label"); color: Theme.colorAccent; font.bold: true }
                                Text { text: "1920x1080 @ 30 FPS [MJPEG]"; color: Theme.colorSuccess }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Theme.surfaceElevated
                            radius: Theme.radiusSmall
                            ColumnLayout {
                                anchors.centerIn: parent
                                Text { text: "📷 " + Theme.tr("wizard.camera_left_label"); color: Theme.colorAccent; font.bold: true }
                                Text { text: "1920x1080 @ 30 FPS [MJPEG]"; color: Theme.colorSuccess }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Theme.surfaceElevated
                            radius: Theme.radiusSmall
                            ColumnLayout {
                                anchors.centerIn: parent
                                Text { text: "📷 " + Theme.tr("wizard.camera_right_label"); color: Theme.colorAccent; font.bold: true }
                                Text { text: "1920x1080 @ 30 FPS [MJPEG]"; color: Theme.colorSuccess }
                            }
                        }

                    }
                }
            }

            // Step 3: Calibration & Drift Check
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step4")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                    }

                    StatusRow {
                        componentTitle: "Maksimal Kalibrovka Siljishi:"
                        detail: root.maxDriftCm.toFixed(1) + " sm (Chegara: 5.0 sm)"
                        status: root.isCalibValid ? "READY" : "FAILED"
                    }

                    Text {
                        text: Theme.tr("wizard.calibration_desc")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }


                    Item { Layout.fillHeight: true }

                    BigButton {
                        text: Theme.tr("admin.btn_calibrate")
                        variant: "secondary"
                        onClicked: {
                            root.calibrationCheckRequested()
                            root.canProceed = true
                        }
                    }
                }
            }

            // Step 4: Autodrome Zones
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step5")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                    }

                    Text {
                        text: "1. START -> 2. ESTAKADA -> 3. ZMEIKA -> 4. TURN_90 -> 5. PARALLEL_PARKING -> 6. GARAGE_REVERSE -> 7. STOP -> 8. FINISH"
                        color: Theme.colorSuccess
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Text {
                        text: Theme.tr("wizard.polygon_geofence")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // Step 5: Audio Speaker Test
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step6")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                    }

                    Text {
                        text: Theme.tr("wizard.audio_desc")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }

                    BigButton {
                        text: Theme.tr("wizard.btn_test_audio")
                        variant: "primary"
                        onClicked: {
                            root.audioTestRequested()
                            root.audioPlayed = true
                            root.canProceed = true
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // Step 6: Final Summary & Save
            Rectangle {
                color: Theme.surfaceDark
                radius: Theme.radiusLarge
                border.color: Theme.surfaceBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: Theme.tr("wizard.step7")
                        color: Theme.colorSuccess
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitleLarge
                        font.bold: true
                    }

                    Text {
                        text: Theme.tr("wizard.summary_success")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }


                    Item { Layout.fillHeight: true }

                    BigButton {
                        text: Theme.tr("wizard.btn_complete")
                        variant: "primary"
                        onClicked: root.requestSave()
                    }
                }
            }
        }

        // 3. Wizard Bottom Navigation Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            BigButton {
                text: Theme.tr("btn_back")
                variant: "secondary"
                enabled: root.currentStepIndex > 0
                onClicked: root.requestPrev()
            }

            Item { Layout.fillWidth: true }

            BigButton {
                text: root.currentStepIndex < root.totalSteps - 1 ? Theme.tr("btn_proceed") : Theme.tr("wizard.btn_complete")
                variant: "primary"
                enabled: root.currentStepIndex === (root.totalSteps - 1) || root.canProceed
                onClicked: root.requestNext()
            }
        }
    }
}
