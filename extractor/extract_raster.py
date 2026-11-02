"""Extract offers from a *flattened* catalogue PDF (one picture per page, no text layer).

Text comes from macOS Vision OCR, product cut-outs from Vision subject lifting on a cell around
each offer. Output has the same shape as extract.py, so the video template works unchanged.

Usage:
    python extractor/extract_raster.py catalogue.pdf --out video/public/leclerc [--pages 60-66]
"""
import argparse
import json
import re
from pathlib import Path

import fitz
import numpy as np
import Quartz
import Vision
from PIL import Image, ImageDraw

import vision

SKIP = re.compile(r"L'?UNIT|ENSEMBLE|^DONT|PARTICIPATION|PRIX PAY|TICKET|COMPRIS|PILES|FOURNIES|^LE LOT|"
                  r"PRODUIT|PARTENAIRE|^\d+$|AVEC LA CARTE|E\.?LECLERC|LE KG|^SOIT", re.I)
CAISSE = re.compile(r"PRIX PAY", re.I)
TICKET = re.compile(r"TICKET.*COMPRIS|^COMPRIS", re.I)
UNIT = re.compile(r"L'?UNIT|ENSEMBLE|LE LOT|LE KG|LA PI", re.I)


def h(r):
    return r["bbox"][3] - r["bbox"][1]


def upper_ratio(t):
    letters = [c for c in t if c.isalpha()]
    return sum(c.isupper() for c in letters) / max(1, len(letters))


def reocr_price(img, r):
    """Big stylised digits are often misread ('17g', '25g0'): OCR a zoomed crop around the number."""
    W, H = img.size
    x0, y0, x1, y1 = r["bbox"]
    box = (max(0, (x0 - 0.01) * W), max(0, (y0 - 0.01) * H), min(W, (x1 + 0.08) * W), min(H, (y1 + 0.02) * H))
    crop = img.crop(box)
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    tmp = Path(__file__).with_name("_price_crop.png")
    crop.save(tmp)
    toks = vision.ocr(tmp)
    tmp.unlink(missing_ok=True)
    whole = re.sub(r"\s", "", "".join(t["text"] for t in sorted(toks, key=lambda t: t["bbox"][0])))
    m = re.match(r"\D*(\d{1,3})[^\d,.]*[,.]?(\d{2})?", whole)
    cents = None
    for t in toks:
        mm = re.fullmatch(r"[,.]?\s*(\d{2})", t["text"].strip())
        if mm and h(t) < 0.7 * max(h(x) for x in toks):
            cents = mm.group(1)
    return (m.group(1) if m else None), (cents or (m.group(2) if m else None))


def find_prices(img, toks):
    prices = []
    for r in toks:
        if h(r) < 0.022 or not re.match(r"\s*\d", r["text"]):
            continue
        whole = re.sub(r"\s", "", r["text"])
        m = re.match(r"(\d{1,3})", whole)
        if not m:
            continue
        intp, cents = reocr_price(img, r)
        intp = intp or m.group(1)
        if not cents:  # ",90" usually comes as its own token to the right
            for t in toks:
                mm = re.fullmatch(r"[,.]\s*(\d{2})", t["text"].strip())
                if mm and -0.03 < t["bbox"][0] - r["bbox"][2] < 0.06 and r["bbox"][1] - 0.01 < t["bbox"][1] < r["bbox"][3] + 0.01:
                    cents = mm.group(1)
        # label just below the number
        below = [t for t in toks if 0 <= t["bbox"][1] - r["bbox"][3] + 0.012 < 0.035 and abs(t["bbox"][0] - r["bbox"][0]) < 0.06]
        label = " ".join(t["text"] for t in below)
        kind = "caisse" if CAISSE.search(label) else "ticket" if TICKET.search(label) else "regular"
        # ticket label sometimes sits two lines down
        if kind == "regular":
            deeper = [t for t in toks if 0 <= t["bbox"][1] - r["bbox"][3] < 0.06 and abs(t["bbox"][0] - r["bbox"][0]) < 0.06]
            if any(TICKET.search(t["text"]) for t in deeper):
                kind = "ticket"
        unit = next((t["text"] for t in below if UNIT.search(t["text"])), "")
        prices.append(dict(int=intp, cents=cents or "", value=float(f"{intp}.{cents or '00'}"), kind=kind,
                           caption=[unit] if unit else [], bbox=list(r["bbox"]), size=h(r), tok=r))
    return prices


