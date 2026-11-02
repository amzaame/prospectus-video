"""Extract offers, fonts and product cut-outs from a supermarket catalogue PDF.

Works on vector PDFs exported from InDesign (real text + images with alpha masks).

Usage:
    python extractor/extract.py catalogue.pdf --out video/public/catalog [--pages 1-20]
"""
import argparse
import collections
import json
import math
import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw

PAGE_DPI = 200          # page renders used as backgrounds in the video
WHITE = 0xFFFFFF
# Font conventions differ per retailer; the profile is picked from the fonts used in the PDF.
PROFILES = {
    "carrefour": dict(
        title=r"Cond-?Bold", title_size=(6.5, 15), desc=r"Cond-Light", loyalty=r"Cond-Semibold",
        strike=lambda o: o["font"] == "Carrefour" and o["text"] == "x"),
    "auchan": dict(
        title=r"SanaSansAltExp-Heavy", title_size=(7.5, 11), desc=r"SanaSansAltExp-Medium", loyalty=r"^$",
        strike=lambda o: "PrixBarre" in o["font"]),
}
PROFILE = PROFILES["carrefour"]
# words that make white figures a promo badge rather than the selling price
PROMO_RE = re.compile(r"REMISE|%|SUR LE|OFFERT|ÉCONOM|ECONOM|CAGNOTT|GRATUIT|\d\s*\+\s*\d", re.I)
DATE_RE = re.compile(r"\b(DU|AU)\b.*\b(JANVIER|FÉVRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AOÛT|SEPTEMBRE|OCTOBRE|NOVEMBRE|DÉCEMBRE)\b", re.I)


def font_family(name):
    return name.split("+")[-1]


def rect_dist(a, b):
    """Distance between two rects (0 if they overlap)."""
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy)


def union(rects):
    rects = [r for r in rects if r]
    return [min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[2] for r in rects), max(r[3] for r in rects)]


