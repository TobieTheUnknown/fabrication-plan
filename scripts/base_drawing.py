"""
Helper de base pour générer des plans de fabrication normalisés (ISO 129-1) avec ezdxf.
Usage : adapter ce script pour chaque projet, puis l'exécuter.
"""

import subprocess, sys

def _ensure(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg,
                               "--break-system-packages", "-q"])

_ensure("ezdxf")
_ensure("matplotlib")

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment
import math
import os

# ─── Constantes de style ISO 129-1 ───────────────────────────────────────────
LAYER_VISIBLE   = "CONTOUR"        # trait continu fort  (objets visibles)
LAYER_HIDDEN    = "CACHE"          # trait interrompu fin (arêtes cachées)
LAYER_AXIS      = "AXE"            # trait mixte          (lignes d'axe)
LAYER_DIM       = "COTATION"       # cotation
LAYER_ANNOT     = "ANNOTATION"     # textes et repères
LAYER_FRAME     = "CARTOUCHE"      # cadre et cartouche

DIMSTYLE_NAME   = "ISO_WW"         # style de cotation personnalisé

def create_doc(title: str = "Plan de fabrication") -> tuple:
    """Crée un document DXF avec layers et dimstyle ISO."""
    doc = ezdxf.new(dxfversion="R2010", units=units.MM)
    msp = doc.modelspace()

    # Layers
    doc.layers.add(LAYER_VISIBLE, color=7,  lineweight=50)   # blanc, 0.5 mm
    doc.layers.add(LAYER_HIDDEN,  color=8,  lineweight=18)   # gris, 0.18 mm
    doc.layers.add(LAYER_AXIS,    color=1,  lineweight=18)   # rouge, 0.18 mm
    doc.layers.add(LAYER_DIM,     color=3,  lineweight=18)   # vert, 0.18 mm
    doc.layers.add(LAYER_ANNOT,   color=2,  lineweight=25)   # jaune, 0.25 mm
    doc.layers.add(LAYER_FRAME,   color=7,  lineweight=70)   # blanc, 0.7 mm

    # Dimstyle ISO
    dxf_dimstyle = doc.dimstyles.new(DIMSTYLE_NAME)
    dxf_dimstyle.dxf.dimtxt  = 3.5    # hauteur texte 3.5 mm
    dxf_dimstyle.dxf.dimasz  = 3.5    # taille flèche 3.5 mm
    dxf_dimstyle.dxf.dimexe  = 1.5    # dépassement ligne d'attache
    dxf_dimstyle.dxf.dimexo  = 1.5    # écart ligne d'attache / contour
    dxf_dimstyle.dxf.dimdli  = 8      # espacement entre lignes de cote parallèles
    dxf_dimstyle.dxf.dimtad  = 1      # texte au-dessus de la ligne de cote
    dxf_dimstyle.dxf.dimclrd = 3      # couleur cotation (vert)

    return doc, msp


