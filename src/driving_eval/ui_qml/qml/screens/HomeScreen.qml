import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    signal startTestClicked()
    signal precheckClicked()
    signal settingsClicked()

    // Background
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
        title: "AVTOMATLASHTIRILGAN HAYDASH IMTIHONI"
        subtitle: "4-Kamerali Offline AI Baholash Tizimi"
        carId: backendBridge.carId
        showBack: false
        showSettings: true
        onSettingsClicked: root.settingsClicked()
    }

    // Main Center Content
    Column {
        anchors.centerIn: parent
        spacing: 36
        width: Math.min(parent.width - 64, 800)

        // Car / Driving Evaluation Emblem
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 110
            height: 110
            source: "../assets/icons/car.svg"
            fillMode: Image.PreserveAspectFit
        }

        // Title & Description
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "HAYDASH MALAKASINI BAHOLASH"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitleLarge
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: backendBridge.precheckPassed 
                    ? "Barcha tizimlar soz holatda. Imtihonni boshlashga tayyor."
                    : "⚠️ Tizim ishga tushirildi. Avval uskunalar tekshiruvini (Pre-check) o'tkazing."
                color: backendBridge.precheckPassed ? Theme.colorSuccess : Theme.colorWarning
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
            }
        }

        // Action Buttons
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 20

            BigButton {
                anchors.horizontalCenter: parent.horizontalCenter
                minWidth: Theme.buttonLargeWidth + 60
                minHeight: Theme.buttonLargeHeight
                variant: backendBridge.precheckPassed ? "success" : "secondary"
                enabled: backendBridge.precheckPassed
                iconSource: "../assets/icons/check.svg"
                text: "TESTNI BOSHLASH"
                onClicked: root.startTestClicked()
            }

            BigButton {
                anchors.horizontalCenter: parent.horizontalCenter
                minWidth: Theme.buttonLargeWidth + 60
                minHeight: 64
                variant: backendBridge.precheckPassed ? "secondary" : "primary"
                iconSource: "../assets/icons/refresh.svg"
                text: backendBridge.precheckPassed ? "QAYTA PRE-CHECK" : "TIZIMNI TEKSHIRISH (PRE-CHECK)"
                onClicked: root.precheckClicked()
            }
        }
    }

    // Bottom Status Strip
    BottomBar {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        Row {
            anchors.centerIn: parent
            spacing: 40

            Text {
                text: "Qoidalar: " + backendBridge.rulesVersion
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
            }

            Text {
                text: "Holat: " + (backendBridge.isConnected ? "100% OFFLINE ISHONCHLI" : "ALOQA YO'Q")
                color: backendBridge.isConnected ? Theme.colorSuccess : Theme.colorError
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSub
                font.bold: true
            }
        }
    }
}