def spans_of(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip() and s["size"] > 0.5:
                    out.append(dict(text=s["text"], font=font_family(s["font"]),
                                    size=s["size"], color=s["color"], bbox=list(s["bbox"])))
    return out


# ---------------------------------------------------------------- titles
def is_title_span(s):
    lo, hi = PROFILE["title_size"]
    return re.search(PROFILE["title"], s["font"]) and lo <= s["size"] <= hi and not DATE_RE.search(s["text"])


def is_desc_span(s):
    return re.search(PROFILE["desc"], s["font"]) and s["size"] <= 9 and s["color"] != WHITE


def find_titles(spans):
    """Product titles: stacked Cond-Bold lines, followed by Cond-Light description lines."""
    cand = sorted([s for s in spans if is_title_span(s)], key=lambda s: (s["bbox"][1], s["bbox"][0]))
    groups = []
    for s in cand:
        for g in groups:
            last = g[-1]
            if abs(s["bbox"][0] - g[0]["bbox"][0]) < 4 and 0 <= s["bbox"][1] - last["bbox"][1] < s["size"] * 1.6:
                g.append(s)
                break
            if abs(s["bbox"][1] - last["bbox"][1]) < 2 and 0 <= s["bbox"][0] - last["bbox"][2] < 6:
                g.append(s)  # same line continuation
                break
        else:
            groups.append([s])
    titles = []
    for g in groups:
        lines = collections.OrderedDict()
        for s in g:
            lines.setdefault(round(s["bbox"][1]), []).append(s["text"])
        lines = [" ".join(t).strip() for t in lines.values()]
        text = " ".join(lines)
        if len(text) < 4:
            continue
        bbox = union([s["bbox"] for s in g])
        # brand = trailing uppercase line(s)
        brand = lines[-1] if len(lines) > 1 and lines[-1].upper() == lines[-1] else ""
        name = " ".join(lines[:-1]) if brand else text
        titles.append(dict(name=re.sub(r"\s+", " ", name).strip(), brand=brand.strip(),
                           bbox=bbox, desc=[], loyalty=[]))
    # attach description lines just below each title
    for s in spans:
        for key, test in (("desc", is_desc_span),
                          ("loyalty", lambda s: re.search(PROFILE["loyalty"], s["font"]) and s["size"] <= 9)):
            if not test(s):
                continue
            for t in titles:
                tb = t["bbox"]
                if abs(s["bbox"][0] - tb[0]) < 4 and -2 < s["bbox"][1] - tb[3] < 30:
                    t[key].append(s["text"].strip())
                    t["bbox"] = union([tb, s["bbox"]])
                    break
    return titles


# ---------------------------------------------------------------- prices
def find_prices(spans):
    """Big integer part + '€' + cents to its right. Red 'x' glyph (Carrefour font) = struck price."""
    prices = []
    used = set()
    big = [s for s in spans if re.fullmatch(r"\d{1,3}", s["text"].strip()) and s["size"] >= 14
           and re.search(r"Bold|Black|Extrabld|Heavy", s["font"])]
    for s in big:
        if id(s) in used:
            continue
        b = s["bbox"]
        right = [o for o in spans if o is not s and 0 <= o["bbox"][0] - b[2] + 2 < 8
                 and b[1] - 2 <= o["bbox"][1] <= b[3]]
        euro = next((o for o in right if "€" in o["text"]), None)
        if not euro:
            continue
        cents = next((o for o in right if re.fullmatch(r"\d{2}", o["text"].strip()) and o is not euro), None)
        parts = [s, euro] + ([cents] if cents else [])
        bbox = union([p["bbox"] for p in parts])
        # white figures are a badge ("2€ DE REMISE") unless they are the price printed in a coloured box
        is_badge = s["color"] == WHITE and any(
            o["color"] == WHITE and PROMO_RE.search(o["text"]) and rect_dist(o["bbox"], bbox) < 20 for o in spans)
        # the strike glyph is about as tall as the price it crosses (not the bigger new price under it)
        ph = bbox[3] - bbox[1]
        struck = any(PROFILE["strike"](o) and rect_dist(o["bbox"], bbox) < 4
                     and abs((o["bbox"][3] - o["bbox"][1]) - ph) < 0.5 * ph for o in spans)
        value = float(f"{s['text'].strip()}.{cents['text'].strip() if cents else '00'}")
        # small caption lines under the price (unit price, "La bouteille", ...)
        caption = [o["text"].strip() for o in spans
                   if o["size"] < 8 and abs(o["bbox"][0] - b[0]) < 4 and 0 <= o["bbox"][1] - bbox[3] + 8 < 16
                   and o["color"] == s["color"]]
        prices.append(dict(value=value, int=s["text"].strip(), cents=cents["text"].strip() if cents else "",
                           size=s["size"], color=f"#{s['color']:06x}", struck=struck,
                           badge=is_badge, bbox=bbox, caption=caption))
    return prices


# ---------------------------------------------------------------- badges
def find_badges(spans, prices):
    """White, heavy text = promo badge ("-50% SUR LE 2ème", "30% D'ÉCONOMIES", "2€50 DE REMISE IMMÉDIATE")."""
    white = [s for s in spans if s["color"] == WHITE and (re.search(r"Black|Extrabld|Heavy", s["font"]) or "€" in s["text"])]
    clusters = []
    for s in sorted(white, key=lambda s: (s["bbox"][1], s["bbox"][0])):
        for c in clusters:
            if rect_dist(union([x["bbox"] for x in c]), s["bbox"]) < 6:
                c.append(s)
                break
        else:
            clusters.append([s])
    badges = []
    for c in clusters:
        bbox = union([x["bbox"] for x in c])
        # headline = the numeric glyphs ("-", "25", "%" / "2", "€", "50"), read left to right
        numeric = lambda x: re.fullmatch(r"[-+\d%€,]+", x["text"].strip())
        head = [x for x in c if numeric(x)]
        rest = [x for x in c if not numeric(x)]
        clean = lambda t: re.sub(r"\s+", " ", re.sub(r"\(\d+\)|\*+", "", t)).strip()
        headline = clean("".join(x["text"] for x in sorted(head, key=lambda x: x["bbox"][0])).replace(" ", ""))
        lines = collections.OrderedDict()
        for x in sorted(rest, key=lambda x: (round(x["bbox"][1] / 5), x["bbox"][0])):
            lines.setdefault(round(x["bbox"][1] / 5), []).append(x["text"])
        sub = clean(" ".join("".join(v) for v in lines.values()))
        # "SUR LE 2ème": the exponent is a separate small span
        sub = re.sub(r"(\d)\s*(ÈME|EME|ème)\b", r"\1\2", sub)
        text = f"{headline} {sub}".strip()
        if not headline or not re.search(r"\d|OFFERT|GRATUIT", text, re.I) or len(text) > 80:
            continue
        if not PROMO_RE.search(text):  # e.g. "LA BARQUETTE 8€99" printed white in a price box
            continue
        kind = "percent" if "%" in headline else "amount" if "€" in headline else "other"
        badges.append(dict(text=text, kind=kind, bbox=bbox, headline=headline, sub=sub))
    return badges


# ---------------------------------------------------------------- images
def page_images(doc, page):
    out = []
    area = page.rect.width * page.rect.height
    for info in page.get_image_info(xrefs=True):
        x = info["xref"]
        if not x:
            continue
        bbox = [max(0, info["bbox"][0]), max(0, info["bbox"][1]),
                min(page.rect.width, info["bbox"][2]), min(page.rect.height, info["bbox"][3])]
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w < 25 or h < 25:
            continue
        smask = doc.extract_image(x).get("smask", 0)
        out.append(dict(xref=x, smask=smask, bbox=bbox, area=w * h / area))
    return out


def save_cutout(doc, img, path):
    pix = fitz.Pixmap(doc, img["xref"])
    if img["smask"]:
        mask = fitz.Pixmap(doc, img["smask"])
        if pix.n - pix.alpha >= 4:  # CMYK -> RGB before adding alpha
            pix = fitz.Pixmap(fitz.csRGB, pix)
        try:
            pix = fitz.Pixmap(pix, mask)
        except Exception:
            pass
    elif pix.n - pix.alpha >= 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if pix.colorspace and pix.colorspace.n >= 4 or (pix.colorspace and pix.colorspace.n == 3 and pix.n - pix.alpha != 3):
        pix = fitz.Pixmap(fitz.csRGB, pix)
    try:
        pix.save(path)
    except Exception:  # odd colour spaces (Lab, DeviceN): go through RGB without alpha, then re-apply the mask
        rgb = fitz.Pixmap(fitz.csRGB, fitz.Pixmap(doc, img["xref"]))
        rgb.save(path)
        if img["smask"]:
            m = fitz.Pixmap(doc, img["smask"])
            mask = Image.frombytes("L", (m.width, m.height), m.samples)
            im = Image.open(path).convert("RGB")
            im.putalpha(mask.resize(im.size))
            im.save(path)
    # trim transparent borders
    im = Image.open(path)
    if im.mode == "RGBA":
        bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if bb:
            im.crop(bb).save(path)
    return Image.open(path).size


# ---------------------------------------------------------------- page theme
def page_theme(png_path):
    """Dominant saturated colour of the page (used as video background)."""
    im = Image.open(png_path).convert("RGB").resize((80, 134))
    counts = collections.Counter()
    for r, g, b in im.getdata():
        mx, mn = max(r, g, b), min(r, g, b)
        if mx - mn > 60 and 50 < mx < 250:
            counts[(r // 24 * 24, g // 24 * 24, b // 24 * 24)] += 1
    if not counts:
        return "#1f4fa3"
    r, g, b = counts.most_common(1)[0][0]
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------- main
def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a) - 1, int(b or a)))
    return [p for p in out if p < n]