def add_rectangle(msp, x: float, y: float, width: float, height: float,
                  layer: str = LAYER_VISIBLE):
    """Trace un rectangle (vue de face d'une pièce)."""
    pts = [(x, y), (x+width, y), (x+width, y+height), (x, y+height), (x, y)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def add_center_lines(msp, cx: float, cy: float, radius: float = 5):
    """Dessine des lignes d'axe croisées centrées sur (cx, cy)."""
    r = radius * 1.5
    msp.add_line((cx-r, cy), (cx+r, cy), dxfattribs={"layer": LAYER_AXIS, "linetype": "CENTER"})
    msp.add_line((cx, cy-r), (cx, cy+r), dxfattribs={"layer": LAYER_AXIS, "linetype": "CENTER"})


def add_hole(msp, cx: float, cy: float, diameter: float,
             depth: float = None, label: str = None):
    """
    Dessine un trou en vue de face :
    - cercle plein si traversant
    - cercle + annotation profondeur si borgne
    Annotation normalisée : Ø{diam} ↧{prof}
    """
    r = diameter / 2
    msp.add_circle((cx, cy), r, dxfattribs={"layer": LAYER_VISIBLE})
    add_center_lines(msp, cx, cy, r * 0.8)

    # Annotation
    note = f"Ø{diameter:.0f}"
    if depth:
        note += f" ↧{depth:.0f}"
    if label:
        note = f"{label} {note}"

    msp.add_text(
        note,
        dxfattribs={
            "layer":   LAYER_ANNOT,
            "height":  2.5,
            "insert":  (cx + r + 2, cy + 1),
        }
    )


def add_dim_horizontal(msp, x1: float, y: float, x2: float,
                        offset: float = -10, style: str = DIMSTYLE_NAME):
    """Cotation horizontale entre x1 et x2, ligne de cote à y+offset."""
    msp.add_linear_dim(
        base=(x1, y + offset),
        p1=(x1, y),
        p2=(x2, y),
        dimstyle=style,
        dxfattribs={"layer": LAYER_DIM},
    ).render()


def add_dim_vertical(msp, x: float, y1: float, y2: float,
                      offset: float = -10, style: str = DIMSTYLE_NAME):
    """Cotation verticale entre y1 et y2, ligne de cote à x+offset."""
    msp.add_linear_dim(
        base=(x + offset, y1),
        p1=(x, y1),
        p2=(x, y2),
        angle=90,
        dimstyle=style,
        dxfattribs={"layer": LAYER_DIM},
    ).render()


def add_title_block(msp, title: str, pieces: list[dict],
                    x: float = 0, y: float = -80):
    """
    Cartouche minimaliste avec titre et liste de débit.
    pieces = [{"id": "A", "nom": "...", "mat": "...", "L": 0, "l": 0, "ep": 0, "qte": 1}]
    """
    # Cadre
    w, h = 200, 60 + len(pieces) * 8
    msp.add_lwpolyline(
        [(x, y-h), (x+w, y-h), (x+w, y), (x, y), (x, y-h)],
        close=True,
        dxfattribs={"layer": LAYER_FRAME}
    )
    # Titre
    msp.add_text(title, dxfattribs={"layer": LAYER_ANNOT, "height": 5,
                                     "insert": (x+4, y-10)})
    msp.add_text("LISTE DE DÉBIT", dxfattribs={"layer": LAYER_ANNOT,
                                                "height": 3.5, "insert": (x+4, y-20)})
    header = "N°  Pièce                  Mat.         Ep.  L     l    Qté"
    msp.add_text(header, dxfattribs={"layer": LAYER_ANNOT, "height": 2.5,
                                      "insert": (x+4, y-28)})

    for i, p in enumerate(pieces):
        row = (f"{p['id']:<3} {p['nom']:<22} {p['mat']:<12} "
               f"{p['ep']:<4} {p['L']:<5} {p['l']:<4} {p['qte']}")
        msp.add_text(row, dxfattribs={"layer": LAYER_ANNOT, "height": 2.5,
                                       "insert": (x+4, y-36 - i*8)})


def save(doc, output_dir: str, base_name: str):
    """Sauvegarde en DXF et tente un export SVG via le backend matplotlib."""
    os.makedirs(output_dir, exist_ok=True)
    dxf_path = os.path.join(output_dir, f"{base_name}.dxf")
    doc.saveas(dxf_path)
    print(f"[OK] DXF : {dxf_path}")

    try:
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(16.54, 11.69))  # A3 paysage
        ax = fig.add_axes([0.05, 0.05, 0.90, 0.90])
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)

        svg_path = os.path.join(output_dir, f"{base_name}.svg")
        fig.savefig(svg_path, format="svg", dpi=150)
        plt.close(fig)
        print(f"[OK] SVG : {svg_path}")
    except Exception as e:
        print(f"[INFO] Export SVG non disponible ({e}) — utilise le DXF.")
