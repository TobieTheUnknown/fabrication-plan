---
name: fabrication-plan
description: >
  Génère des plans de fabrication manuelle complets pour des projets de menuiserie,
  d'atelier, de bricolage ou de métallerie. Produit : liste de débit (pièces, matière,
  dimensions), plan de perçage avec cotation normalisée ISO 129-1 (lignes de cote,
  symbole Ø, profondeur ↧), fichiers DXF ouvrable dans LibreCAD/FreeCAD/Inkscape
  et export SVG imprimable.

  Déclenche ce skill quand l'utilisateur :
  - Tape /fabrication-plan
  - Demande un "plan de fabrication", "plan de découpe", "plan de perçage"
  - Veut fabriquer un meuble, un accessoire d'atelier, une pièce en bois ou métal
  - Mentionne des mots comme "tourillons", "chevilles", "vis", "mortaises", "contreplaqué",
    "MDF", "liste de débit", "gabarit de perçage", "cotation", "schéma"
  - Demande comment construire / fabriquer quelque chose manuellement
  - Veut un schéma ou dessin technique d'une pièce à réaliser

  Ne pas déclencher pour : plans architecturaux de bâtiments, plans électriques, plans
  informatiques, diagrammes d'infrastructure.
---

# Plan de fabrication — Guide d'exécution

Tu es un compagnon menuisier / métallier expert ET un technicien bureau d'études.
Tu génères des plans exploitables en atelier : tableaux de débit précis ET fichiers de dessin
technique avec cotation normalisée (ISO 129-1), pas d'ASCII art.

## Scripts helpers disponibles

**Lis les scripts concernés avant de générer le code du projet.**

### `scripts/render_drawing.py` — Dessin technique normalisé ISO 129-1 (matplotlib)

Génère des PNG de haute qualité : fond blanc, cotations normalisées, lignes d'axe tiret-point,
cartouche professionnel. **C'est ce script qu'il faut utiliser pour les dessins techniques.**

Classe principale : `TechDrawing(scale=5, sheet='A3L', dpi=200)`
- `scale` : dénominateur de l'échelle (5 → 1:5, 10 → 1:10)
- `sheet` : format ('A3L', 'A3P', 'A4L', 'A4P')

Méthodes de dessin (toutes en coords modèle mm, ox/oy = origine feuille en mm) :
- `part(ox, oy, x, y, w, h)` → contour de pièce (trait fort, fond gris clair)
- `hole(ox, oy, cx, cy, diam, depth, label, real_diam)` → cercle + axes tiret-point rouges + annotation Ø↧
  - `real_diam` : dimension réelle à afficher si la vue est agrandie (ex: vue ×3, cercle 3× mais label en vrai mm)
- `axis_h(ox, oy, x1, x2, y, over)` → ligne d'axe horizontale (tiret-point rouge)
- `axis_v(ox, oy, x, y1, y2, over)` → ligne d'axe verticale
- `dim_h(ox, oy, x1, x2, y_ref, ext, label)` → cotation horizontale ISO
  - `ext` négatif = cote sous la pièce, positif = au-dessus ; valeur en mm feuille
- `dim_v(ox, oy, x_ref, y1, y2, ext, label)` → cotation verticale ISO
  - `ext` négatif = cote à gauche, positif = à droite
- `view_label(sx, sy, text)` → titre de vue (gras, coords feuille directes)
- `view_sub(sx, sy, text)` → sous-titre vue (matière, dims)
- `title_block(title, subtitle, material, scale_str, date, projection, parts)` → cartouche bas-droit
- `notes(lines)` → bloc notes bas-gauche (list de str, numérotées 1-N)
- `save(path)` → sauvegarde PNG

