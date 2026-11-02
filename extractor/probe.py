"""Tell what kind of catalogue a PDF is, and how to extract it.

Usage:
    python extractor/probe.py catalogue.pdf              # summary + suggested route
    python extractor/probe.py catalogue.pdf --spans 9    # text spans and images of page 9 (to write a new profile)
"""
import argparse
import collections
import re

import fitz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--spans", type=int, help="dump the spans and images of this page (1-based)")
    a = ap.parse_args()
    doc = fitz.open(a.pdf)

    if a.spans:
        page = doc[a.spans - 1]
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    if s["text"].strip():
                        print([round(v) for v in s["bbox"]], round(s["size"], 1), s["font"].split("+")[-1],
                              f"#{s['color']:06x}", repr(s["text"][:60]))
        for i in page.get_image_info(xrefs=True):
            if i["xref"]:
                smask = bool(doc.extract_image(i["xref"]).get("smask"))
                print("IMG", [round(v) for v in i["bbox"]], i["width"], i["height"], "alpha" if smask else "opaque")
        return

    chars, images, alpha = 0, 0, 0
    fonts = collections.Counter()
    for p in doc:
        chars += len(p.get_text())
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    fonts[s["font"].split("+")[-1]] += len(s["text"])
        for i in p.get_image_info(xrefs=True):
            if i["xref"]:
                images += 1
                alpha += bool(doc.extract_image(i["xref"]).get("smask"))
    print(f"pages: {doc.page_count}  size: {doc[0].rect.width:.0f}x{doc[0].rect.height:.0f} pt  "
          f"creator: {doc.metadata.get('creator')}")
    print(f"text chars: {chars}  images: {images}  with alpha (native cut-outs): {alpha}")
    print("fonts:", ", ".join(f"{f} ({n})" for f, n in fonts.most_common(12)) or "none")

    names = " ".join(fonts)
    if chars < 50 * doc.page_count:
        route = "flattened (one picture per page): read the pages yourself, write a spec, run offers_from_spec.py"
    elif "SanaSans" in names:
        route = "vector, profile auchan: run extract.py"
    elif re.search(r"ProximaNova", names):
        route = "vector, profile carrefour: run extract.py"
    else:
        route = ("vector, unknown fonts: dump a page with --spans, add a profile to PROFILES in extract.py "
                 "(title / description fonts, strike glyph), then run extract.py --profile <name>")
    print("route:", route)


if __name__ == "__main__":
    main()
