"""
pdf_generator.py — ReportLab Platypus professional health report.
Pure Python, zero system dependencies.
"""
import io
import base64
import logging
from datetime import date
from typing import Dict, List, Optional, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, KeepTogether,
)

logger = logging.getLogger(__name__)

# ── Page geometry ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
L_MAR = R_MAR = 2.0 * cm
T_MAR          = 1.8 * cm
B_MAR          = 2.0 * cm
CW             = PAGE_W - L_MAR - R_MAR   # ~481 pt

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0f3460")
NAVY2     = colors.HexColor("#1e4080")
BLUE      = colors.HexColor("#1d4ed8")
GREEN     = colors.HexColor("#15803d")
AMBER     = colors.HexColor("#b45309")
RED       = colors.HexColor("#b91c1c")
SLATE     = colors.HexColor("#475569")
STEEL     = colors.HexColor("#64748b")
DARK_TXT  = colors.HexColor("#0f172a")
MED_TXT   = colors.HexColor("#334155")
GREEN_BG  = colors.HexColor("#f0fdf4")
AMBER_BG  = colors.HexColor("#fffbeb")
RED_BG    = colors.HexColor("#fff5f5")
BLUE_BG   = colors.HexColor("#eff6ff")
GRAY_BG   = colors.HexColor("#f8faff")
BORDER_C  = colors.HexColor("#e2e8f0")
WHITE     = colors.white

BIOMARKER_LABELS = {
    "heart_rate":               "Heart Rate",
    "blood_pressure_systolic":  "Blood Pressure (Systolic)",
    "blood_pressure_diastolic": "Blood Pressure (Diastolic)",
    "glucose":                  "Blood Glucose",
    "steps":                    "Daily Steps",
    "sleep":                    "Sleep",
}

REPORT_TYPE_LABELS = {
    "daily":     "Daily Health Report",
    "weekly":    "Weekly Health Report",
    "monthly":   "Monthly Health Report",
    "quarterly": "Quarterly Health Report",
    "annual":    "Annual Health Report",
    "custom":    "Custom Health Report",
}

STATUS_CONF = {
    "normal":     (GREEN, GREEN_BG, "NORMAL"),
    "borderline": (AMBER, AMBER_BG, "BORDERLINE"),
    "abnormal":   (RED,   RED_BG,   "ABNORMAL"),
    "no_data":    (STEEL, GRAY_BG,  "NO DATA"),
}

PRIORITY_CONF = {
    "urgent": (RED,   "URGENT"),
    "high":   (AMBER, "HIGH"),
    "medium": (BLUE,  "MEDIUM"),
    "low":    (SLATE, "LOW"),
}

TREND_CONF = {
    "improving":         ("▲ Improving",   GREEN),
    "declining":         ("▼ Declining",   RED),
    "stable":            ("→ Stable",      BLUE),
    "insufficient_data": ("— Insufficient", STEEL),
}


# ── Style factory ─────────────────────────────────────────────────────────────
def _ps(name: str, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, **kw)


