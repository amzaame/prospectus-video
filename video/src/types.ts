export type PriceT = {int: string; cents: string; value: number; caption: string[]; label?: string};

export type Offer = {
  id: string;
  page: number;
  name: string;
  brand: string;
  description: string;
  loyalty: string;
  badge: null | {text: string; kind: 'percent' | 'amount' | 'other'; headline: string; sub: string};
  price: PriceT | null;
  oldPrice: PriceT | null;
  image: null | {src: string; width: number; height: number};
  /** offer bounding box on its page, normalised 0..1 */
  region: [number, number, number, number];
  pageImage: string;
  pageAspect: number;
};

export type Spot = {
  cover: string;
  coverAspect: number;
  dates: string[];
  theme: {bg: string; accent: string; stickerText?: string; style?: 'carrefour' | 'leclerc' | 'lidl' | 'auchan' | 'systemeu'};
  logo: string | null;
  tagline: string[];
  cta: string[];
  legal: string;
  offers: Offer[];
};
