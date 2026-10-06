"""Official exam evaluation report generator in PDF format using ReportLab.

Embeds candidate information, itemized penalties, inspector suspect list,
and cryptographic SHA-256 root hash for tamper verification.
Supports all 3 languages (uz-Latn, uz-Cyrl, ru) with Unicode TrueType font embedding.
"""

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Register Unicode TrueType font for Cyrillic support (uz-Cyrl and ru)
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

for font_path, bold_path in [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
]:
    if Path(font_path).exists():
        try:
            pdfmetrics.registerFont(TTFont("AppUnicode", font_path))
            pdfmetrics.registerFont(
                TTFont("AppUnicode-Bold", bold_path if Path(bold_path).exists() else font_path)
            )
            FONT_NAME = "AppUnicode"
            FONT_BOLD = "AppUnicode-Bold"
            break
        except Exception:
            pass

PDF_TRANSLATIONS = {
    "uz-Latn": {
        "title": "AVTOMOBIL HAYDASH IMTIHONI RASMIY NATIJA BAYONNOMASI",
        "candidate": "Nomzod F.I.SH:",
        "exam_id": "Imtihon ID:",
        "passport": "Pasport / JSHSHIR:",
        "date_time": "Sana / Vaqt:",
        "vehicle": "Avtomobil:",
        "final_score": "Yakuniy Ball:",
        "rules_version": "Qoidalar Versiyasi:",
        "verdict": "XULOSA (NATIJA):",
        "confirmed_title": "Tasdiqlangan Qoidabuzarliklar (Jarima Hisoblangan):",
        "no_confirmed": "Hech qanday tasdiqlangan qoidabuzarlik qayd etilmadi.",
        "headers": ["№", "Vaqt", "Mashq", "Qoida Nomi", "Ball", "Kritik"],
        "yes": "HA",
        "no": "YO'Q",
        "suspect_title": "Shubhali Hodisalar (Inspektor Ko'rigi Uchun, Jarimasiz):",
        "no_suspect": "Hech qanday shubhali hodisa qayd etilmadi.",
        "suspect_headers": ["№", "Vaqt", "Kamera", "Qoida", "Ishonch", "Holat"],
        "root_hash": "Kriptografik Butunlik Xeshi (SHA-256):",
        "signatures": "Imtihon topshiruvchi: _________________   Bosh inspektor: _________________",
    },
    "uz-Cyrl": {
        "title": "АВТОМОБИЛЬ ҲАЙДАШ ИМТИҲОНИ РАСМИЙ НАТИЖА БАЁННОМАСИ",
        "candidate": "Номзод Ф.И.Ш:",
        "exam_id": "Имтиҳон ID:",
        "passport": "Паспорт / ЖШШИР:",
        "date_time": "Сана / Вақт:",
        "vehicle": "Автомобиль:",
        "final_score": "Якуний Балл:",
        "rules_version": "Қоидалар Версияси:",
        "verdict": "ХУЛОСА (НАТИЖА):",
        "confirmed_title": "Тасдиқланган Қоидабузарликлар (Жарима Ҳисобланган):",
        "no_confirmed": "Ҳеч қандай тасдиқланган қоидабузарлик қайд этилмади.",
        "headers": ["№", "Вақт", "Машқ", "Қоида Номи", "Балл", "Критик"],
        "yes": "ҲА",
        "no": "ЙЎҚ",
        "suspect_title": "Шубҳали Ҳодисалар (Инспектор Кўриги Учун, Жаримасиз):",
        "no_suspect": "Ҳеч қандай шубҳали ҳодиса қайд этилмади.",
        "suspect_headers": ["№", "Вақт", "Камера", "Қоида", "Ишонч", "Ҳолат"],
        "root_hash": "Криптографик Бутунлик Хеши (SHA-256):",
        "signatures": "Имтиҳон топширувчи: _________________   Бош инспектор: _________________",
    },
    "ru": {
        "title": "ОФИЦИАЛЬНЫЙ ПРОТОКОЛ РЕЗУЛЬТАТОВ ЭКЗАМЕНА ПО ВОЖДЕНИЮ",
        "candidate": "Ф.И.О. кандидата:",
        "exam_id": "ID экзамена:",
        "passport": "Паспорт / ПИНФЛ:",
        "date_time": "Дата / Время:",
        "vehicle": "Автомобиль:",
        "final_score": "Итоговый балл:",
        "rules_version": "Версия правил:",
        "verdict": "ЗАКЛЮЧЕНИЕ (РЕЗУЛЬТАТ):",
        "confirmed_title": "Подтверждённые нарушения (начислен штраф):",
        "no_confirmed": "Подтверждённых нарушений не зафиксировано.",
        "headers": ["№", "Время", "Упражнение", "Нарушение", "Балл", "Критич."],
        "yes": "ДА",
        "no": "НЕТ",
        "suspect_title": "Подозрительные события (для инспектора, без штрафа):",
        "no_suspect": "Подозрительных событий не зафиксировано.",
        "suspect_headers": ["№", "Время", "Камера", "Нарушение", "Доверие", "Статус"],
        "root_hash": "Криптографический хэш целостности (SHA-256):",
        "signatures": "Экзаменуемый: _________________   Главный инспектор: _________________",
    },
}