def _st() -> Dict[str, ParagraphStyle]:
    return {
        # cover
        "brand":      _ps("brand",  fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#e0f2fe")),
        "rtype":      _ps("rtype",  fontName="Helvetica-Bold", fontSize=9,  leading=11, textColor=colors.HexColor("#90caf9"), alignment=TA_RIGHT),
        "cvr_title":  _ps("cvrT",   fontName="Helvetica-Bold", fontSize=34, leading=38, textColor=WHITE),
        "cvr_sub":    _ps("cvrS",   fontName="Helvetica",      fontSize=11, leading=14, textColor=colors.HexColor("#93c5fd")),
        "cvr_key":    _ps("cvrK",   fontName="Helvetica-Bold", fontSize=7,  leading=10, textColor=colors.HexColor("#64b5f6")),
        "cvr_val":    _ps("cvrV",   fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#f0f9ff")),
        # sections
        "sec":        _ps("sec",    fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=NAVY),
        # metric cards
        "ml":         _ps("ml",     fontName="Helvetica-Bold", fontSize=7,  leading=9,  textColor=STEEL),
        "mu":         _ps("mu",     fontName="Helvetica",      fontSize=9,  leading=11, textColor=STEEL),
        # biomarker cards
        "bn":         _ps("bn",     fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=DARK_TXT),
        "bsl":        _ps("bsl",    fontName="Helvetica-Bold", fontSize=7,  leading=9,  textColor=STEEL,    alignment=TA_CENTER),
        "bsv":        _ps("bsv",    fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=DARK_TXT, alignment=TA_CENTER),
        "bnm":        _ps("bnm",    fontName="Helvetica",      fontSize=8,  leading=10, textColor=STEEL),
        # insight
        "ins_title":  _ps("insT",   fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=NAVY),
        "ins_txt":    _ps("insX",   fontName="Helvetica",      fontSize=9,  leading=12, textColor=MED_TXT),
        # misc
        "body":       _ps("body",   fontName="Helvetica",      fontSize=9,  leading=12, textColor=MED_TXT),
        "nm":         _ps("nm",     fontName="Helvetica",      fontSize=8.5, leading=12, textColor=STEEL),
        "chip":       _ps("chip",   fontName="Helvetica-Bold", fontSize=8,  leading=10, textColor=SLATE,    alignment=TA_CENTER),
    }


# ── Section title ─────────────────────────────────────────────────────────────
def _section(text: str, st: dict) -> Table:
    t = Table([[Paragraph(text.upper(), st["sec"])]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LINEBELOW",     (0,0), (-1,-1), 1.5, NAVY),
    ]))
    return t


# ── Cover ─────────────────────────────────────────────────────────────────────
def _build_cover(patient_name, report_type, date_from_str, date_to_str,
                  generated_date, total_readings, st):
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type.title())

    # Inner metadata table (4 columns, 2 rows: keys + values)
    meta_cw = CW / 4
    meta = Table(
        [
            [Paragraph("PATIENT NAME", st["cvr_key"]),
             Paragraph("REPORT PERIOD", st["cvr_key"]),
             Paragraph("DATE GENERATED", st["cvr_key"]),
             Paragraph("DATA POINTS", st["cvr_key"])],
            [Paragraph(patient_name, st["cvr_val"]),
             Paragraph(f"{date_from_str} – {date_to_str}", st["cvr_val"]),
             Paragraph(generated_date, st["cvr_val"]),
             Paragraph(str(total_readings), st["cvr_val"])],
        ],
        colWidths=[meta_cw] * 4,
    )
    meta.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))

    # Outer cover table — dark navy background across full content width
    cover_data = [
        [Paragraph("● Pulse Health", st["brand"]),
         Paragraph(type_label, st["rtype"])],          # row 0: brand bar
        [Spacer(1, 12), ""],                            # row 1: gap
        [Paragraph(type_label, st["cvr_title"]), ""],  # row 2: big title
        [Paragraph("Patient Health Analysis &amp; Clinical Insights Report",
                   st["cvr_sub"]), ""],                # row 3: subtitle
        [Spacer(1, 16), ""],                           # row 4: gap before divider
        [meta, ""],                                    # row 5: metadata
        [Spacer(1, 8), ""],                            # row 6: bottom pad
    ]

    cover = Table(cover_data, colWidths=[CW * 0.68, CW * 0.32])
    cover.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("SPAN",          (0,2), (1,2)),
        ("SPAN",          (0,3), (1,3)),
        ("SPAN",          (0,5), (1,5)),
        ("SPAN",          (0,6), (1,6)),
        ("LEFTPADDING",   (0,0), (-1,-1), 36),
        ("RIGHTPADDING",  (0,0), (-1,-1), 36),
        ("TOPPADDING",    (0,0), (-1,0),  28),
        ("TOPPADDING",    (0,1), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        # Thin divider above metadata
        ("LINEABOVE",     (0,5), (-1,5), 0.5, NAVY2),
    ]))

    return [cover, Spacer(1, 0.5 * cm)]


# ── Metric cards row ──────────────────────────────────────────────────────────
def _metric_cards_row(cards: list, st: dict) -> Table:
    """
    cards: list of dicts — label, value, unit, badge, top_color, bg_color, badge_color
    """
    n = len(cards)
    col_w = CW / n

    def _cell(c):
        badge_style = _ps(f"_b{id(c)}_", fontName="Helvetica-Bold",
                          fontSize=7.5, leading=9, textColor=c["badge_color"])
        val_style   = _ps(f"_v{id(c)}_", fontName="Helvetica-Bold",
                          fontSize=24, leading=26, textColor=DARK_TXT)
        return Table(
            [
                [Paragraph(c["label"].upper(), st["ml"])],
                [Paragraph(str(c["value"]), val_style)],
                [Paragraph(c["unit"], st["mu"])],
                [Spacer(1, 4)],
                [Paragraph(c["badge"], badge_style)],
            ],
            colWidths=[col_w - 24],
        )

    cells = [_cell(c) for c in cards]
    t = Table([cells], colWidths=[col_w] * n)

    ts_cmds = [
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("GRID",          (0,0), (-1,-1), 0.5, BORDER_C),
    ]
    for i, c in enumerate(cards):
        ts_cmds += [
            ("LINEABOVE",  (i,0), (i,0), 3, c["top_color"]),
            ("BACKGROUND", (i,0), (i,-1), c["bg_color"]),
        ]
    t.setStyle(TableStyle(ts_cmds))
    return t


# ── Health score section ──────────────────────────────────────────────────────
def _score_color(score):
    if score is None or score < 40: return (RED,   RED_BG)
    if score < 70:                   return (AMBER, AMBER_BG)
    return (GREEN, GREEN_BG)


