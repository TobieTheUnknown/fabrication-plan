"""
Générateur de dossier de fabrication PDF — format A4 portrait, style bureau d'études.
Usage : appeler build_pdf(data, output_path, dxf_image_path=None)

Auto-installe reportlab si absent.

data = {
    "title":      "Étagère murale 3 tablettes",
    "subtitle":   "Plan de fabrication",
    "material":   "Contreplaqué 18 mm",
    "dimensions": "800 × 900 × 250 mm",
    "assembly":   "Tourillons Ø8",
    "level":      "Intermédiaire",
    "date":       "2026-06-26",
    "debit": [
        {"id": "1", "nom": "Montant gauche", "mat": "CP 18", "ep": 18, "L": 900, "l": 250, "qte": 1, "notes": ""},
        ...
    ],
    "percage": [
        {
            "piece": "Montants (×2)",
            "ref_bords": "Bord bas = 0 / Bord avant = 0",
            "trous": [
                {"id": "M1a", "diam": 8, "prof": 15, "X": 60, "Y": 219, "usage": "Tourillon tablette basse"},
                ...
            ]
        },
        ...
    ],
    "etapes": [
        "Débit des montants — régler guide parallèle à 250 mm...",
        "Ponçage des chants — grain 80 puis 120...",
        ...
    ],
    "outillage": [
        "Scie circulaire + guide de parallélisme",
        "Perceuse + foret Ø8 + butée de profondeur",
        ...
    ],
    "consommables": [
        "16 tourillons Ø8 × 30 mm",
        "Colle PVA 250 ml",
        ...
    ],
    "conseils": [
        "Éclatement contreplaqué : face visible vers le bas lors de la coupe...",
        ...
    ],
}
"""

import subprocess, sys

def _ensure(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg,
                               "--break-system-packages", "-q"])

_ensure("reportlab")
_ensure("pillow", "PIL")

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image as RLImage
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

# ─── Palette de couleurs ──────────────────────────────────────────────────────
C_DARK    = colors.HexColor("#1a2332")   # bleu nuit (headers)
C_MID     = colors.HexColor("#2d4a6b")   # bleu moyen
C_ACCENT  = colors.HexColor("#e8a020")   # ambre (accents)
C_LIGHT   = colors.HexColor("#f5f7fa")   # gris très clair (fond alternance)
C_BORDER  = colors.HexColor("#c0ccd8")   # gris-bleu (contours tableau)
C_WHITE   = colors.white
C_TEXT    = colors.HexColor("#1a2332")

W, H = A4  # 210 × 297 mm


def _styles():
    """Retourne un dict de styles nommés."""
    base = getSampleStyleSheet()
    s = {}
    s["h1"] = ParagraphStyle("h1", fontSize=22, textColor=C_WHITE,
                              fontName="Helvetica-Bold", leading=28, alignment=TA_LEFT)
    s["h2"] = ParagraphStyle("h2", fontSize=13, textColor=C_WHITE,
                              fontName="Helvetica-Bold", leading=18, alignment=TA_LEFT)
    s["h3"] = ParagraphStyle("h3", fontSize=10, textColor=C_DARK,
                              fontName="Helvetica-Bold", leading=14, alignment=TA_LEFT,
                              spaceAfter=4)
    s["body"] = ParagraphStyle("body", fontSize=9, textColor=C_TEXT,
                                fontName="Helvetica", leading=13, alignment=TA_LEFT)
    s["small"] = ParagraphStyle("small", fontSize=7.5, textColor=colors.HexColor("#556677"),
                                 fontName="Helvetica", leading=11)
    s["step"] = ParagraphStyle("step", fontSize=9, textColor=C_TEXT,
                                fontName="Helvetica", leading=13, leftIndent=10,
                                spaceAfter=5)
    s["tip"] = ParagraphStyle("tip", fontSize=8.5, textColor=C_MID,
                               fontName="Helvetica-Oblique", leading=12,
                               leftIndent=12, spaceAfter=4)
    s["check"] = ParagraphStyle("check", fontSize=9, textColor=C_TEXT,
                                 fontName="Helvetica", leading=13, leftIndent=8,
                                 spaceAfter=3)
    s["meta"] = ParagraphStyle("meta", fontSize=9, textColor=C_WHITE,
                                fontName="Helvetica", leading=14)
    s["meta_label"] = ParagraphStyle("ml", fontSize=7.5,
                                     textColor=colors.HexColor("#a8c4d8"),
                                     fontName="Helvetica", leading=10)
    return s


def _section_header(title: str, styles: dict):
    """Retourne [Drawing bandeau coloré + Paragraph titre]."""
    d = Drawing(W - 40*mm, 9*mm)
    d.add(Rect(0, 0, W - 40*mm, 9*mm, fillColor=C_DARK, strokeColor=None))
    d.add(Rect(0, 0, 3*mm, 9*mm, fillColor=C_ACCENT, strokeColor=None))
    d.add(String(5*mm, 2.5*mm, title.upper(), fontSize=10,
                 fontName="Helvetica-Bold", fillColor=colors.white))
    return [d, Spacer(1, 3*mm)]