def extract(pdf, out, pages=None, debug_dir="output/debug", profile=None):
    global PROFILE
    out = Path(out)
    for d in ("pages", "products"):
        (out / d).mkdir(parents=True, exist_ok=True)
    debug = Path(debug_dir) if debug_dir else None
    if debug:
        debug.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    if not profile:  # guess from the fonts of the first pages
        sample = " ".join(f[3] for p in list(doc)[:4] for f in p.get_fonts())
        profile = "auchan" if "SanaSans" in sample else "carrefour"
    PROFILE = PROFILES[profile]
    print("profile:", profile)

    fonts = collections.Counter()
    font_roles = collections.defaultdict(collections.Counter)
    offers, page_meta = [], []
    validity = collections.Counter()

    for pno in parse_pages(pages, doc.page_count):
        page = doc[pno]
        W, H = page.rect.width, page.rect.height
        spans = spans_of(page)
        for s in spans:
            fonts[s["font"]] += len(s["text"])
        for s in spans:
            if DATE_RE.search(s["text"]):
                validity[s["text"].strip()] += 1

        png = out / "pages" / f"p{pno + 1:03d}.jpg"
        page.get_pixmap(dpi=PAGE_DPI).pil_save(png, quality=88)
        page_meta.append(dict(page=pno + 1, image=f"pages/{png.name}", width=W, height=H,
                              theme=page_theme(png),
                              heading=next((s["text"].strip() for s in sorted(spans, key=lambda s: -s["size"])
                                            if s["bbox"][1] < 60 and len(s["text"].strip()) > 3), "")))

        titles = find_titles(spans)
        prices = find_prices(spans)
        badges = find_badges(spans, prices)
        images = [i for i in page_images(doc, page) if i["smask"] and 0.01 < i["area"] < 0.45]  # skip logos/labels

        for t in titles:
            font_roles["title"][next(s["font"] for s in spans if s["text"] and s["bbox"][1] >= t["bbox"][1] - 1
                                     and is_title_span(s))] += 1
        for p in prices:
            font_roles["price"]["ProximaNova-Bold"] += 1

        cards = [dict(title=t, prices=[], badges=[], image=None) for t in titles]
        if not cards:
            continue
        # photo cells: a price printed on the same photo as a title belongs to it (Auchan puts the price
        # box in the opposite corner of the photo), otherwise the nearest title wins
        cells = [i["bbox"] for i in page_images(doc, page) if 0.03 < i["area"] < 0.6]

        def cell_of(r):
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            inside = [c for c in cells if c[0] - 8 <= cx <= c[2] + 8 and c[1] - 8 <= cy <= c[3] + 8]
            return min(inside, key=lambda c: (c[2] - c[0]) * (c[3] - c[1])) if inside else None

        for p in prices:
            if p["badge"]:
                continue
            pc = cell_of(p["bbox"])
            same = [c for c in cards if pc and cell_of(c["title"]["bbox"]) == pc]
            pool = same or cards
            c = min(pool, key=lambda c: rect_dist(p["bbox"], c["title"]["bbox"]))
            if same or rect_dist(p["bbox"], c["title"]["bbox"]) < 120:
                c["prices"].append(p)
        for b in badges:
            # badge sits above its price, same left column
            def score(c):
                ref = union([c["title"]["bbox"]] + [p["bbox"] for p in c["prices"]])
                col = 0 if any(abs(p["bbox"][0] - b["bbox"][0]) < 12 for p in c["prices"]) else 40
                return rect_dist(b["bbox"], ref) + col
            c = min(cards, key=score)
            if score(c) < 160:
                c["badges"].append(b)
        # images: greedy match, nearest first but favouring big pictures over small labels
        anchor = lambda c: union([c["title"]["bbox"]] + [p["bbox"] for p in c["prices"]])
        pairs = sorted(((rect_dist(i["bbox"], anchor(c)) - 120 * math.sqrt(i["area"]), rect_dist(i["bbox"], anchor(c)), ci, ii)
                        for ci, c in enumerate(cards) for ii, i in enumerate(images)))
        used_c, used_i = set(), set()
        for _, d, ci, ii in pairs:
            if ci in used_c or ii in used_i or d > 160:
                continue
            cards[ci]["image"] = images[ii]
            used_c.add(ci)
            used_i.add(ii)

        for k, c in enumerate(cards):
            if not c["prices"] and not c["badges"]:
                continue
            oid = f"p{pno + 1:03d}_{k:02d}"
            t = c["title"]
            prices_sorted = sorted(c["prices"], key=lambda p: (p["struck"] is False, p["bbox"][1]))
            old = next((p for p in prices_sorted if p["struck"]), None)
            new = [p for p in c["prices"] if not p["struck"]]
            new = max(new, key=lambda p: p["size"]) if new else None
            cutout = None
            if c["image"]:
                path = out / "products" / f"{oid}.png"
                try:
                    w, h = save_cutout(doc, c["image"], path)
                    cutout = dict(src=f"products/{path.name}", width=w, height=h)
                except Exception as e:  # odd colourspaces
                    print("cutout failed", oid, e)
            region = union([t["bbox"]] + [p["bbox"] for p in c["prices"]] + [b["bbox"] for b in c["badges"]]
                           + ([c["image"]["bbox"]] if c["image"] else []))
            offers.append(dict(
                id=oid, page=pno + 1,
                name=t["name"], brand=t["brand"], description=" ".join(t["desc"]),
                loyalty=" ".join(t["loyalty"]),
                badge=(c["badges"][0] if c["badges"] else None),
                price=(dict(int=new["int"], cents=new["cents"], value=new["value"], caption=new["caption"])
                       if new else None),
                oldPrice=(dict(int=old["int"], cents=old["cents"], value=old["value"], caption=old["caption"])
                          if old else None),
                image=cutout,
                region=[round(region[0] / W, 4), round(region[1] / H, 4),
                        round(region[2] / W, 4), round(region[3] / H, 4)],
            ))
        if debug:
            draw_debug(png, debug / png.name.replace(".jpg", ".png"), W, H, [o for o in offers if o["page"] == pno + 1])

    meta = dict(
        source=Path(pdf).name, title=doc.metadata.get("title"), pageCount=doc.page_count,
        validity=[v for v, _ in validity.most_common(3)],
        pages=page_meta,
    )
    fonts_out = dict(
        byUsage=[dict(font=f, chars=n) for f, n in fonts.most_common()],
        families=sorted({re.split(r"-|Cond|ExCn", f)[0] for f in fonts}),
        roles={k: v.most_common(3) for k, v in font_roles.items()},
    )
    (out / "catalog.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    (out / "offers.json").write_text(json.dumps(offers, ensure_ascii=False, indent=2))
    (out / "fonts.json").write_text(json.dumps(fonts_out, ensure_ascii=False, indent=2))
    print(f"{len(offers)} offers, {sum(1 for o in offers if o['image'])} with cut-outs -> {out}")
    return offers


def draw_debug(src, dst, W, H, offers):
    im = Image.open(src).convert("RGB")
    sx, sy = im.width / W, im.height / H
    d = ImageDraw.Draw(im)
    for o in offers:
        r = o["region"]
        d.rectangle([r[0] * im.width, r[1] * im.height, r[2] * im.width, r[3] * im.height],
                    outline=(255, 0, 180), width=5)
        label = f"{o['id']} {o['badge']['headline'] if o['badge'] else ''} {o['price']['int'] + ',' + o['price']['cents'] if o['price'] else ''}"
        d.rectangle([r[0] * im.width, r[1] * im.height - 26, r[0] * im.width + 11 * len(label), r[1] * im.height],
                    fill=(255, 0, 180))
        d.text((r[0] * im.width + 4, r[1] * im.height - 22), label, fill="white")
    im.thumbnail((900, 1500))
    im.save(dst)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default="video/public/catalog")
    ap.add_argument("--pages", default=None, help="e.g. 1-12,20")
    ap.add_argument("--debug", default="output/debug", help="where to write offer-overlay previews ('' to skip)")
    ap.add_argument("--profile", choices=sorted(PROFILES), help="font conventions (default: auto-detect)")
    a = ap.parse_args()
    extract(a.pdf, a.out, a.pages, a.debug, a.profile)
