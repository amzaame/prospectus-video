---
name: catalog-video
description: Turn a supermarket catalogue (PDF or online flyer URL) into animated promo videos, 16:9 and 9:16, in the retailer's brand style. Use when the person gives a prospectus / catalogue / flyer (Carrefour, Leclerc, Lidl, Auchan or any other retailer) and wants a video, a spot, a reel or a story showing its offers.
---

# Catalogue → promo video

You turn a retailer's catalogue into a 15–20 s spot: cover intro → one scene per offer (name, promo badge,
old/new price, product cut-out with a sticker, the catalogue page with the offer framed) → brand outro.
The scripts do the mechanical work; your job is the judgment the scripts cannot make: which route to take,
which offers to show, whether every price and cut-out is right, and what the brand looks like.

**Paths.** The tool lives two levels above this skill's base directory (`<base>/../..`, called TOOL below).
Never write inside TOOL. Everything happens in a workspace, by default `./prospectus-video` in the
person's current folder (WS below). Run every command from WS.

## 1. Workspace

If `WS/.venv` or `WS/video/node_modules` is missing, run `bash TOOL/scripts/setup.sh WS` (a few minutes:
Python packages and npm). It stops with a clear message when something is missing (macOS only, node,
ffmpeg); tell the person the fix (`brew install …`) rather than working around it. Re-run it after a plugin
update; it keeps the person's files.

## 2. Find the route

Ask for nothing you can find out. With a PDF:

```bash
.venv/bin/python extractor/probe.py "<pdf>"
```

| probe says | route |
|---|---|
| vector, profile carrefour / auchan | **A**: automatic extraction |
| vector, unknown fonts | **A** after adding a profile (reference.md › New font profile) |
| flattened | **B**: you read the pages and write a spec |
| (a flyer URL, no PDF) | **C**: online flyer |

**A. Vector PDF**

```bash
.venv/bin/python extractor/extract.py "<pdf>" --out video/public/<name> --debug output/debug_<name>
```

`<name>` is a short lowercase slug (`auchan`, `carrefour_nov`). It writes `offers.json` (one entry per
offer with id `pNNN_KK`), native cut-outs, page renders, and `output/debug_<name>/pNNN.png` with every
detected offer framed in pink. Expect a few mistakes: a price taken from the neighbouring offer, a missed
old price, a logo instead of the product.

**B. Flattened PDF** (no text layer): render grids, read the pages yourself, and write `specs/<name>.json`:

```bash
.venv/bin/python extractor/offers_from_spec.py specs/<name>.json "<pdf>" --out video/public/<name>
.venv/bin/python extractor/grid.py video/public/<name>/pages/p011.jpg --out output/grids
```

Look at the grid images to read `productBox` and `region` as fractions of the page (format in
reference.md › Spec). First run the spec with only the pages you need so the page images exist, then add the boxes.

**C. Online flyer**: open it in the browser, decline non-essential cookies, and look at the network requests
or page data for a JSON feed of pages and products (Lidl: `endpoints.leaflets.schwarz/v4/flyer?flyer_identifier=…`).
Put page image URLs in the spec's `pageImages`. Use only what the public viewer itself loads: if an API
answers "Access Denied" or asks for a login, stop using it — never work around bot protection.

**Better product photos (any route).** A retailer's product page often has a bigger packshot than the
catalogue. Find it with the site's own search (EAN / product id), put it in the offer's `imageUrl`, and pick
the cut-out method: `"cutout": "white"` (default) for boxes and packs, `"vision"` for appliances, glass,
metal or anything with light parts on a white background. A spec entry with `imageUrl` works on top of route A
too, through the overrides file (reference.md › Overrides).

## 3. Choose and check the offers

Pick 4–6 offers for a 15–20 s spot. Prefer: a real promo (%, € off, 2nd at −x %, loyalty cash-back), a
clean cut-out, variety (fresh food + grocery + non-food), offers from different pages. Avoid alcohol unless
the person wants it (it needs the alcohol health warning as the legal line).

Then **check every chosen offer against the page image**, not the JSON: name, brand, price, cents, old
price, badge text, and the cut-out (look at the PNG on a coloured background — missing parts, a logo instead
of the product, a crop cut by a price tag, a reflection). Fix route A mistakes in `specs/<name>_overrides.json`
(survives re-extraction), route B/C mistakes in the spec. Flat photo with a background → `"cutout": "vision"`
in the overrides. Do not ship a price you have not seen on the page.

## 4. Brand style

Presets in `video/src/brand.ts`: `carrefour`, `leclerc`, `lidl`, `auchan`. For another retailer create one
(reference.md › New brand style): colours from the retailer's website (computed styles / CSS variables) and
from the PDF fills, its fonts identified but **replaced by the closest Google font** — brand fonts are
proprietary, never download or embed them. Background motif, sticker shape, price format (`stack` 44€99,
`comma` 59€,90, `inline` 44.99) and date pills follow what the catalogue does.

## 5. Build the spot config

```bash
.venv/bin/python extractor/make_spot.py --catalog <name> --style <brand> --ids <id> <id> … \
  [--overrides specs/<name>_overrides.json] --bg "#…" --accent "#…" --sticker-text "#…" \
  --dates "DU …|AU …" --tagline "LINE 1|LINE 2" --cta "LINE 1|LINE 2" --legal "…" \
  --logo-crop x0,y0,x1,y1          # logo on the cover page, fractions (or --pdf … --logo-rect in PDF points)
```

- Dates: the catalogue's general validity (cover or the retailer's site); say so when offers have narrower dates.
- Legal line: the mandatory mention printed in the catalogue — food: the mangerbouger.fr line the catalogue
  uses; alcohol: "L'abus d'alcool est dangereux pour la santé. À consommer avec modération."
- Tagline: the retailer's own slogan from the catalogue; CTA: its app or website.
- Check the logo crop by looking at `video/public/<name>/logo.png`.

It writes `video/src/spots/<name>.json`; compositions `<Name>-16x9` and `<Name>-9x16` appear by themselves.

## 6. Render and look

Render stills first and look at them — every offer scene (around frames 110 + 82·k), the intro (30) and the outro (last frame − 20):

```bash
cd video && npx remotion still src/index.ts <Name>-16x9 ../output/stills/<name>_110.jpg --frame=110
```

Check: text overflowing or wrapping badly, sticker over the product name, the yellow frame on the right
offer, cut-outs complete, outro text clear of the logo, the same in 9:16. Fix, then render both:

```bash
npx remotion render src/index.ts <Name>-16x9 ../output/<name>_16x9.mp4
npx remotion render src/index.ts <Name>-9x16 ../output/<name>_9x16.mp4
```

Each render takes 1–3 minutes; run them in the background when you can.

## 7. Report

Give the paths of both MP4s, the offers shown with their prices, what you corrected by hand, what you
assumed (dates, legal line, fonts substituted), and what you did not check. These videos carry the
retailer's logo and products: they are for the retailer or with its permission.