def generate_pdf_report(
    output_path: str | Path,
    session_data: dict[str, Any],
    student_data: dict[str, Any],
    vehicle_data: dict[str, Any],
    violations: list[dict[str, Any]],
    root_hash: str,
    language: str = "uz-Latn",
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lang = language if language in PDF_TRANSLATIONS else "uz-Latn"
    tr = PDF_TRANSLATIONS[lang]

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles with Unicode font
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=20,
        alignment=1,  # Center
        textColor=colors.HexColor("#1A365D"),
    )
    h2_style = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#2B6CB0"),
    )
    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=10,
        leading=13,
    )
    normal_bold = ParagraphStyle(
        "NormalBold",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=10,
        leading=13,
    )

    elements = []

    # Title
    elements.append(Paragraph(tr["title"], title_style))
    elements.append(Spacer(1, 15))

    # Candidate & Session Summary Table
    is_pass = session_data.get("result") == "PASS"
    result_color = colors.HexColor("#2E7D32") if is_pass else colors.HexColor("#C62828")

    summary_data = [
        [
            Paragraph(f"<b>{tr['candidate']}</b>", normal_bold),
            Paragraph(f"{student_data.get('last_name', '')} {student_data.get('first_name', '')}", normal_style),
            Paragraph(f"<b>{tr['exam_id']}</b>", normal_bold),
            Paragraph(session_data.get("id", ""), normal_style),
        ],
        [
            Paragraph(f"<b>{tr['passport']}</b>", normal_bold),
            Paragraph(student_data.get("passport_id", ""), normal_style),
            Paragraph(f"<b>{tr['date_time']}</b>", normal_bold),
            Paragraph(str(session_data.get("started_at", ""))[:19], normal_style),
        ],
        [
            Paragraph(f"<b>{tr['vehicle']}</b>", normal_bold),
            Paragraph(f"{vehicle_data.get('model', '')} ({vehicle_data.get('plate_number', '')})", normal_style),
            Paragraph(f"<b>{tr['final_score']}</b>", normal_bold),
            Paragraph(f"<b>{session_data.get('score', 0)} / 100</b>", normal_bold),
        ],
        [
            Paragraph(f"<b>{tr['rules_version']}</b>", normal_bold),
            Paragraph(session_data.get("rules_version", "1.0.0"), normal_style),
            Paragraph(f"<b>{tr['verdict']}</b>", normal_bold),
            Paragraph(f"<font color='{result_color.hexval()}'><b>{session_data.get('result', 'FAIL')}</b></font>", normal_bold),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[130, 140, 110, 140])
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 15))

    # Violations Breakdown
    elements.append(Paragraph(tr["confirmed_title"], h2_style))
    elements.append(Spacer(1, 6))

    confirmed_v = [v for v in violations if v.get("status") == "CONFIRMED"]
    if confirmed_v:
        v_headers = [[Paragraph(f"<b>{h}</b>", normal_bold) for h in tr["headers"]]]
        v_rows = []
        for idx, v in enumerate(confirmed_v, 1):
            ts = str(v.get("timestamp", ""))
            ts_str = ts[11:19] if len(ts) >= 19 else ts
            crit_badge = tr["yes"] if v.get("critical") else tr["no"]
            v_title = v.get("title", v.get("rule_code", ""))
            v_rows.append([
                Paragraph(str(idx), normal_style),
                Paragraph(ts_str, normal_style),
                Paragraph(str(v.get("exercise", "")), normal_style),
                Paragraph(str(v_title), normal_style),
                Paragraph(f"-{v.get('penalty', 0)}", normal_bold),
                Paragraph(crit_badge, normal_style),
            ])
        v_table = Table(v_headers + v_rows, colWidths=[25, 60, 95, 230, 50, 60])
        v_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ED8936")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(v_table)
    else:
        elements.append(Paragraph(f"<i>{tr['no_confirmed']}</i>", normal_style))

    elements.append(Spacer(1, 15))

    # SUSPECT Events Breakdown
    elements.append(Paragraph(tr["suspect_title"], h2_style))
    elements.append(Spacer(1, 6))

    suspect_v = [v for v in violations if v.get("status") == "SUSPECT"]
    if suspect_v:
        s_headers = [[Paragraph(f"<b>{h}</b>", normal_bold) for h in tr["suspect_headers"]]]
        s_rows = []
        for idx, v in enumerate(suspect_v, 1):
            ts = str(v.get("timestamp", ""))
            ts_str = ts[11:19] if len(ts) >= 19 else ts
            conf = v.get("confidence", 0.0)
            s_title = v.get("title", v.get("rule_code", ""))
            s_rows.append([
                Paragraph(str(idx), normal_style),
                Paragraph(ts_str, normal_style),
                Paragraph(str(v.get("camera", "FRONT")), normal_style),
                Paragraph(str(s_title), normal_style),
                Paragraph(f"{conf:.2f}", normal_style),
                Paragraph("SUSPECT (0)", normal_bold),
            ])
        s_table = Table(s_headers + s_rows, colWidths=[25, 60, 60, 265, 50, 60])
        s_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECC94B")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(s_table)
    else:
        elements.append(Paragraph(f"<i>{tr['no_suspect']}</i>", normal_style))

    elements.append(Spacer(1, 25))

    # Cryptographic Root Hash & Signatures
    hash_p = Paragraph(f"<b>{tr['root_hash']}</b> <font face='Courier' size='8'>{root_hash}</font>", normal_style)
    elements.append(hash_p)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(tr["signatures"], normal_style))

    doc.build(elements)
    return out
