# Reference

## Spec (routes B and C)

`specs/<name>.json`, read by `extractor/offers_from_spec.py`. Worked examples ship in `specs/examples/`
(`leclerc.json`: flattened PDF with retailer packshots; `lidl.json`: online flyer).

```json
{
  "validity": ["DU 20 OCTOBRE AU 5 DÉCEMBRE 2026"],
  "source": "https://…",                         // optional, for the record
  "pageImages": {"1": "https://…", "6": "https://…"},  // route C: page number -> image URL (no PDF argument)
  "offers": [
    {
      "id": "robot", "page": 6,
      "name": "Robot multifonction 600 W",         // descriptive line (condensed font)
      "brand": "SILVERCREST",                      // heavy line under it
      "price": "44,99", "oldPrice": "59,99",       // old price is struck through
      "caption": ["Uniquement en ligne sur lidl.fr"],
      "badge": {"kind": "percent", "headline": "-25%", "sub": "UNIQUEMENT EN LIGNE", "text": ""},
      "productBox": [0.25, 0.12, 0.80, 0.50],      // product on the page, fractions x0,y0,x1,y1
      "region": [0.03, 0.06, 0.97, 0.55],          // whole offer on the page (yellow frame in the video)
      "imageUrl": "https://…",                     // optional HD packshot, replaces the page crop
      "cutout": "vision", "whiteTol": 185          // for imageUrl: "white" (default) or "vision"
    }
  ]
}
```

Loyalty "ticket" offers (paid price, then price after the loyalty credit; not struck through):

```json
"ticket": {"paid": "27,90", "net": "23,10", "amount": "4€80", "sub": "EN TICKET E.LECLERC",
           "paidLabel": "PRIX PAYÉ EN CAISSE", "netLabel": "TICKET E.LECLERC COMPRIS*"}
```

Page 1 is always fetched (cover for the intro). `productBox` should avoid price tags and badges that overlap
the product: Vision keeps whatever looks like the subject. `whiteTol` (0–255) is the darkest-channel level
counted as background: 185 removes faded reflections under boxes; 240 keeps light grey and silver parts.

## Overrides (route A)

`specs/<name>_overrides.json`, passed to `make_spot.py --overrides`. Keys are offer ids from `offers.json`;
each value replaces those fields of the offer. Prices are objects here:

```json
{
  "p062_04": {
    "name": "TV LED 85\" / 214 cm", "brand": "SAMSUNG",
    "oldPrice": {"int": "999", "cents": "", "value": 999.0, "caption": []},
    "price": {"int": "849", "cents": "", "value": 849.0, "caption": ["Dont 17€ d'éco-participation"]},
    "badge": {"kind": "amount", "headline": "150€", "sub": "DE REMISE IMMÉDIATE", "text": ""}
  },
  "p054_00": {"cutout": "vision"}
}
```

`"cutout": "vision"` re-cuts the offer's current image with Apple Vision (for a photo with a background).
A price `label` (`"label": "PRIX PAYÉ EN CAISSE"`) shows the label instead of striking the old price.

## New font profile (route A, unknown retailer)

`extract.py` reads offers from font conventions held in `PROFILES`. Dump a page with
`extractor/probe.py <pdf> --spans <page>` and find:

- `title`: regex on the font of product titles (uppercase/bold lines next to the price), with `title_size` (min, max) in points;
- `desc`: font of the description lines under the title; `loyalty`: font of loyalty notes (`"^$"` if none);
- `strike`: how the old price is crossed — a glyph in a dedicated font (Auchan `PrixBarre…`, Carrefour red `x` in font `Carrefour`).

Add the profile, add its detection to `extract()` (font name present in the first pages), run with
`--profile <name>`, then look at the debug overlays. Prices (big digits + `€` + cents) and white promo
badges are found without a profile.

## New brand style

1. **Colours.** On the retailer's site, read computed colours and CSS variables in the browser
   (`getComputedStyle`, `:root` custom properties, `document.fonts`). In the PDF, the biggest fills:
   `page.get_drawings()` fill colours weighted by area.
2. **Fonts.** Note the brand fonts (`document.fonts` on the site, `probe.py` on the PDF), then choose the
   closest Google fonts available in `@remotion/google-fonts` and add a pair to `FONTS` in
   `video/src/fonts.ts`: `heavy` (prices, badges, brand names, outro), `cond` (names, captions), optional
   `price`. List the brand font first in the CSS stack so it is used where the person has it installed.
3. **Preset.** Add an entry to `STYLES` in `video/src/brand.ts` and its name to `style` in `video/src/types.ts`:

| field | values |
|---|---|
| `pattern` | `burst` (turning starbursts), `sparkle` (twinkling stars), `pixels` (drifting squares), `none` |
| `sticker` | `burst` (star with the badge or price), `ticket` (round loyalty sticker with curved texts), `tag` (box + caption band) |
| `priceStyle` | `stack` (44€ over 99), `comma` (59€,90), `inline` (44.99) |
| `priceColor`, `strike` (`diagonal`/`straight`), `strikeColor` | price look |
| `badgeBox` `{bg, fg}` | promo headline drawn in a box in the text column |
| `tagSub` `{bg, fg}` | band under the `tag` sticker |
| `datePill` `{bg, fg}`, `tilt` | date pills |
| `bg2` | second colour of the background gradient |
| `logoScale` | outro logo height in its tile (0.5 for wide logos, ~0.8 for square ones) |
| `stickerTitle`, `stickerFooter` | curved texts of the `ticket` sticker |

A new motif or sticker shape goes in `video/src/components.tsx` (`Background`, `Sticker`).

## Timing

`video/src/timing.ts`: intro 75 frames, 96 per offer with 14 of overlap, outro 90, at 30 fps.
Offer k (from 0) is on screen from frame `61 + 82k`; its text and prices are complete about 50 frames later.
Layout boxes (text column, product, page) are in `useLayout()` in `components.tsx`, for 16:9 and 9:16.

## Troubleshooting

- Remotion cannot download its browser: `video/remotion.config.ts` uses Google Chrome when it is installed.
- Python cannot fetch a URL (TLS handshake error): downloads in `offers_from_spec.py` go through `curl` already; use `curl` for anything else.
- A cut-out keeps a badge or a price tag: shrink `productBox`, or use a retailer packshot.
- A product looks transparent in places: the white removal took light parts — use `"cutout": "vision"` or raise `whiteTol`.