def group_offers(prices):
    """Pair 'PRIX PAYÉ EN CAISSE' with the 'TICKET COMPRIS' price right under it."""
    used, offers = set(), []
    for p in sorted(prices, key=lambda p: (p["bbox"][1], p["bbox"][0])):
        if id(p) in used:
            continue
        used.add(id(p))
        o = dict(price=p, old=None)
        if p["kind"] == "caisse":
            nxt = [q for q in prices if id(q) not in used and abs(q["bbox"][0] - p["bbox"][0]) < 0.06
                   and 0 < q["bbox"][1] - p["bbox"][1] < 0.14]
            if nxt:
                q = min(nxt, key=lambda q: q["bbox"][1])
                used.add(id(q))
                o = dict(price=q, old=p)
        offers.append(o)
    return offers


def find_name(toks, anchor, taken):
    x0, y1 = anchor[0], anchor[3]
    cands = []
    for t in toks:
        if id(t) in taken or SKIP.search(t["text"]) or len(t["text"].strip()) < 4 or upper_ratio(t["text"]) < 0.8:
            continue
        if h(t) > 0.03:
            continue
        dx, dy = t["bbox"][0] - x0, t["bbox"][1] - y1
        if -0.04 < dx < 0.45 and -0.08 < dy < 0.16:
            cands.append((abs(dy) + 0.6 * abs(dx) + (0.05 if dy < 0 else 0), t))
    if not cands:
        return "", [], None
    first = min(cands, key=lambda c: c[0])[1]
    lines, last = [first], first
    for t in sorted(toks, key=lambda t: t["bbox"][1]):  # merge stacked uppercase lines
        if t is last or id(t) in taken:
            continue
        if abs(t["bbox"][0] - first["bbox"][0]) < 0.02 and 0 < t["bbox"][1] - last["bbox"][3] < 0.012 \
                and upper_ratio(t["text"]) > 0.8 and not SKIP.search(t["text"]):
            lines.append(t)
            last = t
    desc = []
    for t in sorted(toks, key=lambda t: t["bbox"][1]):
        if abs(t["bbox"][0] - first["bbox"][0]) < 0.02 and 0 < t["bbox"][1] - last["bbox"][3] < 0.05 \
                and upper_ratio(t["text"]) < 0.6 and len(desc) < 3:
            desc.append(t)
            last = t
    return " ".join(l["text"] for l in lines), [d["text"] for d in desc], lines + desc


# ---------------------------------------------------------------- cut-outs
def cells(anchors, shape=(130, 100)):
    """Voronoi cell of each offer anchor on a coarse grid -> bbox (normalised)."""
    gy, gx = np.mgrid[0:shape[0], 0:shape[1]]
    pts = np.stack([gx / shape[1], gy / shape[0]], -1)
    d = np.stack([np.hypot(pts[..., 0] - ax, (pts[..., 1] - ay) * 1.3) for ax, ay in anchors], 0)
    lab = d.argmin(0)
    out = []
    for i in range(len(anchors)):
        ys, xs = np.where(lab == i)
        out.append([xs.min() / shape[1], ys.min() / shape[0], (xs.max() + 1) / shape[1], (ys.max() + 1) / shape[0]])
    return out


