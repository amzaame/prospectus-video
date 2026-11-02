"""Export every page of a flattened PDF and build contact sheets to choose offers from.

Usage:
    python extractor/pages.py catalogue.pdf --out output/pages_<name>
    # -> output/pages_<name>/p001.jpg ... and sheet_1.jpg, sheet_2.jpg (14 pages per sheet, page numbers drawn)
"""
import argparse
from pathlib import Path

try:  # PyMuPDF >= 1.24 is imported as pymupdf; older ones only as fitz
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    thumbs = []
    for i, page in enumerate(doc):
        dst = out / f"p{i + 1:03d}.jpg"
        infos = page.get_image_info(xrefs=True)
        if len(infos) == 1 and infos[0]["xref"]:  # flattened page: the original picture
            dst.write_bytes(doc.extract_image(infos[0]["xref"])["image"])
        else:
            page.get_pixmap(dpi=150).pil_save(dst, quality=88)
        im = Image.open(dst).convert("RGB")
        im.thumbnail((240, 360))
        ImageDraw.Draw(im).text((6, 6), str(i + 1), fill=(255, 0, 180))
        thumbs.append(im)
    for s in range(0, len(thumbs), 14):
        sheet = Image.new("RGB", (240 * 7, 360 * 2), "white")
        for k, im in enumerate(thumbs[s:s + 14]):
            sheet.paste(im, ((k % 7) * 240, (k // 7) * 360))
        sheet.save(out / f"sheet_{s // 14 + 1}.jpg")
    print(f"{len(thumbs)} pages -> {out}")


if __name__ == "__main__":
    main()