def _build_health_score(avg_score, best_score, worst_score, score_trend,
                         total_readings, score_chart, st):
    items = [Spacer(1, 0.35*cm), _section("Health Score Overview", st), Spacer(1, 0.25*cm)]

    trend_label = {"improving": "↑ Improving", "declining": "↓ Declining",
                   "stable": "→ Stable"}.get(score_trend, "Tracking")
    sc, sbg = _score_color(avg_score)

    cards = [{"label": "Avg Health Score", "value": int(round(avg_score)),
               "unit": "/ 100", "badge": trend_label,
               "top_color": sc, "bg_color": sbg, "badge_color": sc}]
    if best_score is not None:
        cards.append({"label": "Best Score", "value": int(round(best_score)),
                       "unit": "/ 100", "badge": "Peak",
                       "top_color": GREEN, "bg_color": GREEN_BG, "badge_color": GREEN})
    if worst_score is not None:
        wc, wbg = _score_color(worst_score)
        cards.append({"label": "Lowest Score", "value": int(round(worst_score)),
                       "unit": "/ 100", "badge": "Low",
                       "top_color": wc, "bg_color": wbg, "badge_color": wc})
    cards.append({"label": "Total Readings", "value": total_readings,
                   "unit": "data points", "badge": "Recorded",
                   "top_color": BLUE, "bg_color": BLUE_BG, "badge_color": BLUE})

    items.append(_metric_cards_row(cards, st))

    if score_chart:
        items.append(Spacer(1, 0.2*cm))
        img = Image(io.BytesIO(base64.b64decode(score_chart)),
                    width=CW, height=CW * 0.28)
        chart_t = Table([[img]], colWidths=[CW])
        chart_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
            ("BOX",           (0,0), (-1,-1), 0.5, BORDER_C),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("RIGHTPADDING",  (0,0), (-1,-1), 4),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        items.append(chart_t)
    return items


def _build_no_score(total_readings, st):
    items = [Spacer(1, 0.35*cm), _section("Health Score Overview", st), Spacer(1, 0.25*cm)]
    items.append(_metric_cards_row([{
        "label": "Total Readings", "value": total_readings, "unit": "data points",
        "badge": "No health score data recorded yet",
        "top_color": BLUE, "bg_color": BLUE_BG, "badge_color": STEEL,
    }], st))
    return items


# ── Clinical insights ─────────────────────────────────────────────────────────
def _build_insights(active_stats, score_trend, st):
    items = []
    rows = []

    for s in active_stats:
        if s.get("status") == "abnormal":
            rows.append((RED,   "■",
                f"<b>{s['label']}</b> — Average {s['avg']} {s['unit']} is outside normal range. Clinical review recommended."))
        elif s.get("status") == "borderline":
            rows.append((AMBER, "■",
                f"<b>{s['label']}</b> — Borderline readings detected (avg {s['avg']} {s['unit']}). Monitor closely."))
        if s.get("trend") == "declining":
            rows.append((AMBER, "▼", f"<b>{s['label']}</b> values are trending downward over this period."))
        elif s.get("trend") == "improving":
            rows.append((GREEN, "▲", f"<b>{s['label']}</b> shows a positive improving trend. Continue current regimen."))

    if score_trend == "improving":
        rows.append((GREEN, "▲", "Overall health score <b>improved</b> during this period. Patient trending positively."))
    elif score_trend == "declining":
        rows.append((RED,   "▼", "Overall health score <b>declined</b> during this period. Recommend follow-up review."))

    if not rows:
        return items

    items += [Spacer(1, 0.35*cm), _section("Clinical Insights", st), Spacer(1, 0.2*cm)]

    panel_rows = [[Paragraph("Automated Analysis Highlights", st["ins_title"])]]
    for color, sym, text in rows:
        sym_s = _ps(f"_s{id(text)}_", fontName="Helvetica-Bold", fontSize=11,
                    leading=13, textColor=color)
        txt_s = _ps(f"_t{id(text)}_", fontName="Helvetica", fontSize=9,
                    leading=12, textColor=MED_TXT)
        inner = Table([[Paragraph(sym, sym_s), Paragraph(text, txt_s)]],
                      colWidths=[14, CW - 14 - 32])
        inner.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        panel_rows.append([inner])

    panel = Table(panel_rows, colWidths=[CW - 4])
    panel.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
        ("LINEBEFORE",    (0,0), (-1,-1), 4, NAVY),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (0,0),   10),
        ("TOPPADDING",    (0,1), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-2), 4),
        ("BOTTOMPADDING", (0,-1),(-1,-1), 12),
    ]))
    items.append(panel)
    return items


