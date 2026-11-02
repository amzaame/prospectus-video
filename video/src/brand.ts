import {createContext, useContext} from 'react';
import {FONTS} from './fonts';

export type BrandStyle = {
  fonts: {heavy: string; cond: string; price?: string};
  /** background decoration */
  pattern: 'burst' | 'sparkle' | 'pixels' | 'none';
  /** promo sticker next to the product */
  sticker: 'burst' | 'ticket' | 'tag';
  /** stack: 59€ over 90 (Carrefour) · comma: 59€,90 (Leclerc) · inline: 44.99 (Lidl) */
  priceStyle: 'stack' | 'comma' | 'inline';
  priceColor?: string;
  /** old price strike: diagonal slash or straight line-through */
  strike?: 'diagonal' | 'straight';
  strikeColor?: string;
  /** caption band under the 'tag' sticker */
  tagSub?: {bg: string; fg: string};
  /** promo headline in the text column drawn inside a coloured box */
  badgeBox?: {bg: string; fg: string};
  /** tilt of the date pills, degrees */
  tilt: number;
  datePill: {bg: string; fg: string};
  /** second background colour for the gradient */
  bg2?: string;
  /** outro logo height relative to its white tile (square logos need more) */
  logoScale?: number;
  stickerTitle?: string;
  stickerFooter?: string;
};

export const STYLES: Record<string, BrandStyle> = {
  carrefour: {
    fonts: FONTS.proxima,
    pattern: 'burst',
    sticker: 'burst',
    priceStyle: 'stack',
    tilt: -2,
    datePill: {bg: '#ffffff', fg: ''},
  },
  // tokens from www.e.leclerc: --color-brand-primary #06c, --color-blue-500 #0f1e6b, --color-orange-300 #f63
  leclerc: {
    fonts: FONTS.leclerc,
    pattern: 'sparkle',
    sticker: 'ticket',
    priceStyle: 'comma',
    tilt: 0,
    datePill: {bg: '#ff6633', fg: '#ffffff'},
    bg2: '#0f1e6b',
    stickerTitle: 'Ticket E.Leclerc',
    stickerFooter: 'avec la Carte',
  },
  // lidl.fr: blue rgb(0,80,170); catalogue yellow #fff000 prices, red #e60a14 discount boxes
  lidl: {
    fonts: FONTS.lidl,
    pattern: 'none',
    sticker: 'tag',
    priceStyle: 'inline',
    priceColor: '#fff000',
    strike: 'straight',
    badgeBox: {bg: '#e60a14', fg: '#ffffff'},
    tilt: 0,
    datePill: {bg: '#e60a14', fg: '#ffffff'},
    bg2: '#003f8a',
    logoScale: 0.82,
    tagSub: {bg: '#fff000', fg: '#0050aa'},
  },
  // auchan.fr red rgb(224,0,26); catalogue red #ed1c24, Waaoh! green #128f44, "25 jours" pixel motif
  auchan: {
    fonts: FONTS.auchan,
    pattern: 'pixels',
    sticker: 'tag',
    priceStyle: 'stack',
    priceColor: '#ffffff',
    strike: 'diagonal',
    strikeColor: '#262626',
    badgeBox: {bg: '#ffffff', fg: '#e0001a'},
    tagSub: {bg: '#128f44', fg: '#ffffff'},
    tilt: 0,
    datePill: {bg: '#ffffff', fg: '#e0001a'},
    bg2: '#a80014',
  },
};

export const BrandContext = createContext<BrandStyle>(STYLES.carrefour);
export const useBrand = () => useContext(BrandContext);
