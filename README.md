# Prospectus → vidéo promo

Transforme un catalogue PDF de supermarché (export InDesign) en spot vidéo animé :
intro avec la couverture → une scène par offre (titre, badge promo, prix barré, prix,
détourage produit + sticker, page du prospectus avec l'offre surlignée) → outro marque.
Formats 16:9 (1920×1080) et 9:16 (1080×1920), 30 fps, ~15 s pour 4 offres.

## Installation (macOS)

Le détourage et l'OCR utilisent le moteur Vision d'Apple : l'outil tourne sur macOS uniquement.

```bash
brew install ffmpeg node
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd video && npm install
```

Le rendu utilise Google Chrome s'il est installé (voir `video/remotion.config.ts`).
Les catalogues, rendus de pages et visuels produits ne sont pas versionnés : régénérez-les avec l'extracteur.

## Pipeline

```
PDF ──extract.py──▶ video/public/catalog/   offers.json · fonts.json · catalog.json
                                            pages/*.jpg (rendu 200 dpi) · products/*.png (détourages)
    ──make_spot.py──▶ video/src/spots/<catalogue>.json   (offres choisies + thème + textes)
    ──remotion render──▶ output/*.mp4
```

### 1. Extraire

```bash
.venv/bin/python extractor/extract.py "catalogue.pdf" --out video/public/catalog
```

- **Offres** : lecture directe du texte vectoriel. Titre = lignes *ProximaNova Cond Bold* + marque en capitales,
  prix = gros chiffres + `€` + centimes, **prix barré** = glyphe rouge `x` de la police *Carrefour* posé dessus,
  badge = texte blanc *Black* (`-50% SUR LE 2ÈME`, `3€50 DE REMISE IMMÉDIATE`…).
- **Photos produits** : les images du PDF ont leur masque alpha (SMask) → PNG transparents sans IA de détourage.
  Si une offre n'a qu'une photo rectangulaire, la vidéo montre la zone de la page en « carte photo ».
- **Contrôle** : `output/debug/pNNN.png` montre chaque offre détectée encadrée en rose. Corrigez à la main
  `offers.json` si besoin (c'est du JSON lisible).

### 2. Choisir les offres

```bash
.venv/bin/python extractor/make_spot.py --catalog catalog --style carrefour --ids p010_01 p021_01 p018_00 p005_00 \
  --dates "DU MARDI 27 OCTOBRE|AU LUNDI 9 NOVEMBRE 2026" --bg "#a3263c"
# ou auto : --count 4 [--pages 10,18,21]
# logo : --pdf catalogue.pdf --logo-page 1 --logo-rect 14,28,236,68
```

### 3. Prévisualiser / rendre

```bash
cd video
npm run studio                                                     # éditeur live
npx remotion render src/index.ts Carrefour-16x9 ../output/carrefour_16x9.mp4   # <Marque>-16x9 / <Marque>-9x16
npx remotion render src/index.ts Carrefour-9x16 ../output/carrefour_9x16.mp4
```

Réglages : durées dans `video/src/timing.ts`, positions dans `useLayout()` (`video/src/components.tsx`),
animations dans `video/src/scenes.tsx`.

## Catalogues « aplatis » (ex. Leclerc)

Certains PDF n'ont aucun texte : chaque page est une seule image. Deux options :

- `extractor/extract_raster.py` : OCR macOS Vision + détourage automatique. **Expérimental** : les gros
  chiffres stylisés et les stickers « 2€ avec la Carte » sont encore mal interprétés.
- `extractor/offers_from_spec.py` (mode assisté, utilisé pour la vidéo Leclerc) : un JSON décrit chaque
  offre (textes, prix, cadre du produit sur la page) et le produit est détouré automatiquement par Vision.

```bash
.venv/bin/python extractor/offers_from_spec.py specs/leclerc.json "catalogue leclerc.pdf" --out video/public/leclerc
.venv/bin/python extractor/make_spot.py --catalog leclerc --ids pat_patrouilleur fort_boyard minnie dessinez escape_game \
  --bg "#0a5aa8" --accent "#ffe600" --sticker-text "#0a5aa8" --dates "DU 27 OCTOBRE|AU 13 DÉCEMBRE 2026" \
  --tagline "TOUT CE QUI COMPTE POUR VOUS|EXISTE À PRIX E.LECLERC" --cta "COMMANDEZ EN|CLICK & COLLECT" \
  --logo-crop 0.095,0.008,0.385,0.085
cd video && npx remotion render src/index.ts Leclerc-16x9 ../output/leclerc_16x9.mp4
```

**Visuels HD** : dans la spec, `imageUrl` remplace le crop de la page par le packshot du site marchand
(Leclerc : `https://media.e.leclerc/<EAN>_1?fmt=png-alpha`, EAN trouvé via la recherche du site). Le fond blanc
et le reflet sont retirés automatiquement.

**Catalogue en ligne sans PDF (ex. Lidl)** : `"pageImages": {"1": "<url>", ...}` dans la spec remplace le PDF
(`offers_from_spec.py specs/lidl.json --out video/public/lidl`). Les URLs des pages HD, des produits et de leurs
visuels viennent du JSON public du lecteur Lidl (`endpoints.leaflets.schwarz/v4/flyer?flyer_identifier=...`).
Par offre, `"cutout": "vision"` (électroménager, verre, métal) ou `"white"` + `"whiteTol"` (boîtes, reflets).

**PDF vectoriels d'autres enseignes (ex. Auchan)** : `extract.py` détecte le profil de polices
(`carrefour`, `auchan`, ou `--profile`). Les erreurs ponctuelles se corrigent dans un fichier
`specs/<enseigne>_overrides.json` passé à `make_spot.py --overrides` (gardé même si on ré-extrait) ;
`"cutout": "vision"` y détoure une photo pleine.

**Charte par marque** : `--style carrefour|leclerc` choisit un preset de `video/src/brand.ts`
(polices, décor du fond, sticker, format de prix « 59€,90 », pastilles de dates). Leclerc reprend les tokens du
site e.leclerc : bleu `#0066cc`, marine `#0f1e6b`, orange `#ff6633`, jaune `#ffcc01`, Roboto / Roboto Condensed.

Chaque marque a sa config dans `video/src/spots/<catalogue>.json` et ses compositions `<Marque>-16x9` / `<Marque>-9x16`
(à déclarer dans `video/src/Root.tsx`). Un prix avec `label` (« PRIX PAYÉ EN CAISSE ») n'est pas barré.

## Polices du catalogue (fonts.json)

| Famille | Usage dans le catalogue |
|---|---|
| Proxima Nova Condensed (Light / Semibold / Bold) | descriptifs, noms produits, mentions fidélité |
| Proxima Nova (Regular / Medium / Bold / Black / Extrabold) | prix, badges promo, titres de rayon |
| DIN OT Condensed | titres d'univers (« ÉQUATEUR / VENEZUELA »…) |
| Proxima Nova Extra Condensed, Futura Std, Omnes, Ubuntu, Lato, Chaloops | ponctuel (pages partenaires) |
| Carrefour (police pictos) | logo, barre du prix barré |

Proxima Nova / DIN sont des polices commerciales : si elles sont installées sur la machine, la vidéo les
utilise ; sinon **Montserrat** (prix/badges) et **Barlow Condensed** (noms) servent de substituts.