# ── Biomarker cards ───────────────────────────────────────────────────────────
def _bio_card(s: dict, card_w: float, st: dict) -> Table:
    sc, sbg, slabel = STATUS_CONF.get(s.get("status", "no_data"), STATUS_CONF["no_data"])

    # ── header ────────────────────────────────────────────────────────────────
    status_s = _ps(f"_ss{id(s)}_", fontName="Helvetica-Bold", fontSize=7,
                   leading=9, textColor=sc)
    hdr = Table(
        [[Paragraph(s.get("label", ""), st["bn"]),
          Paragraph(slabel, status_s)]],
        colWidths=[card_w * 0.62, card_w * 0.38],
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
        ("LINEBELOW",     (0,0), (-1,-1), 0.5, BORDER_C),
        ("LINEABOVE",     (0,0), (-1,0),  3,   sc),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (1,0), (1,-1), "RIGHT"),
    ]))

    # ── body ──────────────────────────────────────────────────────────────────
    body_parts = []
    inner_w = card_w - 20   # 10px padding each side

    if s.get("status") != "no_data" and s.get("avg") is not None:
        # Stat grid
        q = inner_w / 4
        stat_t = Table(
            [
                [Paragraph("Average", st["bsl"]), Paragraph("Min", st["bsl"]),
                 Paragraph("Max", st["bsl"]),     Paragraph("Latest", st["bsl"])],
                [Paragraph(str(s.get("avg", "—")), st["bsv"]),
                 Paragraph(str(s.get("min", "—")), st["bsv"]),
                 Paragraph(str(s.get("max", "—")), st["bsv"]),
                 Paragraph(str(s.get("latest", "—")), st["bsv"])],
            ],
            colWidths=[q] * 4,
        )
        stat_t.setStyle(TableStyle([
            ("ALIGN",        (0,0), (-1,-1), "CENTER"),
            ("GRID",         (0,0), (-1,-1), 0.5, BORDER_C),
            ("BACKGROUND",   (0,0), (-1,0),  GRAY_BG),
            ("TOPPADDING",   (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
            ("LEFTPADDING",  (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ]))
        body_parts.append(stat_t)
        body_parts.append(Spacer(1, 6))

        # Normal range
        days_total = s.get("days_total", 0)
        if days_total > 0:
            pct = int(round(s.get("days_in_normal", 0) / days_total * 100))
            body_parts.append(Paragraph(
                f"Within normal range: <b>{pct}%</b> of {days_total} days  •  "
                f"{s.get('readings_count', 0)} readings",
                st["bnm"],
            ))
            body_parts.append(Spacer(1, 4))

        # Chart
        if s.get("chart"):
            body_parts.append(
                Image(io.BytesIO(base64.b64decode(s["chart"])),
                      width=inner_w, height=inner_w * 0.38)
            )
            body_parts.append(Spacer(1, 5))

        # Trend
        trend_text, trend_color = TREND_CONF.get(
            s.get("trend", "insufficient_data"), TREND_CONF["insufficient_data"])
        unit = s.get("unit", "")
        trend_s = _ps(f"_tr{id(s)}_", fontName="Helvetica-Bold", fontSize=8.5,
                      leading=11, textColor=trend_color)
        lbl_s   = _ps(f"_tl{id(s)}_", fontName="Helvetica", fontSize=8.5,
                      leading=11, textColor=MED_TXT)
        unit_s  = _ps(f"_tu{id(s)}_", fontName="Helvetica", fontSize=8.5,
                      leading=11, textColor=STEEL)
        trend_row = Table(
            [[Paragraph("Trend: ", lbl_s),
              Paragraph(trend_text, trend_s),
              Paragraph(f"  Unit: {unit}", unit_s)]],
            colWidths=[38, 80, inner_w - 118],
        )
        trend_row.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ("LINEABOVE",     (0,0), (-1,0),  0.5, BORDER_C),
        ]))
        body_parts.append(Spacer(1, 2))
        body_parts.append(trend_row)
    else:
        body_parts.append(Paragraph(
            "No readings logged for this biomarker during the selected period.",
            _ps("_nd_", fontName="Helvetica", fontSize=9, leading=12, textColor=STEEL)
        ))

    body_rows = [[part] for part in body_parts]
    body_inner = Table(body_rows, colWidths=[inner_w])
    body_inner.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    body_wrap = Table([[body_inner]], colWidths=[card_w])
    body_wrap.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))

    card = Table([[hdr], [body_wrap]], colWidths=[card_w])
    card.setStyle(TableStyle([
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER_C),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return card


def _build_biomarkers(active_stats: list, st: dict) -> list:
    if not active_stats:
        return []
    items = [Spacer(1, 0.35*cm), _section("Biomarker Analysis", st), Spacer(1, 0.25*cm)]
    GAP    = 10
    card_w = (CW - GAP) / 2

    for i in range(0, len(active_stats), 2):
        left  = _bio_card(active_stats[i], card_w, st)
        right = (_bio_card(active_stats[i+1], card_w, st)
                 if i + 1 < len(active_stats)
                 else Table([[""]], colWidths=[card_w]))

        row = Table([[left, Spacer(GAP, 1), right]],
                    colWidths=[card_w, GAP, card_w])
        row.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        items.append(KeepTogether(row))
    return items


# ── Goal tracking ─────────────────────────────────────────────────────────────
def _build_goals(goals, completed_goals, missed_goals, goal_rate, st):
    if not goals:
        return []
    items = [Spacer(1, 0.35*cm), _section("Goal Tracking", st), Spacer(1, 0.25*cm)]

    cards = [
        {"label": "Total Tracked",  "value": len(goals),           "unit": "", "badge": "Recorded",
         "top_color": BLUE,  "bg_color": BLUE_BG,  "badge_color": BLUE},
        {"label": "Completed",      "value": len(completed_goals), "unit": "", "badge": "Achieved",
         "top_color": GREEN, "bg_color": GREEN_BG, "badge_color": GREEN},
        {"label": "Missed",         "value": len(missed_goals),    "unit": "", "badge": "Not met",
         "top_color": RED,   "bg_color": RED_BG,   "badge_color": RED},
    ]
    if goal_rate is not None:
        gc = GREEN if goal_rate >= 75 else (AMBER if goal_rate >= 40 else RED)
        gb = GREEN_BG if goal_rate >= 75 else (AMBER_BG if goal_rate >= 40 else RED_BG)
        cards.append({"label": "Completion Rate", "value": f"{int(round(goal_rate))}%",
                       "unit": "", "badge": "of goals met",
                       "top_color": gc, "bg_color": gb, "badge_color": gc})

    items.append(_metric_cards_row(cards, st))
    items.append(Spacer(1, 0.2*cm))

    for goal_list, title, title_color, bg, border in [
        (completed_goals, "✓  Completed Goals", GREEN, GREEN_BG, GREEN),
        (missed_goals,    "✗  Missed Goals",    RED,   RED_BG,   RED),
    ]:
        if not goal_list:
            continue
        title_s = _ps(f"_gl{id(goal_list)}_", fontName="Helvetica-Bold",
                      fontSize=8, leading=10, textColor=title_color)
        rows = [[Paragraph(title, title_s)]]
        for g in goal_list[:10]:
            freq = (g.get("goal_frequency") or "").title()
            dt   = g.get("completion_date", "")
            txt  = f"• {g.get('goal_text', '')}"
            meta = f"  ({freq} · {dt})"
            gi_s   = _ps(f"_gi{id(g)}_",  fontName="Helvetica",      fontSize=9, leading=12, textColor=DARK_TXT)
            meta_s = _ps(f"_gm{id(g)}_", fontName="Helvetica",      fontSize=8, leading=10, textColor=STEEL)
            rows.append([Table([[Paragraph(txt, gi_s), Paragraph(meta, meta_s)]],
                               colWidths=[CW * 0.65, CW * 0.25])])
        t = Table(rows, colWidths=[CW - 24])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), bg),
            ("LINEBEFORE",    (0,0), (-1,-1), 3, border),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
            ("TOPPADDING",    (0,0), (0,0),   8),
            ("TOPPADDING",    (0,1), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-2), 4),
            ("BOTTOMPADDING", (0,-1),(-1,-1), 10),
        ]))
        items += [t, Spacer(1, 0.15*cm)]
    return items


