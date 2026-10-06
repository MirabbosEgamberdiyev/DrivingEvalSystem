"""Official exam evaluation report generator in PDF format using ReportLab.

Embeds candidate information, itemized penalties, inspector suspect list,
and cryptographic SHA-256 root hash for tamper verification.
"""

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_pdf_report(
    output_path: str | Path,
    session_data: dict[str, Any],
    student_data: dict[str, Any],
    vehicle_data: dict[str, Any],
    violations: list[dict[str, Any]],
    root_hash: str,
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        textColor=colors.HexColor("#1A365D"),
    )
    h2_style = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
    )
    normal_style = styles["Normal"]

    elements = []

    # Title
    elements.append(Paragraph("AVTOMOBIL HAYDASH IMTIHONI RASMIY NATIJA BAYONNOMASI", title_style))
    elements.append(Spacer(1, 15))

    # Candidate & Session Summary Table
    is_pass = session_data.get("result") == "PASS"
    result_color = colors.HexColor("#2E7D32") if is_pass else colors.HexColor("#C62828")

    summary_data = [
        [
            Paragraph("<b>Nomzod F.I.SH:</b>", normal_style),
            Paragraph(f"{student_data.get('last_name', '')} {student_data.get('first_name', '')}", normal_style),
            Paragraph("<b>Imtihon ID:</b>", normal_style),
            Paragraph(session_data.get("id", ""), normal_style),
        ],
        [
            Paragraph("<b>Pasport / JSHSHIR:</b>", normal_style),
            Paragraph(student_data.get("passport_id", ""), normal_style),
            Paragraph("<b>Sana / Vaqt:</b>", normal_style),
            Paragraph(session_data.get("started_at", "")[:19], normal_style),
        ],
        [
            Paragraph("<b>Avtomobil:</b>", normal_style),
            Paragraph(f"{vehicle_data.get('model', '')} ({vehicle_data.get('plate_number', '')})", normal_style),
            Paragraph("<b>Yakuniy Ball:</b>", normal_style),
            Paragraph(f"<b>{session_data.get('score', 0)} / 100</b>", normal_style),
        ],
        [
            Paragraph("<b>Qoidalar Versiyasi:</b>", normal_style),
            Paragraph(session_data.get("rules_version", "1.0.0"), normal_style),
            Paragraph("<b>XULOSA (NATIJA):</b>", normal_style),
            Paragraph(f"<font color='{result_color.hexval()}'><b>{session_data.get('result', 'FAIL')}</b></font>", normal_style),
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
    elements.append(Paragraph("Tasdiqlangan Qoidabuzarliklar (Jarima Hisoblangan):", h2_style))
    elements.append(Spacer(1, 6))

    confirmed_v = [v for v in violations if v.get("status") == "CONFIRMED"]
    if confirmed_v:
        v_headers = [["№", "Vaqt", "Mashq", "Qoida Nomi", "Ball", "Kritik"]]
        v_rows = []
        for idx, v in enumerate(confirmed_v, 1):
            ts = v.get("timestamp", "")[11:19]
            crit_badge = "HA" if v.get("critical") else "YO'Q"
            v_rows.append([
                str(idx),
                ts,
                v.get("exercise", ""),
                Paragraph(v.get("title", v.get("rule_code", "")), normal_style),
                f"-{v.get('penalty', 0)}",
                crit_badge,
            ])
        v_table = Table(v_headers + v_rows, colWidths=[25, 60, 95, 230, 50, 60])
        v_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ED8936")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(v_table)
    else:
        elements.append(Paragraph("<i>Hech qanday tasdiqlangan qoidabuzarlik qayd etilmadi.</i>", normal_style))

    elements.append(Spacer(1, 15))

    # SUSPECT Events Breakdown
    elements.append(Paragraph("Shubhali Hodisalar (Inspektor Ko'rigi Uchun, Jarimasiz):", h2_style))
    elements.append(Spacer(1, 6))

    suspect_v = [v for v in violations if v.get("status") == "SUSPECT"]
    if suspect_v:
        s_headers = [["№", "Vaqt", "Kamera", "Qoida", "Ishonch", "Holat"]]
        s_rows = []
        for idx, sv in enumerate(suspect_v, 1):
            ts = sv.get("timestamp", "")[11:19]
            s_rows.append([
                str(idx),
                ts,
                sv.get("camera", ""),
                Paragraph(sv.get("title", sv.get("rule_code", "")), normal_style),
                f"{sv.get('confidence', 0):.2f}",
                "SUSPECT (0 ball)",
            ])
        s_table = Table(s_headers + s_rows, colWidths=[25, 60, 75, 220, 60, 80])
        s_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A5568")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ])
        )
        elements.append(s_table)
    else:
        elements.append(Paragraph("<i>Shubhali holatlar mavjud emas.</i>", normal_style))

    elements.append(Spacer(1, 20))

    # Cryptographic Hash Chaining Verification Footer
    footer_text = f"""
    <b>Xavfsizlik va Kriptografik Autentifikatsiya:</b><br/>
    Ushbu bayonnoma 100% offline standalone tizim tomonidan yaratildi.<br/>
    <b>SHA-256 Hash Zanjiri Ildizi:</b> <font face="Courier" size="8">{root_hash}</font><br/>
    <i>Har qanday o'zgartirish yoki dalil buzilishi xesh zanjirining mos kelmasligiga olib keladi.</i>
    """
    elements.append(Paragraph(footer_text, normal_style))

    doc.build(elements)
    return out
