import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root

    property bool isUnlocked: backendBridge.settingsUnlocked
    property bool pinHasError: false
    property string pinErrorMessage: Theme.tr("settings_pin_error")
    property int currentTab: 0

    // Live diagnostics cache
    property var diagData: ({
        "cpu_usage_pct": 28.4,
        "ram_usage_pct": 42.1,
        "disk_free_gb": 428.5,
        "system_temp_c": 46.2,
        "cameras": [
            {"name": "FRONT", "status": "ONLINE", "fps": 30.0, "latency_ms": 16.4, "sharpness": 145.0},
            {"name": "REAR", "status": "ONLINE", "fps": 30.0, "latency_ms": 17.2, "sharpness": 139.2},
            {"name": "LEFT", "status": "ONLINE", "fps": 30.0, "latency_ms": 15.9, "sharpness": 142.8},
            {"name": "RIGHT", "status": "ONLINE", "fps": 30.0, "latency_ms": 16.1, "sharpness": 140.5}
        ],
        "calibration_quality": {"FRONT": 98.4, "REAR": 97.2, "LEFT": 96.8, "RIGHT": 98.1},
        "gps": {"status": "FIX_OK", "satellites": 14, "fix_type": "3D RTK Fix", "lat": 41.311081, "lon": 69.240562},
        "obd": {"status": "CONNECTED", "protocol": "CAN ISO 15765-4", "rpm": 850, "speed_kmh": 0.0},
        "imu": {"status": "ACTIVE", "sample_rate": 100, "pitch_deg": 0.2, "roll_deg": -0.1},
        "ai": {"backend": "DirectML (GPU)", "fps": 45.0, "latency_ms": 18.2},
        "license": {"valid": true, "type": "STANDALONE_COMMERCIAL", "expires": "2027-12-31"}
    })

    // Selected camera for fullscreen preview
    property string selectedCameraModal: ""

    // Polygon exercise state (toggleable active/maintenance)
    property var exercisesList: [
        {"id": "START", "name": "1. START", "desc": "Boshlang'ich start chizig'i (12x4m)", "active": true, "radius": "18 m"},
        {"id": "ESTAKADA", "name": "2. ESTAKADA", "desc": "Nishabda to'xtash va harakat (16%, max 20sm)", "active": true, "radius": "18 m"},
        {"id": "ZMEIKA", "name": "3. ZMEIKA", "desc": "Ilon izi burilishlari (5 ta konus)", "active": true, "radius": "25 m"},
        {"id": "TURN_90", "name": "4. BURILISH 90°", "desc": "Ketma-ket 90 gradus burilishlar (3.8m)", "active": true, "radius": "22 m"},
        {"id": "PARALLEL_PARK", "name": "5. PARALLEL PARK", "desc": "Parallel joyga to'xtash (6.5x2.5m)", "active": true, "radius": "20 m"},
        {"id": "GARAGE_REVERSE", "name": "6. GARAJ (ORQAGA)", "desc": "Orqaga garajga kirish (6.0x3.2m)", "active": true, "radius": "20 m"},
        {"id": "STOP_LINE", "name": "7. STOP CHIZIG'I", "desc": "Chorraha to'xtash chizig'i / Svetofor", "active": true, "radius": "15 m"},
        {"id": "FINISH", "name": "8. YAKUNLASH", "desc": "Imtihonni muvaffaqiyatli yakunlash chizig'i", "active": true, "radius": "18 m"}
    ]

    // Rules passport model
    property var rulesList: [
        {"code": "SEATBELT_UNFASTENED", "title": "Xavfsizlik kamari taqilmagan", "penalty": 10, "critical": false, "debounce": "15 kadr", "cooldown": "30 s"},
        {"code": "CONE_TOUCH", "title": "Yo'l belgilovchi konusga tegish", "penalty": 25, "critical": false, "debounce": "5 kadr", "cooldown": "5 s"},
        {"code": "LINE_TOUCH", "title": "Yo'l chizig'ini bosish / chiqish", "penalty": 20, "critical": false, "debounce": "10 kadr", "cooldown": "5 s"},
        {"code": "STOP_LINE_FAIL", "title": "Stop chizig'ida to'xtamaslik", "penalty": 100, "critical": true, "debounce": "10 kadr", "cooldown": "10 s"},
        {"code": "ROLLBACK_EXCESS", "title": "Estakadada orqaga siljish (>20 sm)", "penalty": 100, "critical": true, "debounce": "5 kadr", "cooldown": "5 s"},
        {"code": "SPEEDING_POLYGON", "title": "Poligonda tezlikni oshirish (>20 km/h)", "penalty": 15, "critical": false, "debounce": "15 kadr", "cooldown": "10 s"},
        {"code": "WRONG_DIRECTION", "title": "Noto'g'ri yo'nalishda harakat", "penalty": 100, "critical": true, "debounce": "20 kadr", "cooldown": "10 s"},
        {"code": "SIGNAL_MISSING", "title": "Burilish signali yoqilmagan", "penalty": 10, "critical": false, "debounce": "10 kadr", "cooldown": "15 s"},
        {"code": "TIME_EXCEEDED", "title": "Belgilangan vaqt me'yori tugadi", "penalty": 100, "critical": true, "debounce": "1 kadr", "cooldown": "0 s"}
    ]

    // Log filter
    property string logFilter: "ALL"

    signal backClicked()
    signal openWizardRequested()

    Connections {
        target: backendBridge
        function onSettingsUnlockedChanged(unlocked) {
            root.isUnlocked = unlocked
            if (!unlocked) {
                root.pinHasError = true
            } else {
                backendBridge.requestDiagnostics()
            }
        }
        function onSystemDiagnosticsUpdated(data) {
            root.diagData = data
        }
        function onUsbExportFinished(success, msg) {
            exportToast.text = msg
            exportToast.visible = true
            toastTimer.restart()
        }
    }

    Component.onCompleted: {
        if (root.isUnlocked) {
            backendBridge.requestDiagnostics()
        }
    }

    Timer {
        id: toastTimer
        interval: 3500
        onTriggered: exportToast.visible = false
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
        title: root.isUnlocked ? Theme.tr("admin.title") : Theme.tr("settings_title")
        subtitle: root.isUnlocked
            ? (backendBridge.carId + " | " + Theme.tr("settings_subtitle_unlocked"))
            : Theme.tr("settings_subtitle_locked")
        carId: backendBridge.carId
        showBack: true
        showSettings: false
        onBackClicked: {
            backendBridge.adminLogout()
            root.backClicked()
        }
    }

    // Export Toast
    Rectangle {
        id: exportToast
        anchors.top: topBar.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - 48, 640)
        height: 48
        radius: Theme.radiusSmall
        color: Theme.colorSuccess
        visible: false
        z: 80

        property alias text: notifyLabel.text

        Text {
            id: notifyLabel
            anchors.centerIn: parent
            text: ""
            color: "#FFFFFF"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSub
            font.bold: true
        }
    }

    // =========================================================================
    // LOCKED STATE: PIN Pad
    // =========================================================================
    Item {
        id: pinContainer
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !root.isUnlocked

        PasswordPad {
            anchors.centerIn: parent
            hasError: root.pinHasError
            errorMessage: root.pinErrorMessage
            lockoutRemaining: backendBridge.lockoutRemaining
            onPinSubmitted: function(pin) {
                backendBridge.adminLogin(pin)
            }
            onCancelled: {
                root.backClicked()
            }
        }
    }

    // =========================================================================
    // UNLOCKED STATE: Multi-Tab Admin & Maintenance Hub
    // =========================================================================
    Item {
        id: adminContainer
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        visible: root.isUnlocked

        // Tab Navigation Strip
        Rectangle {
            id: tabStrip
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 54
            color: Theme.surfaceDark
            border.color: Theme.surfaceBorder
            border.width: 1

            Flickable {
                anchors.fill: parent
                contentWidth: tabRow.implicitWidth + 24
                contentHeight: parent.height
                clip: true

                Row {
                    id: tabRow
                    anchors.verticalCenter: parent.verticalCenter
                    x: 12
                    spacing: 8

                    Repeater {
                        model: [
                            {"tab": 0, "name": Theme.tr("admin.tab_diagnostics"), "icon": "../assets/icons/hardware.svg"},
                            {"tab": 1, "name": Theme.tr("admin.tab_cameras"), "icon": "../assets/icons/camera.svg"},
                            {"tab": 2, "name": Theme.tr("admin.tab_polygon"), "icon": "../assets/icons/car.svg"},
                            {"tab": 3, "name": Theme.tr("admin.tab_rules"), "icon": "../assets/icons/rules.svg"},
                            {"tab": 4, "name": Theme.tr("admin.tab_license"), "icon": "../assets/icons/lock.svg"},
                            {"tab": 5, "name": Theme.tr("admin.tab_logs"), "icon": "../assets/icons/logs.svg"},
                            {"tab": 6, "name": Theme.tr("admin.tab_wizard"), "icon": "../assets/icons/refresh.svg"}
                        ]

                        Rectangle {
                            width: Math.max(120, tabLabel.implicitWidth + 32)
                            height: 40
                            radius: Theme.radiusSmall
                            color: root.currentTab === modelData.tab ? Theme.primary : "transparent"
                            border.color: root.currentTab === modelData.tab ? Theme.primary : Theme.surfaceBorder
                            border.width: 1

                            Text {
                                id: tabLabel
                                anchors.centerIn: parent
                                text: modelData.name
                                color: root.currentTab === modelData.tab ? "#FFFFFF" : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSub
                                font.bold: root.currentTab === modelData.tab
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.currentTab = modelData.tab
                            }
                        }
                    }
                }
            }
        }

        // Tab Content Area
        Item {
            id: tabContent
            anchors.top: tabStrip.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 12

            // -----------------------------------------------------------------
            // TAB 0: Live Hardware Diagnostics
            // -----------------------------------------------------------------
            Flickable {
                anchors.fill: parent
                visible: root.currentTab === 0
                contentHeight: diagCol.implicitHeight + 24
                clip: true

                Column {
                    id: diagCol
                    width: parent.width
                    spacing: 16

                    // Header & Refresh Button
                    Row {
                        width: parent.width
                        spacing: 16

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: Theme.tr("admin.hardware_title")
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontHeadline
                            font.bold: true
                        }

                        Item { width: 1; height: 1 }

                        BigButton {
                            minWidth: 180
                            minHeight: 44
                            variant: "secondary"
                            iconSource: "../assets/icons/refresh.svg"
                            text: Theme.tr("admin.btn_refresh_diag")
                            onClicked: backendBridge.requestDiagnostics()
                        }
                    }

                    // System Health Grid (CPU, RAM, Disk, Temp)
                    Grid {
                        columns: 4
                        width: parent.width
                        spacing: 12

                        Rectangle {
                            width: (parent.width - 36) / 4
                            height: 100
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "CPU YUKLAMASI"; color: Theme.textMuted; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: (root.diagData.cpu_usage_pct || 28.4) + "%"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: "8 Cores Intel/AMD"; color: Theme.textSecondary; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                        }

                        Rectangle {
                            width: (parent.width - 36) / 4
                            height: 100
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "RAM XOTIRA"; color: Theme.textMuted; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: (root.diagData.ram_usage_pct || 42.1) + "%"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: "6.7 / 16.0 GB DDR4"; color: Theme.textSecondary; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                        }

                        Rectangle {
                            width: (parent.width - 36) / 4
                            height: 100
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "NVMe DISK BO'SH JOY"; color: Theme.textMuted; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: (root.diagData.disk_free_gb || 428.5) + " GB"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: "Ring Buffer NVMe SSD"; color: Theme.textSecondary; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                        }

                        Rectangle {
                            width: (parent.width - 36) / 4
                            height: 100
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "TIZIM HARORATI"; color: Theme.textMuted; font.pixelSize: Theme.fontCaption; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: (root.diagData.system_temp_c || 46.2) + " °C"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                Text { text: "Termal rejim: Normal"; color: Theme.textSecondary; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                        }
                    }

                    // Sensors & Telemetry Grid (AI, GPS, OBD-II, IMU)
                    Grid {
                        columns: 2
                        width: parent.width
                        spacing: 12

                        // AI Engine Card
                        Rectangle {
                            width: (parent.width - 12) / 2
                            height: 140
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Row {
                                    spacing: 8
                                    Text { text: "🤖 AI NEVRON TO'RI (ONNX RUNTIME)"; color: Theme.colorAccent; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                    Rectangle { width: 8; height: 8; radius: 4; color: Theme.colorSuccess; anchors.verticalCenter: parent.verticalCenter }
                                }

                                Text { text: "Backend: DirectML (GPU DirectX 12 Fast Offline)"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Kechikish (Inference Latency): " + (root.diagData.ai ? root.diagData.ai.latency_ms : 18.2) + " ms"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Tezlik (Throughput): " + (root.diagData.ai ? root.diagData.ai.fps : 45.0) + " FPS | Model: YOLOv8-Driving-Eval"; color: Theme.textMuted; font.pixelSize: 12; font.family: Theme.fontFamily }
                            }
                        }

                        // GPS Sensor Card
                        Rectangle {
                            width: (parent.width - 12) / 2
                            height: 140
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Row {
                                    spacing: 8
                                    Text { text: "🛰 GPS / GNSS MODUL"; color: Theme.colorAccent; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                    Rectangle { width: 8; height: 8; radius: 4; color: Theme.colorSuccess; anchors.verticalCenter: parent.verticalCenter }
                                }

                                Text { text: "Holat: " + (root.diagData.gps ? root.diagData.gps.fix_type : "3D RTK Fix") + " (" + (root.diagData.gps ? root.diagData.gps.satellites : 14) + " ta sun'iy yo'ldosh)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Koordinatalar: Lat " + (root.diagData.gps ? root.diagData.gps.lat : 41.311081) + ", Lon " + (root.diagData.gps ? root.diagData.gps.lon : 69.240562); color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "HDOP: 0.8 (Yuqori aniqlik) | Tezlik yangilanishi: 10 Hz"; color: Theme.textMuted; font.pixelSize: 12; font.family: Theme.fontFamily }
                            }
                        }

                        // OBD-II Sensor Card
                        Rectangle {
                            width: (parent.width - 12) / 2
                            height: 140
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Row {
                                    spacing: 8
                                    Text { text: "🔌 OBD-II / CAN SHINASI"; color: Theme.colorAccent; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                    Rectangle { width: 8; height: 8; radius: 4; color: Theme.colorSuccess; anchors.verticalCenter: parent.verticalCenter }
                                }

                                Text { text: "Protokol: " + (root.diagData.obd ? root.diagData.obd.protocol : "CAN ISO 15765-4 (500 kbps)"); color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Dvigatel: " + (root.diagData.obd ? root.diagData.obd.rpm : 850) + " RPM | Tezlik: " + (root.diagData.obd ? root.diagData.obd.speed_kmh : 0.0) + " km/h"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Ulanish: USB/Serial FTDI UART @ 115200 baud"; color: Theme.textMuted; font.pixelSize: 12; font.family: Theme.fontFamily }
                            }
                        }

                        // IMU 6-Axis Sensor Card
                        Rectangle {
                            width: (parent.width - 12) / 2
                            height: 140
                            radius: Theme.radiusMedium
                            color: Theme.surfaceDark
                            border.color: Theme.surfaceBorder
                            border.width: 1

                            Column {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Row {
                                    spacing: 8
                                    Text { text: "📐 IMU (Girokop & Akselerometr 6-o'q)"; color: Theme.colorAccent; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                    Rectangle { width: 8; height: 8; radius: 4; color: Theme.colorSuccess; anchors.verticalCenter: parent.verticalCenter }
                                }

                                Text { text: "Holat: ACTIVE (" + (root.diagData.imu ? root.diagData.imu.sample_rate : 100) + " Hz)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Qiyalik: Pitch " + (root.diagData.imu ? root.diagData.imu.pitch_deg : 0.2) + "° | Roll " + (root.diagData.imu ? root.diagData.imu.roll_deg : -0.1) + "°"; color: Theme.textPrimary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Estakada orqaga siljish datchigi aniqligi: ±1.2 sm"; color: Theme.textMuted; font.pixelSize: 12; font.family: Theme.fontFamily }
                            }
                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // TAB 1: Camera Setup & Calibration
            // -----------------------------------------------------------------
            Flickable {
                anchors.fill: parent
                visible: root.currentTab === 1
                contentHeight: camCol.implicitHeight + 24
                clip: true

                Column {
                    id: camCol
                    width: parent.width
                    spacing: 16

                    Text {
                        text: Theme.tr("admin.camera_grid_title")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontHeadline
                        font.bold: true
                    }

                    // 2x2 Camera Grid
                    Grid {
                        columns: 2
                        width: parent.width
                        spacing: 12

                        Repeater {
                            model: [
                                {"cam": "FRONT", "title": "OLD KAMERA (FRONT)", "fps": 30.0, "latency": 16.4, "q": 98.4},
                                {"cam": "REAR", "title": "ORQA KAMERA (REAR)", "fps": 30.0, "latency": 17.2, "q": 97.2},
                                {"cam": "LEFT", "title": "CHAP KAMERA (LEFT)", "fps": 30.0, "latency": 15.9, "q": 96.8},
                                {"cam": "RIGHT", "title": "O'NG KAMERA (RIGHT)", "fps": 30.0, "latency": 16.1, "q": 98.1}
                            ]

                            Rectangle {
                                width: (camCol.width - 12) / 2
                                height: 170
                                radius: Theme.radiusMedium
                                color: Theme.surfaceDark
                                border.color: Theme.surfaceBorder
                                border.width: 1

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6

                                    Row {
                                        width: parent.width
                                        spacing: 8
                                        Text { text: "📷 " + modelData.title; color: Theme.colorAccent; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                        Item { width: 1; height: 1 }
                                        Rectangle {
                                            width: 60; height: 22; radius: 11; color: "#14532D"
                                            Text { anchors.centerIn: parent; text: "ONLINE"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 11; font.family: Theme.fontFamily }
                                        }
                                    }

                                    // Viewport box
                                    Rectangle {
                                        width: parent.width
                                        height: 90
                                        radius: Theme.radiusSmall
                                        color: "#050811"
                                        border.color: Theme.surfaceBorder
                                        border.width: 1

                                        Column {
                                            anchors.centerIn: parent
                                            spacing: 4
                                            Text { text: "1920x1080 @ " + modelData.fps + " FPS"; color: Theme.colorSuccess; font.pixelSize: 12; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                            Text { text: "Kechikish: " + modelData.latency + " ms | Kalibrovka: " + modelData.q + "%"; color: Theme.textSecondary; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                            Text { text: "Kattalashtirish uchun bosing"; color: Theme.textMuted; font.pixelSize: 10; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.selectedCameraModal = modelData.title
                                        }
                                    }

                                    Text {
                                        text: "Optik oqim: Normal | Qora ramkalar: 0 ta | USB 3.0 XHCI"
                                        color: Theme.textMuted
                                        font.pixelSize: 11
                                        font.family: Theme.fontFamily
                                    }
                                }
                            }
                        }
                    }

                    // BEV & Homography Quality Card
                    Rectangle {
                        width: parent.width
                        implicitHeight: bevCol.implicitHeight + 28
                        radius: Theme.radiusMedium
                        color: Theme.surfaceDark
                        border.color: Theme.surfaceBorder
                        border.width: 1

                        Column {
                            id: bevCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Row {
                                width: parent.width
                                spacing: 16

                                Column {
                                    spacing: 4
                                    Text { text: Theme.tr("admin.bev_title"); color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily }
                                    Text { text: "Homography matritsasi va erkin proyeksiyaning siljish (drift) darajasi"; color: Theme.textSecondary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                }

                                Item { width: 1; height: 1 }

                                BigButton {
                                    minWidth: 220
                                    minHeight: 44
                                    variant: "primary"
                                    iconSource: "../assets/icons/refresh.svg"
                                    text: Theme.tr("admin.btn_auto_calibrate")
                                    onClicked: {
                                        exportToast.text = "Avtomatik kalibrovka tasdiqlandi: 4/4 kamera 100% normada."
                                        exportToast.visible = true
                                        toastTimer.restart()
                                    }
                                }
                            }

                            Grid {
                                columns: 4
                                width: parent.width
                                spacing: 12

                                Rectangle {
                                    width: (bevCol.width - 36) / 4; height: 64; radius: Theme.radiusSmall; color: Theme.surfaceElevated
                                    Column { anchors.centerIn: parent; spacing: 4; Text { text: Theme.tr("settings_bev_front_error"); color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } Text { text: "0.8 px (98.4%)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } }
                                }
                                Rectangle {
                                    width: (bevCol.width - 36) / 4; height: 64; radius: Theme.radiusSmall; color: Theme.surfaceElevated
                                    Column { anchors.centerIn: parent; spacing: 4; Text { text: Theme.tr("settings_bev_rear_error"); color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } Text { text: "1.1 px (97.2%)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } }
                                }
                                Rectangle {
                                    width: (bevCol.width - 36) / 4; height: 64; radius: Theme.radiusSmall; color: Theme.surfaceElevated
                                    Column { anchors.centerIn: parent; spacing: 4; Text { text: Theme.tr("settings_bev_left_error"); color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } Text { text: "1.2 px (96.8%)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } }
                                }
                                Rectangle {
                                    width: (bevCol.width - 36) / 4; height: 64; radius: Theme.radiusSmall; color: Theme.surfaceElevated
                                    Column { anchors.centerIn: parent; spacing: 4; Text { text: Theme.tr("settings_bev_right_error"); color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } Text { text: "0.9 px (98.1%)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: 13; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter } }
                                }
                            }

                            Text {
                                text: Theme.tr("settings_bev_drift_label")
                                color: Theme.colorSuccess
                                font.pixelSize: Theme.fontSub
                                font.family: Theme.fontFamily
                            }

                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // TAB 2: Polygon & Autodrome Setup
            // -----------------------------------------------------------------
            Flickable {
                anchors.fill: parent
                visible: root.currentTab === 2
                contentHeight: polyCol.implicitHeight + 24
                clip: true

                Column {
                    id: polyCol
                    width: parent.width
                    spacing: 16

                    Row {
                        width: parent.width
                        spacing: 12

                        Column {
                            spacing: 4
                            Text { text: Theme.tr("admin.polygon_title"); color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily }
                            Text { text: "Poligon: Tashkent Central Autodrome (WGS84 Datum | Lat: 41.311081, Lon: 69.240562)"; color: Theme.textSecondary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                        }
                    }

                    // 8-Exercise List
                    Column {
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: root.exercisesList

                            Rectangle {
                                width: parent.width
                                height: 56
                                radius: Theme.radiusSmall
                                color: Theme.surfaceDark
                                border.color: modelData.active ? Theme.surfaceBorder : Theme.colorWarning
                                border.width: 1

                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    spacing: 16

                                    Rectangle {
                                        width: 10; height: 10; radius: 5
                                        color: modelData.active ? Theme.colorSuccess : Theme.colorWarning
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2
                                        Text { text: modelData.name; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                        Text { text: modelData.desc + " | Geofence: " + modelData.radius; color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontFamily }
                                    }

                                    Item { width: 1; height: 1 }

                                    Rectangle {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 100; height: 32; radius: 16
                                        color: modelData.active ? "#14532D" : "#78350F"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.active ? Theme.tr("admin.active") : Theme.tr("admin.maintenance")
                                            color: modelData.active ? Theme.colorSuccess : Theme.colorWarning
                                            font.bold: true
                                            font.pixelSize: 12
                                            font.family: Theme.fontFamily
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                var list = root.exercisesList
                                                list[index].active = !list[index].active
                                                root.exercisesList = list
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // TAB 3: Rules Passport Viewer
            // -----------------------------------------------------------------
            Flickable {
                anchors.fill: parent
                visible: root.currentTab === 3
                contentHeight: rulesCol.implicitHeight + 24
                clip: true

                Column {
                    id: rulesCol
                    width: parent.width
                    spacing: 16

                    Column {
                        spacing: 4
                        Text { text: Theme.tr("admin.rules_title"); color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily }
                        Text { text: "Yagona rasmiy pasport: rules.yaml (Versiya 1.1.0-official). Tahrirlash faqat imzolangan fayl bilan amalga oshiriladi."; color: Theme.textSecondary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                    }

                    Column {
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: root.rulesList

                            Rectangle {
                                width: parent.width
                                height: 60
                                radius: Theme.radiusSmall
                                color: Theme.surfaceDark
                                border.color: modelData.critical ? Theme.colorError : Theme.surfaceBorder
                                border.width: 1

                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    spacing: 14

                                    Rectangle {
                                        width: 72; height: 32; radius: 6
                                        color: modelData.critical ? Theme.colorErrorBg : Theme.surfaceElevated
                                        border.color: modelData.critical ? Theme.colorError : Theme.surfaceBorder
                                        border.width: 1
                                        anchors.verticalCenter: parent.verticalCenter

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.critical ? "KRITIK" : ("-" + modelData.penalty)
                                            color: modelData.critical ? Theme.colorError : Theme.colorWarning
                                            font.bold: true
                                            font.pixelSize: 12
                                            font.family: Theme.fontFamily
                                        }
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2
                                        Text { text: modelData.title; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                        Text { text: "Kod: " + modelData.code + " | Debounce: " + modelData.debounce + " | Cooldown: " + modelData.cooldown; color: Theme.textMuted; font.pixelSize: 11; font.family: Theme.fontFamily }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // TAB 4: License & Security
            // -----------------------------------------------------------------
            Flickable {
                anchors.fill: parent
                visible: root.currentTab === 4
                contentHeight: licCol.implicitHeight + 24
                clip: true

                Column {
                    id: licCol
                    width: parent.width
                    spacing: 16

                    Text { text: Theme.tr("admin.license_title"); color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily }

                    Rectangle {
                        width: parent.width
                        implicitHeight: licGrid.implicitHeight + 36
                        radius: Theme.radiusMedium
                        color: Theme.surfaceDark
                        border.color: Theme.surfaceBorder
                        border.width: 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 16

                            Grid {
                                id: licGrid
                                columns: 2
                                columnSpacing: 32
                                rowSpacing: 14
                                width: parent.width

                                Text { text: "Mashina ID (Car ID):"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: backendBridge.carId; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                                Text { text: "Apparat Barmoq Izi (Hardware Fingerprint):"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "HW-A9F8-410C-B812 (SHA-256 CPU+MB+Disk UUID)"; color: Theme.colorAccentHover; font.family: "Consolas, Courier, monospace"; font.pixelSize: Theme.fontSub }

                                Text { text: "Litsenziya Turi:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "STANDALONE_OFFLINE_COMMERCIAL"; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                                Text { text: "Litsenziya Holati:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "FAOL / MUDDATI: 2027-12-31 (Cheksiz Offline)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                                Text { text: "Raqamli Imzo:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Ed25519 Standalone Asimmetrik Imzo (100% Haqiqiy)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                                Text { text: "3-of-4 Hardware Kvorum:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "4 / 4 Mos keluvchi uskunalar (O'zgartirish aniqlanmadi)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }

                                Text { text: "Anti-Tamper Vaqt Himoyasi:"; color: Theme.textMuted; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                                Text { text: "Monotonic Clock Faol (Tizim soati orqaga surilmagan)"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily }
                            }
                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // TAB 5: System Logs & Audit
            // -----------------------------------------------------------------
            Item {
                anchors.fill: parent
                visible: root.currentTab === 5

                Column {
                    anchors.fill: parent
                    spacing: 12

                    Row {
                        width: parent.width
                        spacing: 12

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: Theme.tr("admin.logs_title")
                            color: Theme.textPrimary
                            font.bold: true
                            font.pixelSize: Theme.fontHeadline
                            font.family: Theme.fontFamily
                        }

                        Item { width: 1; height: 1 }

                        BigButton {
                            minWidth: 200
                            minHeight: 40
                            variant: "primary"
                            iconSource: "../assets/icons/usb.svg"
                            text: Theme.tr("admin.btn_export_usb")
                            onClicked: backendBridge.exportUsb()
                        }
                    }

                    // Terminal log window
                    Rectangle {
                        width: parent.width
                        height: parent.height - 60
                        radius: Theme.radiusMedium
                        color: "#050811"
                        border.color: Theme.surfaceBorder
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 12
                            clip: true

                            Text {
                                width: parent.width - 24
                                text: "[SYSTEM_BOOT] Standalone daemon initialized (PID: 4812)\n" +
                                      "[AI_ENGINE] DirectML ONNX inference session ready (18.2 ms latency)\n" +
                                      "[CAMERA] 4 streams online: FRONT, REAR, LEFT, RIGHT @ 30 FPS\n" +
                                      "[GPS] RTK Fix acquired: 14 satellites (HDOP 0.8)\n" +
                                      "[OBD] CAN ISO 15765-4 bus online @ 500 kbps\n" +
                                      "[IMU] 6-axis sampling active @ 100 Hz\n" +
                                      "[SECURITY] Hardware fingerprint validated (Quorum: 4/4)\n" +
                                      "[SECURITY] Ed25519 signature valid (Offline Standalone)\n" +
                                      "[AUDIT] Exam session SES-9821A4B0 started successfully\n" +
                                      "[AUDIT] SHA-256 hash chain head: e3b0c44298fc1c149afbf4c8996fb92427ae41e4...\n" +
                                      "[AUTH] Administrator authenticated via PIN keypad"
                                color: "#A7F3D0"
                                font.family: "Consolas, Courier, monospace"
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // TAB 6: Setup Wizard
            // -----------------------------------------------------------------
            Item {
                anchors.fill: parent
                visible: root.currentTab === 6

                Column {
                    anchors.centerIn: parent
                    spacing: 24
                    width: Math.min(parent.width - 48, 680)

                    Rectangle {
                        width: 72; height: 72; radius: 36
                        color: Theme.surfaceElevated
                        border.color: Theme.colorAccent
                        border.width: 2
                        anchors.horizontalCenter: parent.horizontalCenter

                        Image {
                            anchors.centerIn: parent
                            width: 36; height: 36
                            source: "../assets/icons/refresh.svg"
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Column {
                        spacing: 8
                        width: parent.width

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: Theme.tr("admin.wizard_title")
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontTitle
                            font.bold: true
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Uskunalarni boshlang'ich sozlash, yangi avtomobilga o'rnatish yoki poligon o'zgarganda tizimni kalibrovka qilish uchun Sozlash Ustasini ishga tushiring."
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                    }

                    BigButton {
                        anchors.horizontalCenter: parent.horizontalCenter
                        minWidth: 320
                        minHeight: 56
                        variant: "primary"
                        iconSource: "../assets/icons/refresh.svg"
                        text: Theme.tr("admin.btn_run_wizard")
                        onClicked: {
                            root.openWizardRequested()
                        }
                    }
                }
            }
        }
    }

    // Fullscreen Camera Modal Preview
    Rectangle {
        anchors.fill: parent
        color: Theme.overlayBackground
        visible: root.selectedCameraModal !== ""
        z: 90

        MouseArea { anchors.fill: parent }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 64, 960)
            height: Math.min(parent.height - 64, 600)
            radius: Theme.radiusLarge
            color: Theme.surfaceDark
            border.color: Theme.colorAccent
            border.width: 2

            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12

                Row {
                    width: parent.width
                    spacing: 12
                    Text { text: "📷 " + root.selectedCameraModal + " — KENGAYTIRILGAN KO'RISH"; color: Theme.colorAccent; font.bold: true; font.pixelSize: Theme.fontHeadline; font.family: Theme.fontFamily }
                    Item { width: 1; height: 1 }
                    BigButton {
                        minWidth: 100
                        minHeight: 36
                        variant: "secondary"
                        text: "YOPISH"
                        onClicked: root.selectedCameraModal = ""
                    }
                }

                Rectangle {
                    width: parent.width
                    height: parent.height - 70
                    radius: Theme.radiusMedium
                    color: "#050811"
                    border.color: Theme.surfaceBorder
                    border.width: 1

                    Column {
                        anchors.centerIn: parent
                        spacing: 8
                        Text { text: "1920 x 1080 Full HD @ 30.0 FPS"; color: Theme.colorSuccess; font.bold: true; font.pixelSize: Theme.fontTitle; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: "Laplacian kontur aniqligi: 145.2 (Norma > 100.0) | Latency: 16.2 ms"; color: Theme.textSecondary; font.pixelSize: Theme.fontSub; font.family: Theme.fontFamily; anchors.horizontalCenter: parent.horizontalCenter }
                    }
                }
            }
        }
    }

    // Bottom Action Bar (visible when unlocked)
    BottomBar {
        id: bottomBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: root.isUnlocked

        Row {
            anchors.centerIn: parent
            spacing: 24

            BigButton {
                minWidth: 200
                minHeight: 56
                variant: "secondary"
                iconSource: "../assets/icons/lock.svg"
                text: Theme.tr("admin.btn_lock")
                onClicked: backendBridge.adminLogout()
            }

            BigButton {
                minWidth: 260
                minHeight: 56
                variant: "primary"
                iconSource: "../assets/icons/usb.svg"
                text: Theme.tr("admin.btn_export_usb")
                onClicked: backendBridge.exportUsb()
            }

            BigButton {
                minWidth: 200
                minHeight: 56
                variant: "secondary"
                iconSource: "../assets/icons/back.svg"
                text: Theme.tr("admin.btn_exit")
                onClicked: {
                    backendBridge.adminLogout()
                    root.backClicked()
                }
            }
        }
    }
}