# ── AI Recommendations ────────────────────────────────────────────────────────
def _build_recommendations(recommendations: list, st: dict) -> list:
    if not recommendations:
        return []
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    recs = sorted(recommendations,
                  key=lambda r: priority_order.get(r.get("priority", "low"), 3))

    items = [Spacer(1, 0.35*cm), _section("AI Health Recommendations", st)]

    for rec in recs:
        priority = rec.get("priority", "low")
        pc, plabel = PRIORITY_CONF.get(priority, PRIORITY_CONF["low"])
        category = (rec.get("category") or "").replace("_", " ").title()
        consult  = rec.get("requires_professional_consultation", False)

        pri_s = _ps(f"_pr{id(rec)}_", fontName="Helvetica-Bold", fontSize=7,
                    leading=9, textColor=pc)
        cat_s = _ps(f"_ca{id(rec)}_", fontName="Helvetica", fontSize=8,
                    leading=10, textColor=STEEL)
        con_s = _ps(f"_cn{id(rec)}_", fontName="Helvetica-Bold", fontSize=7.5,
                    leading=9, textColor=colors.HexColor("#92400e"))

        # header row
        hdr_right = [Paragraph(category, cat_s)]
        if consult:
            hdr_right.append(Paragraph(" ⬤ Consult Healthcare Provider", con_s))
        hdr_right_cell = Table([[p] for p in hdr_right], colWidths=[CW * 0.65])
        hdr_right_cell.setStyle(TableStyle([
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))

        hdr = Table([[Paragraph(f"{plabel} PRIORITY", pri_s), hdr_right_cell]],
                    colWidths=[CW * 0.28, CW * 0.72])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
            ("LINEBELOW",     (0,0), (-1,-1), 0.5, BORDER_C),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
            ("TOPPADDING",    (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))

        # body
        title_s = _ps(f"_rt{id(rec)}_", fontName="Helvetica-Bold", fontSize=11,
                      leading=14, textColor=DARK_TXT)
        desc_s  = _ps(f"_rd{id(rec)}_", fontName="Helvetica", fontSize=9,
                      leading=13, textColor=MED_TXT)
        step_s  = _ps(f"_rs{id(rec)}_", fontName="Helvetica", fontSize=8.5,
                      leading=12, textColor=SLATE)

        body_items = [
            Paragraph(rec.get("title", ""), title_s),
            Spacer(1, 5),
            Paragraph(rec.get("description", ""), desc_s),
        ]
        for idx, step in enumerate((rec.get("action_steps") or [])[:3]):
            instruction = step.get("instruction", "") if isinstance(step, dict) else str(step)
            body_items += [Spacer(1, 3), Paragraph(f"{idx+1}. {instruction}", step_s)]

        body_rows = [[item] for item in body_items]
        body = Table(body_rows, colWidths=[CW - 24])
        body.setStyle(TableStyle([
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        body_wrap = Table([[body]], colWidths=[CW])
        body_wrap.setStyle(TableStyle([
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ]))

        card = Table([[hdr], [body_wrap]], colWidths=[CW])
        card.setStyle(TableStyle([
            ("BOX",           (0,0), (-1,-1), 0.5, BORDER_C),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        items += [Spacer(1, 0.2*cm), KeepTogether(card)]
    return items


# ── Pet companion section ─────────────────────────────────────────────────────
PET_EMOJIS = {
    "cat": "Cat", "dog": "Dog", "elephant": "Elephant",
    "lion": "Lion", "owl": "Owl", "panda": "Panda",
    "penguin": "Penguin", "raccoon": "Raccoon",
}

def _build_pet_section(pet_info: dict, pet_chart: Optional[str], st: dict) -> list:
    if not pet_info:
        return []

    items = [Spacer(1, 0.35*cm), _section("Pet Companion Status", st), Spacer(1, 0.25*cm)]

    emotion      = pet_info.get("current_emotion", "neutral")
    pet_name     = pet_info.get("pet_name") or pet_info.get("display_name") or "Pet"
    pet_type     = PET_EMOJIS.get(pet_info.get("pet_key", ""), pet_info.get("display_name", "Pet"))
    score        = float(pet_info.get("current_score") or 0)
    events       = [e for e in pet_info.get("events", [])
                    if e.get("previous_emotion") != e.get("new_emotion")]
    accessory    = pet_info.get("accessory_unlocked", False)

    emo_color = {"happy": GREEN, "neutral": AMBER, "sad": BLUE}.get(emotion, STEEL)
    emo_bg    = {"happy": GREEN_BG, "neutral": AMBER_BG, "sad": BLUE_BG}.get(emotion, GRAY_BG)
    sc_color, sc_bg = _score_color(score)

    # ── Pet info card (3 columns: name+type | emotion | score) ────────────────
    name_s  = _ps("_pn_",  fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=DARK_TXT)
    type_s  = _ps("_pt_",  fontName="Helvetica",      fontSize=9,  leading=11, textColor=STEEL)
    lbl_s   = _ps("_pl_",  fontName="Helvetica-Bold", fontSize=7,  leading=9,  textColor=STEEL)
    emo_s   = _ps("_pe_",  fontName="Helvetica-Bold", fontSize=20, leading=22, textColor=emo_color)
    emo2_s  = _ps("_pe2_", fontName="Helvetica-Bold", fontSize=8,  leading=10, textColor=emo_color)
    sc_s    = _ps("_ps_",  fontName="Helvetica-Bold", fontSize=20, leading=22, textColor=sc_color)
    sc2_s   = _ps("_ps2_", fontName="Helvetica",      fontSize=8,  leading=10, textColor=STEEL)
    acc_s   = _ps("_pa_",  fontName="Helvetica-Bold", fontSize=8,  leading=10,
                  textColor=GREEN if accessory else STEEL)

    col1_w = CW * 0.38
    col2_w = CW * 0.31
    col3_w = CW * 0.31

    left_cell = Table([
        [Paragraph(pet_name, name_s)],
        [Paragraph(pet_type, type_s)],
        [Spacer(1, 6)],
        [Paragraph("ACCESSORY UNLOCK", lbl_s)],
        [Paragraph("Unlocked!" if accessory else "Earn 7-day streak", acc_s)],
    ], colWidths=[col1_w - 24])
    left_cell.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    mid_cell = Table([
        [Paragraph("CURRENT MOOD", lbl_s)],
        [Paragraph(emotion.title(), emo_s)],
        [Spacer(1, 4)],
        [Paragraph("MOOD THIS PERIOD", lbl_s)],
        [Paragraph(f"{len(events)} state change{'s' if len(events) != 1 else ''}", emo2_s)],
    ], colWidths=[col2_w - 24])
    mid_cell.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    right_cell = Table([
        [Paragraph("HEALTH SCORE", lbl_s)],
        [Paragraph(f"{int(round(score))}", sc_s)],
        [Paragraph("/ 100", sc2_s)],
    ], colWidths=[col3_w - 24])
    right_cell.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    info_row = Table(
        [[left_cell, mid_cell, right_cell]],
        colWidths=[col1_w, col2_w, col3_w],
    )
    info_row.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("BACKGROUND",    (0,0), (0,-1), GRAY_BG),
        ("BACKGROUND",    (1,0), (1,-1), emo_bg),
        ("BACKGROUND",    (2,0), (2,-1), sc_bg),
        ("LINEABOVE",     (0,0), (0,0), 3, NAVY),
        ("LINEABOVE",     (1,0), (1,0), 3, emo_color),
        ("LINEABOVE",     (2,0), (2,0), 3, sc_color),
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER_C),
    ]))
    items.append(info_row)

    # ── State change event log ────────────────────────────────────────────────
    if events:
        items.append(Spacer(1, 0.2*cm))
        ev_title_s = _ps("_etit_", fontName="Helvetica-Bold", fontSize=7.5,
                         leading=10, textColor=NAVY)
        items.append(Table([[Paragraph("MOOD CHANGE EVENTS THIS PERIOD", ev_title_s)]],
                           colWidths=[CW]))

        items.append(Spacer(1, 0.1*cm))
        for event in events[:8]:
            prev_emo = event.get("previous_emotion", "")
            new_emo  = event.get("new_emotion", "")
            ev_score = float(event.get("final_score") or 0)
            try:
                from datetime import datetime as _dt
                ts = _dt.fromisoformat(event["created_at"].replace("Z", "+00:00"))
                date_str = ts.strftime("%b %d, %Y")
            except Exception:
                date_str = str(event.get("created_at", ""))[:10]

            nc = {"happy": GREEN, "neutral": AMBER, "sad": RED}.get(new_emo, STEEL)
            pc = {"happy": GREEN, "neutral": AMBER, "sad": RED}.get(prev_emo, STEEL)

            prev_s = _ps(f"_ep{id(event)}_", fontName="Helvetica-Bold", fontSize=8,
                         leading=10, textColor=pc)
            new_s  = _ps(f"_en{id(event)}_", fontName="Helvetica-Bold", fontSize=9,
                         leading=11, textColor=nc)
            date_s = _ps(f"_ed{id(event)}_", fontName="Helvetica", fontSize=8,
                         leading=10, textColor=STEEL)
            sc2    = _ps(f"_es{id(event)}_", fontName="Helvetica-Bold", fontSize=8,
                         leading=10, textColor=nc)

            # Top reasons from breakdown
            reasons = []
            breakdown = (event.get("input_snapshot") or {}).get("breakdown") or []
            for b in breakdown[:2]:
                bname = (b.get("biomarker_type") or "").replace("_", " ").title()
                bsc   = b.get("score", 0)
                breason = b.get("reason", "")
                reasons.append(f"{bname}: {int(round(bsc))}/20 — {breason}")

            reason_s = _ps(f"_er{id(event)}_", fontName="Helvetica", fontSize=8,
                           leading=11, textColor=MED_TXT)

            ev_content = [[
                Paragraph(f"{prev_emo.title()} → {new_emo.title()}", new_s),
                Paragraph(f"Score: {int(round(ev_score))}/100", sc2),
                Paragraph(date_str, date_s),
            ]]
            if reasons:
                ev_content.append([
                    Table([[Paragraph(r, reason_s)] for r in reasons],
                          colWidths=[CW - 40]),
                    "", "",
                ])

            ev_row = Table(ev_content, colWidths=[CW * 0.4, CW * 0.2, CW * 0.4])
            ev_row.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
                ("LINEBEFORE",    (0,0), (-1,-1), 3, nc),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
                ("SPAN",          (0,1), (-1,1)) if len(ev_content) > 1 else ("SPAN", (0,0), (0,0)),
            ]))
            items.append(ev_row)
            items.append(Spacer(1, 4))

    # ── Pet mood timeline chart ────────────────────────────────────────────────
    if pet_chart:
        items.append(Spacer(1, 0.2*cm))
        chart_lbl_s = _ps("_pcl_", fontName="Helvetica-Bold", fontSize=7.5,
                          leading=10, textColor=STEEL)
        items.append(Paragraph("Mood Journey — Health Score Over Time", chart_lbl_s))
        items.append(Spacer(1, 4))
        img = Image(io.BytesIO(base64.b64decode(pet_chart)),
                    width=CW, height=CW * 0.32)
        chart_t = Table([[img]], colWidths=[CW])
        chart_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
            ("BOX",           (0,0), (-1,-1), 0.5, BORDER_C),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("RIGHTPADDING",  (0,0), (-1,-1), 4),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        items.append(chart_t)

    return items


