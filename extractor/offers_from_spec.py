"""Assisted mode: build offers.json from a hand-written (or LLM-written) spec + automatic cut-outs.

For flattened catalogues where OCR heuristics are not reliable enough. Each spec entry gives the
offer text and the product frame on the page (normalised 0..1); the product is lifted with macOS
Vision inside that frame.

Usage:
    python extractor/offers_from_spec.py specs/leclerc.json "catalogue.pdf" --out video/public/leclerc
    python extractor/offers_from_spec.py specs/lidl.json --out video/public/lidl   # pages from "pageImages" URLs
"""
import argparse
import json
from pathlib import Path

import subprocess

import fitz

from extract_raster import lift


def download(url, dst):
    # curl copes with CDNs whose TLS setup the bundled Python ssl rejects
    subprocess.run(["curl", "-sfL", "-A", "Mozilla/5.0", "-o", str(dst), url], check=True)


def remove_white_bg(src, dst, tol=185):
    """Packshots on white: clear the white connected to the image border, keep the whole product
    (subject lifting would only keep the illustration printed on a box)."""
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.open(src).convert("RGBA")
    flat = Image.new("RGB", im.size, (255, 255, 255))
    flat.paste(im, (0, 0), im)
    # whiteness = darkest channel: saturated colours (yellow box) stay, faded reflections go
    r, g, b = flat.split()
    from PIL import ImageChops
    whiteness = ImageChops.darker(ImageChops.darker(r, g), b)
    near_white = whiteness.point(lambda v: 255 if v >= tol else 0)
    w, h = im.size
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if near_white.getpixel((x, y)) == 255:
            ImageDraw.floodfill(near_white, (x, y), 128)
    alpha = near_white.point(lambda v: 0 if v == 128 else 255).filter(ImageFilter.GaussianBlur(1.2))
    flat.putalpha(alpha)
    bb = alpha.point(lambda a: 255 if a > 20 else 0).getbbox()
    flat = flat.crop(bb)
    flat.save(dst)
    return flat.size


def price(s, label=None, caption=None):
    i, _, c = s.partition(",")
    return dict(int=i, cents=c, value=float(f"{i}.{c or '00'}"), caption=caption or [],
                **({"label": label} if label else {}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("pdf", nargs="?", help="source PDF (not needed when the spec lists pageImages)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    out = Path(a.out)
    (out / "pages").mkdir(parents=True, exist_ok=True)
    (out / "products").mkdir(parents=True, exist_ok=True)
    page_images = spec.get("pageImages", {})  # online flyers: page number -> image URL
    doc = fitz.open(a.pdf) if a.pdf else None

    pages = {}
    for o in spec["offers"]:
        pages.setdefault(o["page"], None)
    pages.setdefault(1, None)
    page_meta = []
    for pno in sorted(pages):
        jpg = out / "pages" / f"p{pno:03d}.jpg"
        if str(pno) in page_images:
            download(page_images[str(pno)], jpg)
            from PIL import Image
            w, h = Image.open(jpg).size
            page_meta.append(dict(page=pno, image=f"pages/{jpg.name}", width=w, height=h))
            continue
        page = doc[pno - 1]
        infos = page.get_image_info(xrefs=True)
        if len(infos) == 1 and infos[0]["xref"]:  # flattened page: keep the original picture
            jpg.write_bytes(doc.extract_image(infos[0]["xref"])["image"])
        else:
            page.get_pixmap(dpi=200).pil_save(jpg, quality=88)
        from PIL import Image
        w, h = Image.open(jpg).size
        page_meta.append(dict(page=pno, image=f"pages/{jpg.name}", width=w, height=h))

    offers = []
    for k, o in enumerate(spec["offers"]):
        oid = o.get("id") or f"p{o['page']:03d}_{k:02d}"
        jpg = out / "pages" / f"p{o['page']:03d}.jpg"
        image = None
        if o.get("imageUrl"):  # HD packshot (e.g. the retailer's product page) beats a crop of the page
            src = out / "products" / f"{oid}.download"
            download(o["imageUrl"], src)
            # "white": clear the white backdrop (keeps whole boxes); "vision": subject lifting (keeps glass/silver)
            if o.get("cutout", "white") == "vision":
                r = lift(src, [0, 0, 1, 1], [], out / "products" / f"{oid}.png")
            else:
                r = (remove_white_bg(src, out / "products" / f"{oid}.png", o.get("whiteTol", 185)), None)
            src.unlink()
        else:
            r = lift(jpg, o["productBox"], [], out / "products" / f"{oid}.png")
        if r:
            (w, h), _ = r
            image = dict(src=f"products/{oid}.png", width=w, height=h)
        else:
            print("no subject found for", oid)
        ticket = o.get("ticket")  # Leclerc style: paid price, then price with loyalty ticket
        badge = o.get("badge")
        if ticket and not badge:
            badge = dict(kind="amount", headline=ticket["amount"], sub=ticket.get("sub", "AVEC LA CARTE"), text="")
        offers.append(dict(
            id=oid, page=o["page"], name=o.get("name", ""), brand=o.get("brand", ""),
            description=o.get("description", ""), loyalty="", badge=badge,
            price=price(ticket["net"] if ticket else o["price"], ticket and ticket.get("netLabel"), o.get("caption")),
            oldPrice=price(ticket["paid"], ticket.get("paidLabel")) if ticket else
            (price(o["oldPrice"]) if o.get("oldPrice") else None),
            image=image, region=o.get("region") or o["productBox"],
        ))
        print(oid, offers[-1]["brand"] or offers[-1]["name"], "cut-out" if image else "NO cut-out")

    meta = dict(source=spec.get("source") or Path(a.pdf).name, pageCount=doc.page_count if doc else len(page_meta), validity=spec.get("validity", []), pages=page_meta)
    (out / "catalog.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    (out / "offers.json").write_text(json.dumps(offers, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
