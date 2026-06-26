# fabrication-plan — Claude Code Skill

Un skill Claude Code pour générer des **plans de fabrication manuelle** complets : menuiserie, atelier, bricolage, métallerie.

## Ce qu'il produit

Pour chaque projet décrit, le skill génère :

- **Liste de débit** — toutes les pièces avec dimensions précises (L × l × épaisseur, matière, quantité)
- **Plan de perçage** — position des trous avec cotes X/Y depuis un bord de référence, diamètre `Ø`, profondeur `↧`
- **Fichier DXF** — dessin technique avec cotation normalisée ISO 129-1 (lignes de cote, flèches, lignes d'axe)
- **Export SVG** — vue vectorielle imprimable directement
- **Dossier PDF** — document complet style bureau d'études : page de garde, dessin technique, liste de débit, plans de perçage, étapes de fabrication, checklist outillage

## Installation

```bash
# Cloner dans votre dossier de skills Claude Code
git clone https://github.com/TobieTheUnknown/fabrication-plan ~/.claude/skills/fabrication-plan
```

Les dépendances Python (`ezdxf`, `reportlab`, `matplotlib`) sont **auto-installées** au premier usage — pas besoin de setup manuel.

## Usage

Dans Claude Code, décrivez simplement votre projet :

```
/fabrication-plan étagère murale 80×90cm, contreplaqué 18mm, 3 tablettes, tourillons
```

Ou en langage naturel :

```
je veux fabriquer un établi d'atelier en hêtre massif 40mm, 160×70cm, pieds pin 70×70mm
```

```
plan de fabrication pour une boîte à outils 30×20×15cm en MDF 10mm, couvercle coulissant
```

## Exemple de sortie

Le dossier `examples/` contient un plan complet pour une **étagère murale 3 tablettes** :
- [`etagere_murale_3_tablettes.pdf`](examples/etagere_murale_3_tablettes.pdf) — dossier PDF complet

## Structure

```
fabrication-plan/
├── SKILL.md                  ← Instructions du skill (lues par Claude)
├── scripts/
│   ├── base_drawing.py       ← Helper ezdxf : dessin technique DXF/SVG (ISO 129-1)
│   └── generate_pdf.py       ← Générateur de dossier PDF (reportlab)
├── evals/
│   └── evals.json            ← Cas de test
└── examples/
    └── etagere_murale_3_tablettes.pdf
```

## Matériaux supportés

- Bois massif (toutes essences)
- Contreplaqué (tout format)
- MDF
- Acier / aluminium
- Assemblages : tourillons, dominos, mortaises-tenons, vis, collage, soudure

## Ouvrir le fichier DXF

Le DXF généré s'ouvre dans n'importe quel logiciel CAO :
- [LibreCAD](https://librecad.org/) — gratuit, recommandé
- [FreeCAD](https://www.freecad.org/) — gratuit, 3D + 2D
- [Inkscape](https://inkscape.org/) — gratuit, vectoriel

## Licence

MIT
