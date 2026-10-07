pragma Singleton
import QtQuick

QtObject {
    id: root

    // --- Colors (High Contrast WCAG AA/AAA for Sunlight & Cockpit Readability) ---
    readonly property color backgroundDark: "#0B0F19"
    readonly property color surfaceDark: "#151B28"
    readonly property color surfaceElevated: "#1F293D"
    readonly property color surfaceBorder: "#2E3D59"

    readonly property color textPrimary: "#FFFFFF"
    readonly property color textSecondary: "#94A3B8"
    readonly property color textMuted: "#64748B"

    readonly property color colorSuccess: "#16A34A"       // Solid Green (Check/Pass)
    readonly property color colorSuccessBg: "#14532D"
    readonly property color colorError: "#DC2626"         // Solid Red (Violation/Fail)
    readonly property color colorErrorBg: "#7F1D1D"
    readonly property color colorWarning: "#D97706"       // Amber (Checking/Caution)
    readonly property color colorWarningBg: "#78350F"
    readonly property color colorCritical: "#991B1B"      // Deep urgent red
    readonly property color colorCriticalBg: "#450A0A"
    readonly property color colorAccent: "#2563EB"        // Action Blue
    readonly property color colorAccentHover: "#3B82F6"
    readonly property color colorDisabled: "#334155"

    readonly property color overlayBackground: "#E6000000"

    // --- Typography (Large touch legibility: Body >= 22px, Headings >= 36px, HUD >= 72px) ---
    readonly property string fontFamily: "Segoe UI, Roboto, Inter, Helvetica, Arial, sans-serif"

    readonly property int fontDisplay: 76      // HUD Speed and timer values
    readonly property int fontTitleLarge: 36   // Screen titles
    readonly property int fontTitle: 28        // Card headings, popup codes
    readonly property int fontHeadline: 24     // Button labels, component titles
    readonly property int fontBody: 22         // General text (Strict min 22px)
    readonly property int fontSub: 18          // Meta captions, hashes
    readonly property int fontSmall: 16        // Footers

    // --- Touch Dimensions (Minimum 96x72 px for vibrating vehicle cockpit) ---
    readonly property int buttonMinHeight: 72
    readonly property int buttonMinWidth: 120
    readonly property int buttonLargeHeight: 84
    readonly property int buttonLargeWidth: 280

    readonly property int touchPadding: 16
    readonly property int touchSpacing: 24
    readonly property int itemSpacing: 16

    readonly property int radiusSmall: 8
    readonly property int radiusMedium: 12
    readonly property int radiusLarge: 20

    // --- Semantic Color Tokens ---
    readonly property color background: backgroundDark
    readonly property color surface: surfaceDark
    readonly property color border: surfaceBorder
    readonly property color divider: "#1E293B"

    readonly property color primary: colorAccent
    readonly property color secondary: "#475569"
    readonly property color success: colorSuccess
    readonly property color warning: colorWarning
    readonly property color danger: colorError
    readonly property color critical: colorCritical
    readonly property color info: "#0284C7"

    // --- Typography Hierarchy ---
    readonly property int fontH1: fontTitleLarge
    readonly property int fontH2: fontTitle
    readonly property int fontH3: fontHeadline
    readonly property int fontBodySmall: 18
    readonly property int fontCaption: 14
    readonly property int fontButton: 20
    readonly property int fontStatus: 16

    // Touch Target
    readonly property int minTouchTarget: 48

    // --- Timings & Animations ---
    readonly property int debounceDelayMs: 300
    readonly property int animDurationFast: 150
    readonly property int animDurationNormal: 250

    // --- Reactive Translation Helpers ---

    function tr(key) {
        if (typeof i18n !== "undefined" && i18n) {
            var _l = i18n.currentLanguage
            return i18n.t(key)
        }
        return key
    }

    function trf(key, arg) {
        if (typeof i18n !== "undefined" && i18n) {
            var _l = i18n.currentLanguage
            return i18n.tf(key, arg)
        }
        return key
    }

    function trPlural(key, count) {
        if (typeof i18n !== "undefined" && i18n) {
            var _l = i18n.currentLanguage
            return i18n.t_plural(key, count)
        }
        return count + " " + key
    }
}
