"""Uzbek language localization string dictionary."""

TEXTS_UZ = {
    "app_title": "Avtomatlashtirilgan 4-Kamerali Offline Haydash Imtihon Tizimi",
    "home_title": "Nomzod Ma'lumotlari",
    "student_passport": "Pasport Seriya va Raqami (yoki JSHSHIR):",
    "student_name": "Ismi:",
    "student_surname": "Familiyasi:",
    "btn_start_precheck": "TIZIMNI TEKSHIRISH (PRE-CHECK)",
    "precheck_title": "Uskunalar va Tizim Pre-Check Tekshiruvi",
    "btn_recheck": "QAYTA TEKSHIRISH",
    "btn_to_test_ready": "IMTIHONNI BOSHLASHGA O'TISH",
    "precheck_blocked": "DIQQAT: Majburiy komponent nosozligi tufayli test boshlanishi bloklandi!",
    "test_ready_title": "Imtihon Boshlanishiga Tayyor",
    "btn_start_test": "TESTNI BOSHLASH",
    "hud_time": "Vaqt:",
    "hud_speed": "Tezlik:",
    "hud_exercise": "Joriy Mashq:",
    "hud_penalty": "Jami Jarima:",
    "hud_violations_count": "Qoidabuzarliklar:",
    "btn_finish_test": "TESTNI YAKUNLASH",
    "result_title": "Imtihon Yakuniy Natijasi",
    "pass_label": "MUVAFFAQIYATLI O'TDI (PASS)",
    "fail_label": "YIQILDI (FAIL)",
    "final_score": "Yakuniy Ball:",
    "btn_view_evidence": "DALILNI KO'RISH",
    "btn_export_pdf": "PDF BAYONNOMA YUKLASH",
    "btn_export_usb": "USB GA EKSPORT QILISH",
    "btn_next_student": "KEYINGI NOMZODGA O'TISH",
    "settings_title": "Tizim Sozlamalari (Administrator)",
    "admin_pin_prompt": "Admin PIN kodini kiriting:",
    "btn_unlock": "OCHISH",
    "critical_violation_msg": "Kritik qoidabuzarlik! Imtihon to'xtatildi.",
}


def tr(key: str) -> str:
    """Translates a key into Uzbek."""
    return TEXTS_UZ.get(key, key)