def lift(img_path, crop_box, text_boxes, dst):
    """Subject-lift the crop, dropping instances that are mostly price/label text."""
    full = Image.open(img_path).convert("RGB")
    W, H = full.size
    box = [int(crop_box[0] * W), int(crop_box[1] * H), int(crop_box[2] * W), int(crop_box[3] * H)]
    crop = full.crop(box)
    tmp = Path(dst).with_suffix(".src.png")
    crop.save(tmp)
    req = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(vision._cgimage(tmp), None)
    handler.performRequests_error_([req], None)
    tmp.unlink(missing_ok=True)
    res = req.results()
    if not res:
        return None
    obs = res[0]
    keep = []
    cw, ch = crop.size
    for idx in list(obs.allInstances()):
        iset = Foundation_index_set(idx)
        buf, _ = obs.generateScaledMaskForImageForInstances_fromRequestHandler_error_(iset, handler, None)
        m = pixel_buffer_to_array(buf)
        if m.shape != (ch, cw):
            m = np.array(Image.fromarray((m * 255).astype("uint8")).resize((cw, ch))) / 255.0
        area = (m > 0.5).sum()
        if area < 0.03 * cw * ch:
            continue
        txt = 0
        for tb in text_boxes:
            x0 = int((tb[0] * W) - box[0]); y0 = int((tb[1] * H) - box[1])
            x1 = int((tb[2] * W) - box[0]); y1 = int((tb[3] * H) - box[1])
            x0, y0, x1, y1 = max(0, x0), max(0, y0), min(cw, x1), min(ch, y1)
            if x1 > x0 and y1 > y0:
                txt += (m[y0:y1, x0:x1] > 0.5).sum()
        if txt / area > 0.12:
            continue
        keep.append((area, m))
    if not keep:
        return None
    big = max(a for a, _ in keep)
    alpha = np.zeros((ch, cw))
    for a, m in keep:
        if a > 0.2 * big:
            alpha = np.maximum(alpha, m)
    rgba = np.dstack([np.array(crop), (alpha * 255).astype("uint8")])
    im = Image.fromarray(rgba, "RGBA")
    bb = im.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
    if not bb:
        return None
    im = im.crop(bb)
    im.save(dst)
    region = [(box[0] + bb[0]) / W, (box[1] + bb[1]) / H, (box[0] + bb[2]) / W, (box[1] + bb[3]) / H]
    return im.size, region


def Foundation_index_set(i):
    from Foundation import NSIndexSet
    return NSIndexSet.indexSetWithIndex_(i)


def pixel_buffer_to_array(buf):
    Quartz.CVPixelBufferLockBaseAddress(buf, 0)
    w, hh = Quartz.CVPixelBufferGetWidth(buf), Quartz.CVPixelBufferGetHeight(buf)
    bpr = Quartz.CVPixelBufferGetBytesPerRow(buf)
    raw = Quartz.CVPixelBufferGetBaseAddress(buf).as_buffer(bpr * hh)
    arr = np.frombuffer(raw, dtype=np.float32).reshape(hh, bpr // 4)[:, :w].copy()
    Quartz.CVPixelBufferUnlockBaseAddress(buf, 0)
    return arr


# ---------------------------------------------------------------- main
def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a) - 1, int(b or a)))
    return [p for p in out if p < n]