def _table_style_default(col_widths, header_bg=C_MID):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING",    (0, 0), (-1, 0), 5),
        ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
    ])


# ─── Page de garde ────────────────────────────────────────────────────────────
def _cover_page(data: dict, styles: dict) -> list:
    story = []

    # Bandeau haut pleine largeur
    d = Drawing(W - 40*mm, 55*mm)
    d.add(Rect(0, 0, W - 40*mm, 55*mm, fillColor=C_DARK, strokeColor=None))
    d.add(Rect(0, 0, W - 40*mm, 4*mm, fillColor=C_ACCENT, strokeColor=None))
    d.add(String(8*mm, 35*mm, "DOSSIER DE FABRICATION",
                 fontSize=10, fontName="Helvetica", fillColor=colors.HexColor("#a8c4d8")))
    # Titre principal (tronqué si trop long)
    title = data.get("title", "Plan de fabrication")
    d.add(String(8*mm, 18*mm, title,
                 fontSize=20, fontName="Helvetica-Bold", fillColor=C_WHITE))
    story.append(d)
    story.append(Spacer(1, 8*mm))

    # Métadonnées en grille 2 colonnes
    meta_items = [
        ("MATÉRIAU",   data.get("material",   "—")),
        ("DIMENSIONS", data.get("dimensions", "—")),
        ("ASSEMBLAGE", data.get("assembly",   "—")),
        ("NIVEAU",     data.get("level",      "—")),
        ("DATE",       data.get("date",       "—")),
        ("PIÈCES",     str(len(data.get("debit", [])))),
    ]
    meta_data = []
    for i in range(0, len(meta_items), 2):
        row = []
        for label, value in meta_items[i:i+2]:
            cell = [
                Paragraph(label, styles["meta_label"]),
                Paragraph(value, ParagraphStyle("mv", fontSize=11, textColor=C_DARK,
                                                 fontName="Helvetica-Bold", leading=14)),
            ]
            row.append(cell)
        if len(row) == 1:
            row.append("")
        meta_data.append(row)

    meta_table = Table(meta_data, colWidths=[(W-40*mm)/2]*2)
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 1, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6*mm))

    # Ligne de séparation accent
    story.append(HRFlowable(width="100%", thickness=3, color=C_ACCENT, spaceAfter=5*mm))

    # Résumé du projet si fourni
    if data.get("summary"):
        story.append(Paragraph(data["summary"], styles["body"]))
        story.append(Spacer(1, 5*mm))

    story.append(PageBreak())
    return story


# ─── Dessin technique ─────────────────────────────────────────────────────────
def _drawing_page(dxf_image_path: str, styles: dict) -> list:
    if not dxf_image_path or not os.path.exists(dxf_image_path):
        return []
    story = []
    story += _section_header("Dessin technique", styles)

    max_w = W - 40*mm
    max_h = H - 80*mm
    img = RLImage(dxf_image_path, width=max_w, height=max_h, kind="proportional")
    story.append(img)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Toutes les cotes sont exprimées en millimètres. "
                            "Fichier DXF fourni séparément (LibreCAD / FreeCAD / Inkscape).",
                            styles["small"]))
    story.append(PageBreak())
    return story


# ─── Liste de débit ───────────────────────────────────────────────────────────
def _debit_page(data: dict, styles: dict) -> list:
    story = []
    story += _section_header("Liste de débit", styles)

    rows = [["N°", "Nom de la pièce", "Matière", "Ép.\n(mm)", "L\n(mm)", "l\n(mm)", "Qté", "Notes"]]
    for p in data.get("debit", []):
        rows.append([
            str(p.get("id", "")),
            p.get("nom", ""),
            p.get("mat", ""),
            str(p.get("ep", "")),
            str(p.get("L", "")),
            str(p.get("l", "")),
            str(p.get("qte", "")),
            p.get("notes", ""),
        ])

    col_w = [8*mm, 52*mm, 32*mm, 13*mm, 16*mm, 16*mm, 10*mm, None]
    col_w[-1] = (W - 40*mm) - sum(c for c in col_w if c)
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_table_style_default(col_w))
    story.append(t)
    story.append(Spacer(1, 5*mm))

    # Résumé matière si disponible
    if data.get("achat_matiere"):
        story.append(Paragraph(f"<b>Achat matière :</b> {data['achat_matiere']}", styles["body"]))

    story.append(PageBreak())
    return story


