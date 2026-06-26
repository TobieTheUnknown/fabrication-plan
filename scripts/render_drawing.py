"""
Générateur de dessin technique normalisé ISO 129-1 — matplotlib pur.
Fond blanc A3/A4, cadre, cotations avec flèches + lignes d'attache,
lignes d'axe tiret-point, cartouche bas-droit, notes bas-gauche.

Usage:
    from render_drawing import TechDrawing, MM
    d = TechDrawing(scale=5)
    d.part(ox, oy, 0, 0, 250, 900)            # contour pièce
    d.hole(ox, oy, 125, 450, diam=8, depth=15)
    d.dim_h(ox, oy, 0, 250, y_ref=0, ext=-12) # cotation horiz sous la pièce
    d.dim_v(ox, oy, 250, 0, 900, ext=12)      # cotation vert à droite
    d.title_block(...)
    d.save('/tmp/plan.png')
"""

import subprocess, sys
for _pkg in ['matplotlib']:
    try: __import__(_pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', _pkg,
                               '--break-system-packages', '-q'])

import os, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle, Arc
from matplotlib.lines import Line2D
import numpy as np

# ─── Épaisseurs de trait ISO (points matplotlib) ─────────────────────────────
LW_BORDER  = 2.0   # cadre feuille extérieur
LW_FRAME   = 1.2   # cadre intérieur zone de dessin
LW_VISIBLE = 0.9   # trait fort : contours visibles
LW_HIDDEN  = 0.45  # trait interrompu : arêtes cachées
LW_DIM     = 0.5   # trait fin : lignes de cote et d'attache
LW_CENTER  = 0.4   # trait mixte : lignes d'axe
LW_TITLE   = 0.9   # cartouche

# ─── Couleurs ─────────────────────────────────────────────────────────────────
C_BG      = '#ffffff'   # fond blanc
C_PART    = '#000000'   # trait fort noir
C_DIM     = '#222222'   # cotation (quasi-noir)
C_CENTER  = '#cc2200'   # axe (rouge)
C_TITLE_H = '#1a2e4a'   # fond bandeau cartouche
C_TITLE_T = '#ffffff'   # texte bandeau cartouche
C_NOTE    = '#333333'   # texte notes

# ─── Formats papier (mm) ─────────────────────────────────────────────────────
SHEETS = {
    'A3L': (420, 297),
    'A3P': (297, 420),
    'A4L': (297, 210),
    'A4P': (210, 297),
}

# ─── Marges intérieures ───────────────────────────────────────────────────────
ML, MR, MT, MB = 20, 10, 10, 10   # Left Right Top Bottom


