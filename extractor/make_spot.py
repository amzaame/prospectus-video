"""Pick offers from offers.json and write the props file the video template reads.

Usage:
    python extractor/make_spot.py                       # auto-pick 4 good offers
    python extractor/make_spot.py --ids p010_01 p021_01 p018_00
    python extractor/make_spot.py --pages 10,18 --count 3 --bg "#a3263c"
    python extractor/make_spot.py --logo-page 1 --logo-rect 14,28,236,68   # crop brand logo from the PDF
"""
import argparse
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
PUBLIC = ROOT / "video/public"


def score(o):
    s = 0
    s += 3 if o.get("image") else -10
    s += 2 if o.get("price") else -5
    s += 2 if o.get("badge") else 0
    s += 1 if o.get("oldPrice") else 0
    s += 1 if o.get("brand") else 0
    if o.get("badge") and o["badge"]["kind"] == "percent":
        s += 1
    if o.get("image"):
        w, h = o["image"]["width"], o["image"]["height"]
        s += 1 if min(w, h) > 300 else -2
    return s


def crop_logo(pdf, page, rect, out):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(pdf)
    clip = fitz.Rect(*rect)
    doc[page - 1].get_pixmap(dpi=500, clip=clip).save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="catalog", help="folder under video/public written by the extractor")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--pages", help="restrict auto-pick to these pages, e.g. 10,18,21")
    ap.add_argument("--count", type=int, default=4)
    ap.add_argument("--bg", default="#a3263c", help="background colour of the spot")
    ap.add_argument("--accent", default="#ffd400", help="sticker colour")
    ap.add_argument("--sticker-text", default="#d0021b", help="sticker text colour")
    ap.add_argument("--style", default="carrefour", help="brand style preset in video/src/brand.ts (carrefour, leclerc)")
    ap.add_argument("--dates", help='date pill text, e.g. "DU MARDI 27 OCTOBRE|AU LUNDI 9 NOVEMBRE 2026"')
    ap.add_argument("--tagline", default="ON A TOUS DROIT|AU MEILLEUR")
    ap.add_argument("--cta", default="TÉLÉCHARGEZ|L'APPLICATION")
    ap.add_argument("--legal", default="Pour votre santé, mangez au moins cinq fruits et légumes par jour. "
                                       "Plus d'informations sur www.mangerbouger.fr")
    ap.add_argument("--pdf", help="source PDF (only needed to crop the logo)")
    ap.add_argument("--logo-page", type=int, default=1)
    ap.add_argument("--logo-rect", help="x0,y0,x1,y1 in PDF points")
    ap.add_argument("--logo-crop", help="x0,y0,x1,y1 normalised 0..1 on the rendered page (flattened PDFs)")
    ap.add_argument("--overrides", help="JSON {offer_id: {field: value}} applied on top of offers.json "
                                        "(survives a re-extraction); \"cutout\": \"vision\" re-cuts a flat photo")
    ap.add_argument("--out", default=None, help="defaults to video/src/spots/<catalog>.json")
    a = ap.parse_args()
    CATALOG = PUBLIC / a.catalog
    pre = a.catalog + "/"

    offers = json.loads((CATALOG / "offers.json").read_text())
    catalog = json.loads((CATALOG / "catalog.json").read_text())
    if a.ids:
        by_id = {o["id"]: o for o in offers}
        picked = [by_id[i] for i in a.ids]
    else:
        pool = offers
        if a.pages:
            keep = {int(p) for p in a.pages.split(",")}
            pool = [o for o in offers if o["page"] in keep]
        pool = sorted(pool, key=score, reverse=True)
        picked, seen_pages = [], set()
        for o in pool:  # one offer per page first, for variety
            if o["page"] not in seen_pages:
                picked.append(o)
                seen_pages.add(o["page"])
            if len(picked) == a.count:
                break

    if a.overrides:
        fixes = json.loads(Path(a.overrides).read_text())
        for i, o in enumerate(picked):
            fix = dict(fixes.get(o["id"], {}))
            if fix.pop("cutout", None) == "vision" and o.get("image"):
                from extract_raster import lift  # macOS Vision subject lifting
                src = CATALOG / o["image"]["src"]
                dst = src.with_name(src.stem + "_lift.png")
                (w, h), _ = lift(src, [0, 0, 1, 1], [], dst)
                fix["image"] = dict(src=f"products/{dst.name}", width=w, height=h)
            picked[i] = dict(o, **fix)

    pages = {p["page"]: p for p in catalog["pages"]}
    logo = None
    if a.logo_rect and a.pdf:
        crop_logo(a.pdf, a.logo_page, [float(v) for v in a.logo_rect.split(",")], CATALOG / "logo.png")
    elif a.logo_crop:
        from PIL import Image
        im = Image.open(CATALOG / pages[a.logo_page]["image"])
        x0, y0, x1, y1 = [float(v) for v in a.logo_crop.split(",")]
        im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height))).save(CATALOG / "logo.png")
    if (CATALOG / "logo.png").exists():
        logo = pre + "logo.png"

    dates = a.dates.split("|") if a.dates else (catalog["validity"][:1] or ["", ""])
    if len(dates) == 1 and " AU " in dates[0].upper():
        i = dates[0].upper().index(" AU ")
        dates = [dates[0][:i], dates[0][i + 1:]]

    spot = dict(
        cover=pre + pages[1]["image"],
        coverAspect=pages[1]["width"] / pages[1]["height"],
        dates=[d.upper() for d in dates],
        theme=dict(bg=a.bg, accent=a.accent, stickerText=a.sticker_text, style=a.style),
        logo=logo,
        tagline=a.tagline.split("|"),
        cta=a.cta.split("|"),
        legal=a.legal,
        offers=[dict(o, pageImage=pre + pages[o["page"]]["image"],
                     image=o["image"] and dict(o["image"], src=pre + o["image"]["src"]),
                     pageAspect=pages[o["page"]]["width"] / pages[o["page"]]["height"]) for o in picked],
    )
    a.out = a.out or str(ROOT / f"video/src/spots/{a.catalog}.json")
    Path(a.out).write_text(json.dumps(spot, ensure_ascii=False, indent=2))
    for o in picked:
        print(o["id"], "|", o["name"], o["brand"], "|", (o["badge"] or {}).get("text"), "|",
              o["price"] and o["price"]["value"])
    print("->", a.out)


if __name__ == "__main__":
    main()