# ─── Plans de perçage ─────────────────────────────────────────────────────────
def _percage_pages(data: dict, styles: dict) -> list:
    story = []
    for bloc in data.get("percage", []):
        story += _section_header(f"Plan de perçage — {bloc['piece']}", styles)

        if bloc.get("ref_bords"):
            story.append(Paragraph(f"<b>Référence :</b> {bloc['ref_bords']}", styles["body"]))
            story.append(Spacer(1, 3*mm))

        rows = [["Trou", "Ø (mm)", "Prof. (mm)", "X (mm)", "Y (mm)", "Usage"]]
        for t in bloc.get("trous", []):
            rows.append([
                t.get("id", ""),
                str(t.get("diam", "")),
                str(t.get("prof", "")) if t.get("prof") else "traversant",
                str(t.get("X", "")),
                str(t.get("Y", "")),
                t.get("usage", ""),
            ])

        col_w = [16*mm, 18*mm, 22*mm, 18*mm, 18*mm, None]
        col_w[-1] = (W - 40*mm) - sum(c for c in col_w if c)
        tbl = Table(rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(_table_style_default(col_w))
        story.append(tbl)
        story.append(Spacer(1, 4*mm))

        # Image de perçage si disponible
        if bloc.get("image_path") and os.path.exists(bloc["image_path"]):
            img = RLImage(bloc["image_path"], width=W-40*mm, height=80*mm, kind="proportional")
            story.append(img)
            story.append(Spacer(1, 3*mm))

        story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
        story.append(Spacer(1, 4*mm))

    story.append(PageBreak())
    return story


# ─── Étapes de fabrication ────────────────────────────────────────────────────
def _etapes_page(data: dict, styles: dict) -> list:
    story = []
    story += _section_header("Étapes de fabrication", styles)

    for i, etape in enumerate(data.get("etapes", []), 1):
        # Séparer titre (avant " — ") du corps si présent
        if " — " in etape:
            titre, corps = etape.split(" — ", 1)
            bloc = [
                Paragraph(f"<b>{i}. {titre}</b>", styles["h3"]),
                Paragraph(corps, styles["step"]),
            ]
        else:
            bloc = [Paragraph(f"<b>{i}.</b> {etape}", styles["step"])]

        story.append(KeepTogether(bloc))

    story.append(PageBreak())
    return story


# ─── Outillage & consommables ─────────────────────────────────────────────────
def _outillage_page(data: dict, styles: dict) -> list:
    story = []
    story += _section_header("Outillage & consommables", styles)

    # Deux colonnes côte à côte
    left_items  = data.get("outillage", [])
    right_items = data.get("consommables", [])

    def checklist(items):
        return [Paragraph(f"☐  {item}", styles["check"]) for item in items]

    left_col  = [Paragraph("<b>Outillage</b>", styles["h3"]), Spacer(1, 2*mm)] + checklist(left_items)
    right_col = [Paragraph("<b>Consommables</b>", styles["h3"]), Spacer(1, 2*mm)] + checklist(right_items)

    # Padding pour aligner les colonnes
    max_len = max(len(left_col), len(right_col))
    while len(left_col) < max_len:  left_col.append(Spacer(1, 1))
    while len(right_col) < max_len: right_col.append(Spacer(1, 1))

    col_w = (W - 40*mm) / 2
    rows = [[left_col, right_col]]
    t = Table(rows, colWidths=[col_w, col_w])
    t.setStyle(TableStyle([
        ("VALIGN",  (0, 0), (-1, -1), "TOP"),
        ("BOX",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",(0, 0), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, 0), (0, 0), C_LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), C_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    # Conseils
    if data.get("conseils"):
        story.append(Spacer(1, 6*mm))
        story += _section_header("Conseils & pièges à éviter", styles)
        for conseil in data["conseils"]:
            story.append(Paragraph(f"⚠  {conseil}", styles["tip"]))
            story.append(Spacer(1, 2*mm))

    return story


# ─── Numérotation des pages ───────────────────────────────────────────────────
def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#889aaa"))
    canvas.drawRightString(W - 20*mm, 12*mm,
                           f"Page {doc.page}  —  Dossier de fabrication")
    # Trait de pied de page
    canvas.setStrokeColor(C_ACCENT)
    canvas.setLineWidth(1.5)
    canvas.line(20*mm, 16*mm, W - 20*mm, 16*mm)
    canvas.restoreState()


# ─── Entrée publique ──────────────────────────────────────────────────────────
def build_pdf(data: dict, output_path: str, dxf_image_path: str = None):
    """
    Génère le dossier de fabrication PDF.

    Args:
        data:            dict décrivant le projet (voir docstring en tête de fichier)
        output_path:     chemin de sortie du PDF (ex: ~/Plans/etagere/dossier.pdf)
        dxf_image_path:  chemin vers une image PNG/SVG du dessin technique (optionnel)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=20*mm, bottomMargin=20*mm,
        leftMargin=20*mm, rightMargin=20*mm,
        title=data.get("title", "Plan de fabrication"),
        author="Claude Code — skill fabrication-plan",
    )

    styles = _styles()
    story = []
    story += _cover_page(data, styles)
    story += _drawing_page(dxf_image_path, styles)
    story += _debit_page(data, styles)
    story += _percage_pages(data, styles)
    story += _etapes_page(data, styles)
    story += _outillage_page(data, styles)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    print(f"[OK] PDF : {output_path}")
    return output_path
