import type {Spot} from './types';

export const FPS = 30;
export const INTRO = 75;       // cover on lifestyle background
export const OFFER = 96;       // one product scene
export const OVERLAP = 14;     // cross-over between scenes
export const OUTRO = 90;       // tagline + app CTA

export const offerStart = (i: number) => INTRO - OVERLAP + i * (OFFER - OVERLAP);
export const outroStart = (n: number) => offerStart(n); // = end of the last offer minus the overlap
export const totalFrames = (spot: Spot) => outroStart(spot.offers.length) + OUTRO;