# ── Biomarkers not logged ─────────────────────────────────────────────────────
def _build_not_logged(inactive_stats: list, st: dict) -> list:
    if not inactive_stats:
        return []
    items = [Spacer(1, 0.35*cm), _section("Biomarkers Not Logged", st), Spacer(1, 0.2*cm)]

    n = len(inactive_stats)
    chip_w = max((CW - 8 * (n - 1)) / n, 60)
    chips  = [Paragraph(s.get("label", ""), st["chip"]) for s in inactive_stats]

    chip_t = Table([chips], colWidths=[chip_w] * n)
    chip_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), BORDER_C),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("GRID",          (0,0), (-1,-1), 4, WHITE),
    ]))

    nm_s = _ps("_nm2_", fontName="Helvetica", fontSize=8.5, leading=12, textColor=STEEL)
    box_rows = [
        [Paragraph(
            "The following biomarkers had no recorded data during this period. "
            "Consistent tracking improves report accuracy.", nm_s)],
        [Spacer(1, 8)],
        [chip_t],
    ]
    box = Table(box_rows, colWidths=[CW - 24])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GRAY_BG),
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER_C),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (0,0),   10),
        ("TOPPADDING",    (0,1), (-1,-1), 0),
        ("BOTTOMPADDING", (0,-1),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-2), 0),
    ]))
    items.append(box)
    return items


