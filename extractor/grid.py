"""Draw a 5% grid on page images so product frames can be read off as normalised boxes.

Usage:
    python extractor/grid.py video/public/<catalogue>/pages/p011.jpg [more pages...] --out output/grids
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default="output/grids")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for src in a.images:
        im = Image.open(src).convert("RGB")
        d = ImageDraw.Draw(im)
        for i in range(1, 20):
            x, y = im.width * i / 20, im.height * i / 20
            d.line([x, 0, x, im.height], fill=(255, 0, 255), width=2)
            d.line([0, y, im.width, y], fill=(255, 0, 255), width=2)
            d.text((x + 4, 4), f"{i * 5}", fill=(255, 0, 255))
            d.text((4, y + 4), f"{i * 5}", fill=(255, 0, 255))
        im.thumbnail((900, 1300))
        dst = out / (Path(src).stem + "_grid.jpg")
        im.save(dst)
        print(dst)


if __name__ == "__main__":
    main()
