import {loadFont as loadMontserrat} from '@remotion/google-fonts/Montserrat';
import {loadFont as loadBarlow} from '@remotion/google-fonts/BarlowCondensed';
import {loadFont as loadRoboto} from '@remotion/google-fonts/Roboto';
import {loadFont as loadRobotoCondensed} from '@remotion/google-fonts/RobotoCondensed';
import {loadFont as loadFira} from '@remotion/google-fonts/FiraSans';
import {loadFont as loadFiraCond} from '@remotion/google-fonts/FiraSansCondensed';
import {loadFont as loadFiraXCond} from '@remotion/google-fonts/FiraSansExtraCondensed';
import {loadFont as loadLexend} from '@remotion/google-fonts/Lexend';
import {loadFont as loadFigtree} from '@remotion/google-fonts/Figtree';
import {loadFont as loadMulish} from '@remotion/google-fonts/Mulish';
import {loadFont as loadSatisfy} from '@remotion/google-fonts/Satisfy';

const latin = {subsets: ['latin', 'latin-ext'] as ('latin' | 'latin-ext')[]};
const montserrat = loadMontserrat('normal', {weights: ['600', '700', '800', '900'], ...latin});
const barlow = loadBarlow('normal', {weights: ['300', '500', '600', '700'], ...latin});
const roboto = loadRoboto('normal', {weights: ['400', '500', '700', '900'], ...latin});
const robotoCond = loadRobotoCondensed('normal', {weights: ['700', '800', '900'], ...latin});
const fira = loadFira('normal', {weights: ['600', '700', '800', '900'], ...latin});
const firaCond = loadFiraCond('normal', {weights: ['400', '500', '600'], ...latin});
const firaXCond = loadFiraXCond('normal', {weights: ['700', '800', '900'], ...latin});
const lexend = loadLexend('normal', {weights: ['600', '700', '800', '900'], ...latin});
const figtree = loadFigtree('normal', {weights: ['500', '600', '700'], ...latin});
const mulish = loadMulish('normal', {weights: ['600', '700', '800', '900'], ...latin});
const satisfy = loadSatisfy('normal', {weights: ['400'], subsets: ['latin']});

// Font pairs per brand. Commercial brand fonts are listed first and used when installed locally;
// the Google fonts are the closest free substitutes.
export const FONTS: Record<string, {heavy: string; cond: string; price?: string; script?: string}> = {
  // Carrefour catalogue: Proxima Nova Black/Bold + Proxima Nova Condensed
  proxima: {
    heavy: `"Proxima Nova", ${montserrat.fontFamily}, sans-serif`,
    cond: `"Proxima Nova Condensed", ${barlow.fontFamily}, sans-serif`,
  },
  // E.Leclerc: site in Roboto, catalogue prices/titles in a heavy condensed grotesk
  leclerc: {
    heavy: `${robotoCond.fontFamily}, sans-serif`,
    cond: `${roboto.fontFamily}, sans-serif`,
  },
  // Lidl: LidlFontPro / LidlFontCondPro / LidlFontPrice (proprietary) -> Fira Sans family
  lidl: {
    heavy: `LidlFontPro, ${fira.fontFamily}, sans-serif`,
    cond: `LidlFontCondPro, ${firaCond.fontFamily}, sans-serif`,
    price: `LidlFontPrice, ${firaXCond.fontFamily}, sans-serif`,
  },
  // Auchan: Sana Sans Alt Exp (titles, prices) + Sana Sans Alt (text) -> Lexend + Figtree
  auchan: {
    heavy: `"Sana Sans Alt Exp", ${lexend.fontFamily}, sans-serif`,
    cond: `"Sana Sans Alt", ${figtree.fontFamily}, sans-serif`,
  },
  // Système U: coursesu.com loads Mulish (text) and Satisfy (the handwritten "J'ai tellement plus à y gagner")
  systemeu: {
    heavy: `${mulish.fontFamily}, sans-serif`,
    cond: `${mulish.fontFamily}, sans-serif`,
    script: `${satisfy.fontFamily}, cursive`,
  },
};