# ── Footer (canvas callback) ──────────────────────────────────────────────────
def _make_footer(patient_name: str):
    rid = f"{patient_name.replace(' ', '_')}_{date.today().strftime('%Y%m%d')}"

    def _footer(canvas, doc):
        canvas.saveState()
        y = B_MAR - 0.6 * cm
        canvas.setStrokeColor(BORDER_C)
        canvas.setLineWidth(0.5)
        canvas.line(L_MAR, y + 10, PAGE_W - R_MAR, y + 10)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(STEEL)
        canvas.drawString(L_MAR, y,
            f"Generated by Pulse Health  •  getpulse.app  •  Report ID: {rid}")
        canvas.drawRightString(PAGE_W - R_MAR, y,
            f"Page {doc.page}  •  For informational purposes only. Not medical advice.")
        canvas.restoreState()

    return _footer


# ── Public API ────────────────────────────────────────────────────────────────
async def generate_pdf(
    patient_name: str,
    report_type: str,
    date_from: date,
    date_to: date,
    summary: Dict[str, Any],
    stats: List[Any],
    charts: Dict[str, str],
    score_chart: Optional[str],
    goals: Optional[List[Dict]] = None,
    recommendations: Optional[List[Dict]] = None,
    pet_info: Optional[Dict] = None,
    pet_chart: Optional[str] = None,
) -> bytes:
    st = _st()

    # Enrich stats with labels + charts
    enriched = []
    for s in stats:
        d = s.model_dump() if hasattr(s, "model_dump") else dict(s)
        d["label"] = BIOMARKER_LABELS.get(d["biomarker_type"],
                                           d["biomarker_type"].replace("_", " ").title())
        d["chart"] = charts.get(d["biomarker_type"])
        enriched.append(d)

    active_stats   = [s for s in enriched if s.get("status") != "no_data"]
    inactive_stats = [s for s in enriched if s.get("status") == "no_data"]

    goals           = goals or []
    completed_goals = [g for g in goals if g.get("status") == "completed"]
    missed_goals    = [g for g in goals if g.get("status") == "missed"]
    goal_rate       = summary.get("goals_completion_rate")

    avg_score      = summary.get("avg_health_score")
    best_score     = summary.get("best_score")
    worst_score    = summary.get("worst_score")
    score_trend    = summary.get("score_trend", "stable")
    total_readings = summary.get("total_readings", 0)
    generated_date = date.today().strftime("%B %d, %Y")
    date_from_str  = date_from.strftime("%B %d, %Y")
    date_to_str    = date_to.strftime("%B %d, %Y")

    story = []
    story.extend(_build_cover(patient_name, report_type, date_from_str,
                               date_to_str, generated_date, total_readings, st))

    if avg_score is not None:
        story.extend(_build_health_score(avg_score, best_score, worst_score,
                                          score_trend, total_readings, score_chart, st))
    else:
        story.extend(_build_no_score(total_readings, st))

    story.extend(_build_insights(active_stats, score_trend, st))
    story.extend(_build_biomarkers(active_stats, st))
    story.extend(_build_goals(goals, completed_goals, missed_goals, goal_rate, st))
    story.extend(_build_recommendations(recommendations or [], st))
    story.extend(_build_pet_section(pet_info or {}, pet_chart, st))
    story.extend(_build_not_logged(inactive_stats, st))

    buf = io.BytesIO()
    footer_fn = _make_footer(patient_name)
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=L_MAR, rightMargin=R_MAR,
        topMargin=T_MAR,  bottomMargin=B_MAR,
        title=f"Pulse Health Report – {patient_name}",
        author="Pulse Health",
    )
    doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)
    buf.seek(0)
    return buf.read()