class TechDrawing:
    def __init__(self, scale: int = 5, sheet: str = 'A3L', dpi: int = 200):
        """
        scale  : dénominateur (5 → 1:5, 10 → 1:10)
        sheet  : 'A3L', 'A3P', 'A4L', 'A4P'
        dpi    : résolution PNG de sortie
        """
        self.sc  = scale
        self.dpi = dpi
        self.SW, self.SH = SHEETS.get(sheet, (420, 297))

        self.fig = plt.figure(figsize=(self.SW / 25.4, self.SH / 25.4),
                              facecolor=C_BG, dpi=dpi)
        self.ax  = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, self.SW)
        self.ax.set_ylim(0, self.SH)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.ax.patch.set_facecolor(C_BG)

        self._draw_frame()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _p(self, mx, my, ox, oy):
        """Coords modèle → feuille."""
        return ox + mx / self.sc, oy + my / self.sc

    def _draw_frame(self):
        W, H = self.SW, self.SH
        # Fond
        self.ax.add_patch(Rectangle((0,0), W, H, fc=C_BG, ec='none', zorder=0))
        # Bord ext
        self.ax.add_patch(Rectangle((0,0), W, H, fc='none', ec=C_PART,
                                    lw=LW_BORDER, zorder=1))
        # Cadre intérieur
        self.ax.add_patch(Rectangle((ML, MB), W-ML-MR, H-MT-MB,
                                    fc='none', ec=C_PART, lw=LW_FRAME, zorder=1))

    # ── Primitives géométriques ───────────────────────────────────────────────

    def part(self, ox, oy, x, y, w, h):
        """Rectangle contour de pièce (trait fort)."""
        sx, sy = self._p(x, y, ox, oy)
        self.ax.add_patch(Rectangle((sx, sy), w/self.sc, h/self.sc,
                                    fc='#f8f8f8', ec=C_PART, lw=LW_VISIBLE, zorder=5))

    def hidden(self, ox, oy, x, y, w, h):
        """Rectangle en trait interrompu (arête cachée)."""
        sx, sy = self._p(x, y, ox, oy)
        self.ax.add_patch(Rectangle((sx, sy), w/self.sc, h/self.sc,
                                    fc='none', ec=C_PART, lw=LW_HIDDEN,
                                    ls=(0, (4, 2)), zorder=4))

    def line(self, ox, oy, x1, y1, x2, y2, lw=LW_VISIBLE, color=C_PART, ls='solid'):
        sx1, sy1 = self._p(x1, y1, ox, oy)
        sx2, sy2 = self._p(x2, y2, ox, oy)
        self.ax.plot([sx1, sx2], [sy1, sy2], color=color, lw=lw, ls=ls, zorder=5)

    def hole(self, ox, oy, cx, cy, diam, depth=None, label='', real_diam=None):
        """Trou en vue de face : cercle + axe tiret-point + annotation Ø↧.
        real_diam : dimension réelle à afficher (utile pour vues agrandies).
        """
        scx, scy = self._p(cx, cy, ox, oy)
        r = (diam / 2) / self.sc

        # Cercle
        self.ax.add_patch(Circle((scx, scy), r, fc='#f0f0f0', ec=C_PART,
                                  lw=LW_VISIBLE, zorder=6))

        # Lignes d'axe (tiret-point rouge)
        ext = max(r * 2.5, 3.5)
        _dash = (0, (5, 1.5, 1.5, 1.5))
        self.ax.plot([scx-ext, scx+ext], [scy, scy],
                     color=C_CENTER, lw=LW_CENTER, ls=_dash, zorder=7)
        self.ax.plot([scx, scx], [scy-ext, scy+ext],
                     color=C_CENTER, lw=LW_CENTER, ls=_dash, zorder=7)

        # Annotation (utilise real_diam si fourni)
        d_ann = real_diam if real_diam is not None else diam
        ann = f'Ø{int(d_ann)}'
        if depth is not None:
            ann += f' ↧{int(depth)}'
        if label:
            ann = f'{label}  {ann}'
        self.ax.text(scx + r + 1.2, scy + 0.5, ann,
                     fontsize=9, color=C_PART, va='bottom',
                     fontfamily='monospace', zorder=8)

    def axis_h(self, ox, oy, x1, x2, y, over=5):
        """Ligne d'axe horizontale (tiret-point rouge)."""
        sx1, sy = self._p(x1, y, ox, oy)
        sx2, _  = self._p(x2, y, ox, oy)
        so = over / self.sc
        self.ax.plot([sx1-so, sx2+so], [sy, sy],
                     color=C_CENTER, lw=LW_CENTER,
                     ls=(0, (8, 2, 2, 2)), zorder=4)

    def axis_v(self, ox, oy, x, y1, y2, over=5):
        """Ligne d'axe verticale (tiret-point rouge)."""
        sx, sy1 = self._p(x, y1, ox, oy)
        _,  sy2 = self._p(x, y2, ox, oy)
        so = over / self.sc
        self.ax.plot([sx, sx], [sy1-so, sy2+so],
                     color=C_CENTER, lw=LW_CENTER,
                     ls=(0, (8, 2, 2, 2)), zorder=4)

    # ── Cotations ─────────────────────────────────────────────────────────────

    def _arrow_line(self, x1, y1, x2, y2):
        """Ligne de cote avec flèches double sens (coordonnées feuille)."""
        # Ligne fine
        self.ax.plot([x1, x2], [y1, y2], color=C_DIM, lw=LW_DIM, zorder=3)
        # Flèches aux extrémités
        dx, dy = x2-x1, y2-y1
        length = math.hypot(dx, dy)
        if length < 0.01:
            return
        ux, uy = dx/length, dy/length   # vecteur unitaire
        aw = 1.6   # demi-largeur flèche (mm feuille)
        ah = 2.8   # longueur flèche (mm feuille)

        def _arrowhead(tip_x, tip_y, sign):
            bx = tip_x - sign * ux * ah
            by = tip_y - sign * uy * ah
            px = -sign * uy * aw
            py =  sign * ux * aw
            xs = [tip_x, bx+px, bx-px, tip_x]
            ys = [tip_y, by+py, by-py, tip_y]
            self.ax.fill(xs, ys, color=C_DIM, zorder=3)

        _arrowhead(x1, y1, +1)
        _arrowhead(x2, y2, -1)

    def dim_h(self, ox, oy, x1, x2, y_ref, ext=-12, label=None):
        """
        Cotation horizontale.
        x1, x2  : X modèle des points mesurés
        y_ref   : Y modèle du bord de référence (pied des lignes d'attache)
        ext     : décalage en mm FEUILLE de la ligne de cote depuis y_ref
                  (négatif = en dessous, positif = au-dessus)
        """
        sx1, sy_ref = self._p(x1, y_ref, ox, oy)
        sx2, _      = self._p(x2, y_ref, ox, oy)
        dim_y = sy_ref + ext

        GAP  = 0.8   # mm feuille entre bord pièce et début ligne d'attache
        OVER = 1.5   # mm feuille dépassement au-delà de la ligne de cote

        if ext < 0:
            ya, yb = sy_ref - GAP, dim_y + OVER
        else:
            ya, yb = sy_ref + GAP, dim_y - OVER

        # Lignes d'attache
        for sx in (sx1, sx2):
            self.ax.plot([sx, sx], [ya, yb], color=C_DIM, lw=LW_DIM, zorder=3)

        # Ligne de cote + flèches
        self._arrow_line(sx1, dim_y, sx2, dim_y)

        # Valeur (au-dessus de la ligne de cote, alignée horizontalement)
        val  = label if label else str(abs(int(round(x2 - x1))))
        midx = (sx1 + sx2) / 2
        self.ax.text(midx, dim_y + 1.0, val,
                     ha='center', va='bottom', fontsize=11,
                     color=C_DIM, fontfamily='DejaVu Sans', zorder=8)

    def dim_v(self, ox, oy, x_ref, y1, y2, ext=-12, label=None):
        """
        Cotation verticale.
        x_ref    : X modèle du bord de référence (côté des lignes d'attache)
        y1, y2   : Y modèle des points mesurés
        ext      : décalage en mm FEUILLE (négatif = à gauche, positif = à droite)
        """
        sx_ref, sy1 = self._p(x_ref, y1, ox, oy)
        _,      sy2 = self._p(x_ref, y2, ox, oy)
        dim_x = sx_ref + ext

        GAP  = 0.8
        OVER = 1.5

        if ext < 0:
            xa, xb = sx_ref - GAP, dim_x + OVER
        else:
            xa, xb = sx_ref + GAP, dim_x - OVER

        for sy in (sy1, sy2):
            self.ax.plot([xa, xb], [sy, sy], color=C_DIM, lw=LW_DIM, zorder=3)

        self._arrow_line(dim_x, sy1, dim_x, sy2)

        val  = label if label else str(abs(int(round(y2 - y1))))
        midy = (sy1 + sy2) / 2
        # texte perpendiculaire à la ligne de cote (rotation 90°)
        self.ax.text(dim_x - 1.0 if ext < 0 else dim_x + 1.0, midy, val,
                     ha='right' if ext < 0 else 'left',
                     va='center', fontsize=11, rotation=90,
                     color=C_DIM, fontfamily='DejaVu Sans', zorder=8)

    def leader(self, ox, oy, x_tip, y_tip, x_text, y_text, text, fontsize=5.5):
        """Ligne de repère avec flèche et texte."""
        stx, sty = self._p(x_tip,  y_tip,  ox, oy)
        sxx, sxy = self._p(x_text, y_text, ox, oy)
        self.ax.annotate(
            text,
            xy=(stx, sty), xytext=(sxx, sxy),
            arrowprops=dict(arrowstyle='->', color=C_DIM, lw=LW_DIM),
            fontsize=fontsize, color=C_PART,
            fontfamily='DejaVu Sans', zorder=8
        )

    # ── Textes ────────────────────────────────────────────────────────────────

    def view_label(self, sx, sy, text):
        """Titre de vue — coordonnées FEUILLE directes."""
        self.ax.text(sx, sy, text, ha='left', va='top',
                     fontsize=11, fontweight='bold', color=C_PART,
                     fontfamily='DejaVu Sans', zorder=9)

    def view_sub(self, sx, sy, text):
        """Sous-titre vue (matière, dims) — coordonnées FEUILLE."""
        self.ax.text(sx, sy, text, ha='left', va='top',
                     fontsize=8.5, color='#555555',
                     fontfamily='DejaVu Sans', zorder=9)

    def text(self, sx, sy, txt, fontsize=5.5, color=C_PART,
             ha='left', va='top', bold=False, italic=False):
        """Texte libre en coordonnées feuille."""
        fw = 'bold'   if bold   else 'normal'
        fs = 'italic' if italic else 'normal'
        self.ax.text(sx, sy, txt, ha=ha, va=va, fontsize=fontsize,
                     fontweight=fw, fontstyle=fs, color=color,
                     fontfamily='DejaVu Sans', zorder=9)

    # ── Cartouche ─────────────────────────────────────────────────────────────

    def title_block(self, title='PLAN DE FABRICATION', subtitle='',
                    material='', scale_str='', date='',
                    projection='1er angle', parts=None):
        """Cartouche ISO en bas à droite."""
        TBW, TBH = 160, 60
        TBX = self.SW - MR - TBW
        TBY = MB

        # Fond blanc + cadre
        self.ax.add_patch(Rectangle((TBX, TBY), TBW, TBH,
                                    fc='white', ec=C_PART, lw=LW_TITLE, zorder=10))

        # ── Bandeau titre ──
        BH = 16
        self.ax.add_patch(Rectangle((TBX, TBY+TBH-BH), TBW, BH,
                                    fc=C_TITLE_H, ec='none', zorder=10))
        self.ax.text(TBX+4, TBY+TBH-BH/2, title,
                     fontsize=12, fontweight='bold', color=C_TITLE_T,
                     va='center', fontfamily='DejaVu Sans', zorder=11)
        if subtitle:
            self.ax.text(TBX+TBW-4, TBY+TBH-BH/2, subtitle,
                         fontsize=8, color='#99bbdd',
                         ha='right', va='center',
                         fontfamily='DejaVu Sans', zorder=11)

        # ── Ligne séparation meta ──
        MH = 14
        meta_top = TBY + TBH - BH
        meta_bot = meta_top - MH
        self.ax.plot([TBX, TBX+TBW], [meta_bot]*2,
                     color=C_PART, lw=0.6, zorder=10)

        # 4 colonnes : Matière | Échelle | Projection | Date
        cols = [
            ('MATIÈRE',       material),
            ('ÉCHELLE',        scale_str or f'1:{self.sc}'),
            ('PROJECTION',     projection),
            ('DATE',           date),
        ]
        cw = TBW / len(cols)
        for i, (lbl, val) in enumerate(cols):
            cx = TBX + i * cw
            if i:
                self.ax.plot([cx]*2, [meta_bot, meta_top],
                             color=C_PART, lw=0.4, zorder=10)
            my = (meta_bot + meta_top) / 2
            self.ax.text(cx + cw/2, my + 2.5, lbl,
                         fontsize=6, color='#888888',
                         ha='center', va='center',
                         fontfamily='DejaVu Sans', zorder=11)
            self.ax.text(cx + cw/2, my - 1.5, val,
                         fontsize=11, fontweight='bold', color=C_PART,
                         ha='center', va='center',
                         fontfamily='DejaVu Sans', zorder=11)

        # ── Liste de débit ──
        list_y = meta_bot
        self.ax.plot([TBX, TBX+TBW], [list_y]*2,
                     color=C_PART, lw=0.6, zorder=10)

        if parts:
            hdr = f"{'N°':<3} {'Désignation':<20} {'Mat.':<8}{'Ép':>4}{'L':>6}{'l':>5}{'Q':>3}"
            self.ax.text(TBX+3, list_y - 2, hdr,
                         fontsize=6, color='#555555',
                         va='top', fontfamily='DejaVu Sans Mono', zorder=11)
            self.ax.plot([TBX, TBX+TBW], [list_y-6]*2,
                         color=C_PART, lw=0.3, zorder=10)

            row_h = 4.0
            for i, p in enumerate(parts[:6]):
                ry = list_y - 7 - i * row_h
                if ry < TBY + 2:
                    break
                line = (f"{str(p.get('id','')):<3} {p.get('nom',''):<20} "
                        f"{p.get('mat',''):<8}{str(p.get('ep',''))!s:>4}"
                        f"{str(p.get('L',''))!s:>6}{str(p.get('l',''))!s:>5}"
                        f"{str(p.get('qte',''))!s:>3}")
                self.ax.text(TBX+3, ry, line,
                             fontsize=6, color=C_PART,
                             va='top', fontfamily='DejaVu Sans Mono', zorder=11)

        # Signature
        self.ax.text(TBX+TBW-2, TBY+1.5,
                     'Claude Code — skill fabrication-plan',
                     fontsize=4, color='#aaaaaa', ha='right', va='bottom',
                     fontfamily='DejaVu Sans', zorder=11)

    def notes(self, lines):
        """
        Bloc de notes générales en bas à gauche.
        lines : liste de str — note 1 en haut, dernière en bas.
        """
        nx = ML + 2
        row_h = 5.5
        n = len(lines)
        title_y = MB + 2 + n * row_h + 3
        self.ax.text(nx, title_y, 'NOTES GÉNÉRALES :',
                     fontsize=8, fontweight='bold', color=C_NOTE,
                     va='bottom', fontfamily='DejaVu Sans', zorder=9)
        for i, line in enumerate(lines):
            ly = title_y - 5 - i * row_h
            self.ax.text(nx, ly, f'  {i+1}. {line}',
                         fontsize=7, color=C_NOTE,
                         va='bottom', fontfamily='DejaVu Sans', zorder=9)

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.fig.savefig(path, dpi=self.dpi, format='png',
                         facecolor=C_BG, bbox_inches=None, pad_inches=0)
        plt.close(self.fig)
        print(f'[OK] PNG : {path}')
        return path