def extract(pdf, out, pages=None, debug_dir="output/debug"):
    out = Path(out)
    for d in ("pages", "products"):
        (out / d).mkdir(parents=True, exist_ok=True)
    debug = Path(debug_dir) if debug_dir else None
    if debug:
        debug.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    offers, page_meta = [], []
    for pno in parse_pages(pages, doc.page_count):
        page = doc[pno]
        xref = page.get_image_info(xrefs=True)[0]["xref"]
        jpg = out / "pages" / f"p{pno + 1:03d}.jpg"
        jpg.write_bytes(doc.extract_image(xref)["image"])
        img = Image.open(jpg).convert("RGB")
        toks = vision.ocr(jpg)
        page_meta.append(dict(page=pno + 1, image=f"pages/{jpg.name}", width=img.width, height=img.height))

        groups = group_offers(find_prices(img, toks))
        if not groups:
            continue
        taken = {id(g["price"]["tok"]) for g in groups} | {id(g["old"]["tok"]) for g in groups if g["old"]}
        cards = []
        for g in groups:
            anchor = g["price"]["bbox"]
            name, desc, used = find_name(toks, anchor, taken)
            if used:
                taken |= {id(u) for u in used}
            boxes = [g["price"]["bbox"]] + ([g["old"]["bbox"]] if g["old"] else []) + [u["bbox"] for u in (used or [])]
            cards.append(dict(g=g, name=name, desc=desc, boxes=boxes))
        anchors = [((c["g"]["price"]["bbox"][0] + c["g"]["price"]["bbox"][2]) / 2,
                    (c["g"]["price"]["bbox"][1] + c["g"]["price"]["bbox"][3]) / 2) for c in cards]
        text_boxes = [t["bbox"] for t in toks if h(t) > 0.018 or SKIP.search(t["text"])] + \
                     [b for c in cards for b in c["boxes"]]
        for k, (c, cell) in enumerate(zip(cards, cells(anchors))):
            g = c["g"]
            oid = f"p{pno + 1:03d}_{k:02d}"
            image, img_region = None, None
            try:
                r = lift(jpg, cell, text_boxes, out / "products" / f"{oid}.png")
                if r:
                    (w, hh), img_region = r
                    image = dict(src=f"products/{oid}.png", width=w, height=hh)
            except Exception as e:
                print("cut-out failed", oid, e)
            badge = None
            if g["old"]:
                diff = round(g["old"]["value"] - g["price"]["value"], 2)
                if diff > 0:
                    euros, cts = divmod(round(diff * 100), 100)
                    badge = dict(kind="amount", headline=f"{euros}€{cts:02d}" if cts else f"{euros}€",
                                 sub="EN TICKET E.LECLERC AVEC LA CARTE", text="")
            pr = lambda p, label=None: dict(int=p["int"], cents=p["cents"], value=p["value"],
                                             caption=p["caption"], **({"label": label} if label else {}))
            region = [min(b[0] for b in c["boxes"]), min(b[1] for b in c["boxes"]),
                      max(b[2] for b in c["boxes"]), max(b[3] for b in c["boxes"])]
            if img_region:
                region = [min(region[0], img_region[0]), min(region[1], img_region[1]),
                          max(region[2], img_region[2]), max(region[3], img_region[3])]
            offers.append(dict(
                id=oid, page=pno + 1, name=c["name"].title() if c["name"] else "", brand="",
                description=" ".join(c["desc"]), loyalty="", badge=badge,
                price=pr(g["price"], "TICKET E.LECLERC COMPRIS" if g["old"] else None),
                oldPrice=pr(g["old"], "PRIX PAYÉ EN CAISSE") if g["old"] else None,
                image=image, region=[round(v, 4) for v in region],
            ))
        if debug:
            im = img.copy()
            d = ImageDraw.Draw(im)
            for o in offers:
                if o["page"] != pno + 1:
                    continue
                r = [o["region"][0] * im.width, o["region"][1] * im.height, o["region"][2] * im.width, o["region"][3] * im.height]
                d.rectangle(r, outline=(255, 0, 180), width=4)
                d.rectangle([r[0], r[1] - 18, r[0] + 300, r[1]], fill=(255, 0, 180))
                d.text((r[0] + 3, r[1] - 16), f"{o['id']} {o['price']['int']},{o['price']['cents']} {o['name'][:28]}", fill="white")
            im.save(debug / f"p{pno + 1:03d}.png")
        print(pno + 1, len([o for o in offers if o["page"] == pno + 1]), "offers")

    meta = dict(source=Path(pdf).name, pageCount=doc.page_count, validity=[], pages=page_meta)
    fonts = dict(note="PDF aplati (une image par page) : aucune police embarquée, identification visuelle uniquement.")
    (out / "catalog.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    (out / "offers.json").write_text(json.dumps(offers, ensure_ascii=False, indent=2))
    (out / "fonts.json").write_text(json.dumps(fonts, ensure_ascii=False, indent=2))
    print(f"{len(offers)} offers, {sum(1 for o in offers if o['image'])} with cut-outs -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default="video/public/catalog")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--debug", default="output/debug")
    a = ap.parse_args()
    extract(a.pdf, a.out, a.pages, a.debug)