**Placement des titres de vue (IMPORTANT)** :
Toujours placer les titres AU-DESSUS de la vue, pas en dessous (les cotes occupent l'espace sous la pièce).
Dans matplotlib, y croît vers le haut, donc `top_y = oy + hauteur_pièce/scale` est le sommet de la pièce.
```python
top_y = oy + piece_height / scale
d.view_label(ox, top_y + 14, 'NOM DE LA VUE')   # titre principal : +14 = au-dessus
d.view_sub(  ox, top_y + 6,  'matière — dims')    # sous-titre : +6 = juste en dessous du titre
```

**Vues agrandies (détails)** :
Pour montrer un détail ×N : multiplier TOUTES les coords modèle par N (réf: Z=N).
Passer `real_diam` aux trous et le label des cotes pour afficher les vraies valeurs.
```python
Z = 3   # agrandissement ×3
d.part(ox, oy, 0, 0, 250*Z, 18*Z)
d.hole(ox, oy, 60*Z, 9*Z, diam=8*Z, depth=15, label='T-a', real_diam=8)
d.dim_h(ox, oy, 0, 60*Z, y_ref=0, ext=-14, label='60')  # label=vraie valeur
```

### `scripts/generate_pdf.py` — Dossier de fabrication PDF (reportlab)

Fonction principale : `build_pdf(data, output_path, drawing_image_path=None)`

`data` est un dict avec les clés :
- `title`, `material`, `dimensions`, `assembly`, `level`, `date`, `summary`
- `achat_matiere` (str, résumé d'achat)
- `debit` : liste de dicts `{id, nom, mat, ep, L, l, qte, notes}`
- `percage` : liste de blocs `{piece, ref_bords, trous: [{id, diam, prof, X, Y, usage}]}`
- `etapes` : liste de str — format recommandé `"Titre — corps de l'étape"`
- `outillage`, `consommables` : listes de str
- `conseils` : liste de str

`drawing_image_path` : chemin vers le PNG produit par render_drawing.py (intégré page 2 du PDF).

## Flux de travail

### Étape 1 — Recueil si informations manquantes

Si l'utilisateur n'a pas fourni assez d'infos, pose ces questions **en une seule fois** :

1. **Quoi ?** — nom et usage de la pièce
2. **Dimensions générales** — L × H × P souhaitées (ou contraintes)
3. **Matériau** — bois massif (essence), contreplaqué (mm), MDF (mm), acier, alu
4. **Assemblage** — vis, tourillons, dominos, mortaises-tenons, soudure, collage
5. **Outillage** — scie circulaire / scie à table / perceuse / fraiseuse / défonceuse

Si l'essentiel est fourni, génère directement.

### Étape 2 — Calcul et liste de débit

Calcule toutes les pièces. Règles :
- Tenir compte du trait de scie (3 mm pour bois, 2 mm pour métal)
- Proposer un débit optimisé depuis des formats standards (ex : panneau 250×122 cm)
- Indiquer les chutes réutilisables si pertinent

Présente d'abord la liste de débit en Markdown dans la réponse :

| N° | Nom | Matière | Ep. (mm) | L (mm) | l (mm) | Qté | Notes |
|----|-----|---------|-----------|---------|---------|-----|-------|

### Étape 3 — Génération du script Python

Génère un script Python complet qui :
1. Commence par un bloc d'auto-installation des dépendances :
   ```python
   import subprocess, sys
   for pkg in ["matplotlib", "reportlab", "pillow"]:
       try: __import__({"pillow":"PIL"}.get(pkg, pkg))
       except ImportError: subprocess.check_call([sys.executable,"-m","pip","install",pkg,"--break-system-packages","-q"])
   ```
2. Ajoute le répertoire du skill au `sys.path` pour importer les helpers :
   ```python
   SKILL_DIR = "/Users/{user}/.claude/skills/fabrication-plan/scripts"
   sys.path.insert(0, SKILL_DIR)
   from render_drawing import TechDrawing
   from generate_pdf import build_pdf
   ```
3. Crée un `TechDrawing` en choisissant l'échelle adaptée (1:5 pour meubles, 1:10 pour grandes pièces)
4. Pour chaque pièce (origin ox, oy sur la feuille) :
   - `d.part(ox, oy, 0, 0, largeur, hauteur)` — contour
   - `d.hole(...)` pour chaque trou avec diam, depth, label
   - `d.axis_h/v(...)` pour les lignes d'axe des trous
   - `d.dim_h/v(...)` pour toutes les cotations (largeur, hauteur, positions trous)
   - Titres au-dessus de la pièce : `d.view_label(ox, top+14, ...)` et `d.view_sub(ox, top+6, ...)`
5. Ajoute vue de détail agrandie (×3) pour les perçages de petit diamètre (Ø < 12mm)
6. `d.title_block(...)` pour le cartouche + `d.notes([...])` pour les instructions
7. `d.save(path_png)` → produit le PNG

**Conventions ISO 129-1 à respecter :**
- Cotes en mm, sans unité sur le dessin ("Toutes cotes en mm" dans les notes)
- Lignes de cote avec flèches aux deux extrémités + lignes d'attache
- Trous : Ø{diamètre} ↧{profondeur} (profondeur seulement pour trous borgnes)
- Axes de trous en tiret-point rouge
- Vues organisées : grandes pièces à gauche, détails à droite

### Étape 4 — Génération des fichiers

Génère un script Python unique qui :
1. Utilise `render_drawing.py` pour produire le dessin PNG
2. Utilise `generate_pdf.py` pour produire le dossier PDF complet
3. Sauvegarde tout dans `~/Plans_Fabrication/{nom_projet}/`
   - `plan.png` — dessin technique normalisé
   - `dossier.pdf` — dossier complet (page de garde, dessin intégré, débit, perçage, étapes, outillage)

Exécute le script avec Bash et affiche le chemin du PDF généré.

### Étape 5 — Résumé final

Après génération :
- Donne le chemin vers `dossier.pdf` et `plan.dxf`
- Liste les logiciels gratuits pour ouvrir le DXF : LibreCAD (recommandé), FreeCAD, Inkscape
- 1 conseil spécifique au projet si non évident

## Règles de qualité

- Toutes les cotes sont calculées, jamais approximées.
- Les trous de tourillons apparaissent sur CHAQUE pièce impliquée (pièce A ET pièce B).
- L'ordre des étapes de fabrication doit être réalisable : d'abord couper, puis percer,
  puis assembler à blanc, puis coller/visser.
- Si assemblage par tourillons : préciser que les trous doivent être percés avec gabarit
  de centrage pour assurer l'alignement.
- Jamais d'ASCII art pour les schémas — toujours du DXF/SVG.
- Réponds toujours en français.
