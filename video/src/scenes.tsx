import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ease, Price, Reveal, Sticker, useEnter, useLayout} from './components';
import {useBrand} from './brand';
import {INTRO, OFFER, OUTRO, OVERLAP} from './timing';
import type {Offer, Spot} from './types';

/* ------------------------------------------------------------------ intro */
export const Intro: React.FC<{spot: Spot}> = ({spot}) => {
  const frame = useCurrentFrame();
  const L = useLayout();
  const enter = useEnter(4, {damping: 14, mass: 0.8});
  const exit = interpolate(frame, [INTRO - OVERLAP - 6, INTRO], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: ease,
  });
  const coverH = L.height * (L.portrait ? 0.55 : 0.72);
  const coverW = coverH * spot.coverAspect;
  // the cover flies towards the spot where the pages live in the offer scenes
  const tx = exit * (L.page.x * L.unit + coverW / 2 - L.width / 2);
  return (
    <AbsoluteFill>
      {/* blurred cover stands in for the lifestyle shot, then reveals the brand background */}
      <AbsoluteFill style={{overflow: 'hidden', opacity: 1 - exit}}>
        <Img
          src={staticFile(spot.cover)}
          style={{
            position: 'absolute',
            width: '120%',
            left: '-10%',
            top: '-30%',
            filter: 'blur(28px) saturate(1.2)',
            transform: `scale(${1.15 - frame * 0.002})`,
          }}
        />
        <AbsoluteFill style={{background: 'rgba(0,0,0,0.25)'}} />
      </AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: L.width / 2 - coverW / 2,
          top: L.height / 2 - coverH / 2,
          width: coverW,
          height: coverH,
          transform: `translateX(${tx}px) perspective(1600px) rotateY(${(1 - enter) * -35 + exit * 10}deg) rotate(${
            (1 - enter) * -8 + 3 * exit
          }deg) scale(${0.4 + enter * 0.6 + exit * 0.25})`,
          boxShadow: '0 40px 80px rgba(0,0,0,0.45)',
          opacity: interpolate(enter, [0, 0.2], [0, 1]) * (1 - interpolate(exit, [0.7, 1], [0, 1])),
        }}
      >
        <Img src={staticFile(spot.cover)} style={{width: '100%', height: '100%'}} />
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ offer */
export const OfferScene: React.FC<{offer: Offer; spot: Spot; index: number}> = ({offer, spot, index}) => {
  const frame = useCurrentFrame();
  const B = useBrand();
  const {fps} = useVideoConfig();
  const L = useLayout();
  const u = L.unit;
  const accent = spot.theme.accent;

  const exit = interpolate(frame, [OFFER - OVERLAP, OFFER], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: ease,
  });

  // --- catalogue page (right) : slides in, then turns away like a page on exit
  const pageIn = useEnter(0, {damping: 18, mass: 0.9});
  const pageH = Math.min(L.page.h, (L.portrait ? 520 : 690) / offer.pageAspect) * u; // wide pages: cap the width
  const pageW = pageH * offer.pageAspect;
  const [rx0, ry0, rx1, ry1] = offer.region;
  const ring = useEnter(26);

  // --- product (centre)
  const prodIn = useEnter(8, {damping: 11, mass: 0.9, stiffness: 120});
  const float = Math.sin((frame + index * 20) / 16);
  const box = L.product;
  const img = offer.image;
  const wide = img && img.width > img.height * 1.2 ? 1.3 : 1; // landscape packshots may use more width
  const fit = img ? Math.min((box.w * u * wide) / img.width, (box.h * u) / img.height) : 1;
  const pw = img ? img.width * fit : 0;
  const ph = img ? img.height * fit : 0;

  // --- sticker
  const stickIn = useEnter(22, {damping: 10, stiffness: 140});
  const stickerSize = (L.portrait ? 280 : 240) * u;
  // the ticket sticker only makes sense for a loyalty amount; the burst repeats the price otherwise
  const stickerText =
    offer.badge?.headline || (offer.price && B.sticker === 'burst' ? `${offer.price.int},${offer.price.cents}€` : '');

  // --- prices
  const strike = interpolate(frame, [34, 46], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  const priceIn = useEnter(40, {damping: 12, stiffness: 150});

  const textOut = {transform: `translateX(${-exit * 80 * u}px)`, opacity: 1 - exit};
  const fsName = (L.portrait ? 50 : 50) * u;

  return (
    <AbsoluteFill>
      {/* page */}
      <div
        style={{
          position: 'absolute',
          left: L.page.x * u,
          top: L.page.y * u,
          width: pageW,
          height: pageH,
          transformOrigin: '0% 50%',
          transform: `translateX(${(1 - pageIn) * (L.width - L.page.x * u + 80)}px) perspective(2200px) rotateY(${
            -exit * 75
          }deg) rotate(${L.page.rot * (1 - exit * 0.5)}deg)`,
          boxShadow: '0 30px 70px rgba(0,0,0,0.4)',
          background: 'white',
        }}
      >
        <Img src={staticFile(offer.pageImage)} style={{width: '100%', height: '100%'}} />
        <svg width={pageW} height={pageH} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
          <rect
            x={rx0 * pageW - 6}
            y={ry0 * pageH - 6}
            width={(rx1 - rx0) * pageW + 12}
            height={(ry1 - ry0) * pageH + 12}
            rx={10}
            fill="none"
            stroke={accent}
            strokeWidth={6 * u}
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={100 - ring * 100}
            opacity={1 - exit}
          />
        </svg>
        {/* subtle shade over the rest of the page so the offer stands out */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0,0,0,0.28)',
            clipPath: `polygon(0 0,100% 0,100% 100%,0 100%,0 ${ry0 * 100}%,${rx0 * 100}% ${ry0 * 100}%,${rx0 * 100}% ${
              ry1 * 100
            }%,${rx1 * 100}% ${ry1 * 100}%,${rx1 * 100}% ${ry0 * 100}%,0 ${ry0 * 100}%)`,
            opacity: ring * (1 - exit),
          }}
        />
      </div>

      {/* product */}
      {img && (
        <div
          style={{
            position: 'absolute',
            left: box.x * u + (box.w * u - pw) / 2,
            top: box.y * u + (box.h * u - ph) / 2,
            width: pw,
            height: ph,
            transform: `translate(${-exit * 160 * u}px, ${(1 - prodIn) * 140 * u + float * 8 * u}px) scale(${
              0.55 + prodIn * 0.45 - exit * 0.2
            }) rotate(${(1 - prodIn) * -10 + float * 1.2}deg)`,
            opacity: interpolate(prodIn, [0, 0.15], [0, 1]) * (1 - exit),
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: '-15%',
              background: 'radial-gradient(closest-side, rgba(255,255,255,0.35), rgba(255,255,255,0))',
            }}
          />
          <Img
            src={staticFile(img.src)}
            style={{width: '100%', height: '100%', filter: 'drop-shadow(0 30px 30px rgba(0,0,0,0.35))'}}
          />
        </div>
      )}
      {!img && (() => {
        // no cut-out in the PDF (rectangular photo): show the offer zone of the page as a photo card
        const rw = rx1 - rx0;
        const rh = (ry1 - ry0) / offer.pageAspect;
        const k = Math.min((box.w * u * 0.95) / rw, (box.h * u * 0.8) / rh);
        const cw = rw * k;
        const ch = rh * k;
        const zoom = 1 + frame * 0.0012;
        return (
          <div
            style={{
              position: 'absolute',
              left: box.x * u + (box.w * u - cw) / 2,
              top: box.y * u + (box.h * u - ch) / 2,
              width: cw,
              height: ch,
              overflow: 'hidden',
              borderRadius: 24 * u,
              border: `${8 * u}px solid white`,
              boxShadow: '0 30px 60px rgba(0,0,0,0.4)',
              transform: `translate(${-exit * 160 * u}px, ${(1 - prodIn) * 140 * u + float * 6 * u}px) scale(${
                0.55 + prodIn * 0.45 - exit * 0.2
              }) rotate(${(1 - prodIn) * -10 + float * 0.8 - 2}deg)`,
              opacity: interpolate(prodIn, [0, 0.15], [0, 1]) * (1 - exit),
            }}
          >
            <Img
              src={staticFile(offer.pageImage)}
              style={{
                position: 'absolute',
                width: k,
                height: k / offer.pageAspect,
                left: -rx0 * k,
                top: -ry0 * (k / offer.pageAspect),
                transformOrigin: `${((rx0 + rx1) / 2) * 100}% ${((ry0 + ry1) / 2) * 100}%`,
                transform: `scale(${zoom})`,
              }}
            />
          </div>
        );
      })()}

      {/* sticker */}
      {stickerText && (
        <div
          style={{
            position: 'absolute',
            ...(B.stickerAt === 'bottom' && img
              ? {
                  // lower-left corner of the product: pack logos are usually at the top
                  left: Math.max(30 * u, box.x * u + (box.w * u - pw) / 2 - stickerSize * 0.35), // stay on screen
                  top: box.y * u + (box.h * u + ph) / 2 - stickerSize * 0.85,
                }
              : {left: box.x * u - (L.portrait ? 0 : 40 * u), top: box.y * u + (L.portrait ? -40 : 60) * u}),
            transform: `scale(${stickIn * (1 - exit)}) rotate(${(1 - stickIn) * -120}deg)`,
          }}
        >
          <Sticker
            text={stickerText}
            sub={offer.badge?.sub}
            color={accent}
            textColor={spot.theme.stickerText ?? '#d0021b'}
            size={stickerSize}
          />
        </div>
      )}

      {/* text column */}
      <div
        style={{
          position: 'absolute',
          left: L.text.x * u,
          top: L.text.y * u,
          width: L.text.w * u,
          color: 'white',
          ...textOut,
        }}
      >
        <Reveal delay={6}>
          <div style={{fontFamily: B.fonts.cond, fontWeight: 600, fontSize: fsName, lineHeight: 1.02}}>{offer.name}</div>
        </Reveal>
        {offer.brand && (
          <Reveal delay={10}>
            <div style={{fontFamily: B.fonts.heavy, fontWeight: 900, fontSize: fsName * 0.95, lineHeight: 1.05}}>
              {offer.brand}
            </div>
          </Reveal>
        )}
        {offer.badge && (
          <div style={{marginTop: 22 * u}}>
            <Reveal delay={16}>
              <div
                style={{
                  fontFamily: B.fonts.heavy,
                  fontWeight: 900,
                  fontSize: 110 * u,
                  lineHeight: 0.95,
                  letterSpacing: -3 * u,
                  ...(B.badgeBox && {
                    display: 'inline-block',
                    background: B.badgeBox.bg,
                    color: B.badgeBox.fg,
                    fontFamily: B.fonts.price ?? B.fonts.heavy,
                    padding: `${6 * u}px ${18 * u}px`,
                  }),
                }}
              >
                {offer.badge.headline}
              </div>
            </Reveal>
            <Reveal delay={20}>
              <div style={{fontFamily: B.fonts.heavy, fontWeight: 900, fontSize: 36 * u, lineHeight: 1.05, maxWidth: 380 * u}}>
                {offer.badge.sub}
              </div>
            </Reveal>
          </div>
        )}
        {offer.oldPrice && (
          <div style={{marginTop: 30 * u, opacity: useEnter(28)}}>
            {/* a labelled old price ("PRIX PAYÉ EN CAISSE") is still paid, so it is not struck through */}
            <Price price={offer.oldPrice} size={72 * u} struck={offer.oldPrice.label ? undefined : strike} />
            {offer.oldPrice.label && (
              <div style={{fontFamily: B.fonts.heavy, fontWeight: 800, fontSize: 24 * u, marginTop: 6 * u}}>{offer.oldPrice.label}</div>
            )}
            {offer.oldPrice.caption[0] && (
              <div style={{fontFamily: B.fonts.cond, fontSize: 24 * u, marginTop: 6 * u}}>{offer.oldPrice.caption.join(' · ')}</div>
            )}
            <div style={{height: 2, background: 'rgba(255,255,255,0.35)', width: 320 * u, marginTop: 18 * u}} />
          </div>
        )}
        {offer.price && (
          <div
            style={{
              marginTop: 22 * u,
              transformOrigin: '0% 100%',
              transform: `scale(${priceIn})`,
              opacity: interpolate(priceIn, [0, 0.2], [0, 1]),
            }}
          >
            <Price price={offer.price} size={(L.portrait ? 170 : 160) * u} />
            {offer.price.label && (
              <div style={{fontFamily: B.fonts.heavy, fontWeight: 800, fontSize: 26 * u, marginTop: 8 * u, color: spot.theme.accent}}>
                {offer.price.label}
              </div>
            )}
            {offer.price.caption.length > 0 && (
              <div style={{fontFamily: B.fonts.cond, fontSize: 24 * u, marginTop: 8 * u, opacity: 0.9}}>
                {offer.price.caption.slice(0, 2).join(' · ')}
              </div>
            )}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ outro */
export const Outro: React.FC<{spot: Spot}> = ({spot}) => {
  const frame = useCurrentFrame();
  const B = useBrand();
  const L = useLayout();
  const u = L.unit;
  const swap = 46;
  const a = useEnter(14, {damping: 14});
  const b = useEnter(swap, {damping: 14});
  const out1 = interpolate(frame, [swap - 8, swap], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fade = interpolate(frame, [OUTRO - 10, OUTRO], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const tile = 130 * u;
  // text block sized on its longest line (both messages share the slot)
  const fs = (L.portrait ? 64 : 58) * u;
  const textW = Math.min(L.width * 0.9, Math.max(...[...spot.tagline, ...spot.cta].map((t) => t.length)) * fs * 0.68);
  // a brand with a script font (Système U) writes its slogan by hand, as on the catalogue
  const lines = (txt: string[], p: number, o: number, script = false) => (
    <div style={{position: 'absolute', opacity: o, right: 0, left: L.portrait ? 0 : undefined, textAlign: L.portrait ? 'center' : 'right'}}>
      {txt.map((t, i) => (
        <div key={i} style={{overflow: 'hidden', paddingBottom: script ? fs * 0.15 : 0}}>
          <div
            style={{
              transform: `translateY(${(1 - p) * 110}%)`,
              fontFamily: script ? B.fonts.script : B.fonts.heavy,
              fontWeight: script ? 400 : 900,
              fontSize: (L.portrait ? Math.min(fs, textW / (Math.max(...txt.map((t) => t.length)) * 0.68)) : fs) * (script ? 1.25 : 1),
              lineHeight: script ? 1.1 : 1.05,
              color: 'white',
              whiteSpace: 'nowrap',
            }}
          >
            {t}
          </div>
        </div>
      ))}
    </div>
  );
  const logoTile = (
    <div
      style={{
        height: tile,
        padding: `0 ${34 * u}px`,
        background: 'white',
        borderRadius: 26 * u,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        transform: `scale(${a}) rotate(${(1 - a) * 90}deg)`,
        boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
      }}
    >
      {spot.logo && <Img src={staticFile(spot.logo)} style={{height: tile * (B.logoScale ?? 0.5)}} />}
    </div>
  );
  return (
    <AbsoluteFill style={{opacity: 1 - fade}}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: L.portrait ? 'column-reverse' : 'row', gap: 40 * u}}>
        <div style={{position: 'relative', width: textW, height: 140 * u, display: 'flex', alignItems: 'center'}}>
          {lines(spot.tagline, a, 1 - out1, Boolean(B.fonts.script))}
          {lines(spot.cta, b, 1)}
        </div>
        {logoTile}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

