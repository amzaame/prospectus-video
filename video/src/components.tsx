import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {useBrand} from './brand';
import type {PriceT} from './types';

export const useLayout = () => {
  const {width, height} = useVideoConfig();
  const portrait = height > width;
  return portrait
    ? {
        portrait,
        width,
        height,
        unit: width / 1080,
        dates: {x: 60, y: 70},
        text: {x: 70, y: 250, w: 540},
        product: {x: 90, y: 1060, w: 900, h: 640},
        page: {x: 610, y: 230, h: 760, rot: 5},
      }
    : {
        portrait,
        width,
        height,
        unit: width / 1920,
        dates: {x: 70, y: 60},
        text: {x: 110, y: 215, w: 560},
        product: {x: 680, y: 210, w: 500, h: 640},
        page: {x: 1270, y: 50, h: 960, rot: 4},
      };
};

/** Spring that starts at `delay` frames. */
export const useEnter = (delay = 0, config: Parameters<typeof spring>[0]['config'] = {damping: 200}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - delay, fps, config});
};

export const starPath = (points: number, outer: number, inner: number) => {
  const pts: string[] = [];
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? outer : inner;
    const a = (Math.PI * i) / points - Math.PI / 2;
    pts.push(`${(r * Math.cos(a)).toFixed(2)},${(r * Math.sin(a)).toFixed(2)}`);
  }
  return `M${pts.join('L')}Z`;
};

/** 4-point twinkle star (Leclerc Christmas catalogue). */
const sparklePath = (r: number) =>
  `M0,${-r} C${r * 0.12},${-r * 0.12} ${r * 0.12},${-r * 0.12} ${r},0 C${r * 0.12},${r * 0.12} ${r * 0.12},${r * 0.12} 0,${r} ` +
  `C${-r * 0.12},${r * 0.12} ${-r * 0.12},${r * 0.12} ${-r},0 C${-r * 0.12},${-r * 0.12} ${-r * 0.12},${-r * 0.12} 0,${-r}Z`;

/** "25 jours Auchan" pixel confetti: squares that drift up and blink. */
const PIXELS = Array.from({length: 34}, (_, i) => ({
  x: ((i * 0.618034) % 1) * 0.98 + 0.01,
  y: ((i * 0.754877 + 0.21) % 1),
  s: 0.006 + ((i * 5) % 4) * 0.0045,
  light: i % 3 === 0,
  phase: i * 2.3,
}));

const SPARKLES = Array.from({length: 22}, (_, i) => ({
  x: ((i * 0.618034) % 1) * 0.96 + 0.02,
  y: ((i * 0.381966 + 0.13) % 1) * 0.96 + 0.02,
  r: 0.006 + ((i * 7) % 5) * 0.004,
  phase: i * 1.7,
}));

/** Brand background: colour or gradient, soft light, and the brand's decoration. */
export const Background: React.FC<{color: string}> = ({color}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const B = useBrand();
  const stars = [
    {x: 0.07, y: 0.12, r: 0.11, s: 1},
    {x: 0.08, y: 0.72, r: 0.13, s: -1},
    {x: 0.55, y: 0.95, r: 0.09, s: 1},
    {x: 0.42, y: 0.08, r: 0.06, s: -1},
  ];
  const m = Math.min(width, height) * 1.6;
  const base = B.bg2 ? `linear-gradient(160deg, ${color} 0%, ${color} 35%, ${B.bg2} 100%)` : color;
  return (
    <AbsoluteFill style={{background: base}}>
      <AbsoluteFill
        style={{background: `radial-gradient(circle at 35% 45%, rgba(255,255,255,0.18), rgba(255,255,255,0) 60%)`}}
      />
      <svg width={width} height={height} style={{position: 'absolute'}}>
        {B.pattern === 'burst' &&
          stars.map((s, i) => (
            <g key={i} transform={`translate(${s.x * width} ${s.y * height}) rotate(${s.s * frame * 0.25})`}>
              <path d={starPath(14, s.r * m, s.r * m * 0.84)} fill="white" opacity={0.08} />
            </g>
          ))}
        {B.pattern === 'pixels' &&
          PIXELS.map((p, i) => {
            const size = p.s * m;
            const blink = Math.sin(frame / 7 + p.phase) > -0.6 ? 1 : 0.25;
            const y = (((p.y - frame * 0.0006) % 1) + 1) % 1;
            return (
              <rect key={i} x={p.x * width} y={y * height} width={size} height={size}
                fill={p.light ? '#ffffff' : '#ff8a8a'} opacity={(p.light ? 0.5 : 0.4) * blink} />
            );
          })}
        {B.pattern === 'sparkle' &&
          SPARKLES.map((s, i) => {
            const tw = 0.5 + 0.5 * Math.sin(frame / 9 + s.phase);
            const r = s.r * m * (0.6 + 0.4 * tw);
            return (
              <path key={i} d={sparklePath(r)} fill="white" opacity={0.25 + 0.55 * tw}
                transform={`translate(${s.x * width} ${s.y * height}) rotate(${frame * 0.4 + i * 20})`} />
            );
          })}
      </svg>
      <AbsoluteFill
        style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.25) 100%)'}}
      />
    </AbsoluteFill>
  );
};

/** Masked line reveal (text slides up from behind a clip). */
export const Reveal: React.FC<{delay: number; children: React.ReactNode; style?: React.CSSProperties}> = ({
  delay,
  children,
  style,
}) => {
  const p = useEnter(delay);
  return (
    <div style={{overflow: 'hidden', ...style}}>
      <div style={{transform: `translateY(${(1 - p) * 110}%)`, opacity: interpolate(p, [0, 0.3], [0, 1])}}>
        {children}
      </div>
    </div>
  );
};

/** Price in catalogue style: big integer, then € on top and cents under it. */
export const Price: React.FC<{price: PriceT; size: number; color?: string; struck?: number}> = ({
  price,
  size,
  color,
  struck,
}) => {
  const B = useBrand();
  const c = color ?? B.priceColor ?? 'white';
  const font = B.fonts.price ?? B.fonts.heavy;
  const w = B.priceStyle === 'stack' ? 800 : 900;
  const strikeLine =
    struck === undefined ? null : B.strike === 'straight' ? (
      <div style={{position: 'absolute', left: -size * 0.03, top: '48%', height: size * 0.07, width: `${struck * 106}%`,
        background: c, borderRadius: size}} />
    ) : (
      <svg style={{position: 'absolute', inset: 0, overflow: 'visible'}} width="100%" height="100%" viewBox="0 0 100 100"
        preserveAspectRatio="none">
        <line x1="-4" y1="78" x2={-4 + 108 * struck} y2={78 - 62 * struck} stroke={B.strikeColor ?? '#ff2a2a'} strokeWidth={7}
          vectorEffect="non-scaling-stroke" strokeLinecap="round" style={{strokeWidth: size * 0.07}} />
      </svg>
    );
  if (B.priceStyle === 'inline') {
    // Lidl: "44.99", cents a touch smaller on the same top line
    return (
      <div style={{position: 'relative', display: 'inline-flex', alignItems: 'flex-start', color: c, fontFamily: font,
        fontWeight: w, lineHeight: 0.8, letterSpacing: -size * 0.02}}>
        <span style={{fontSize: size}}>{price.int}</span>
        <span style={{fontSize: size * 0.82}}>.{price.cents || '00'}</span>
        {strikeLine}
      </div>
    );
  }
  return (
    <div style={{position: 'relative', display: 'inline-flex', alignItems: 'flex-start', color: c, fontFamily: font}}>
      <span style={{fontSize: size, fontWeight: w, lineHeight: 0.82, letterSpacing: -size * 0.04}}>{price.int}</span>
      <span style={{display: 'flex', flexDirection: 'column', marginLeft: size * 0.03, lineHeight: 0.9}}>
        <span style={{fontSize: size * 0.42, fontWeight: w}}>€</span>
        {(price.cents || B.priceStyle !== 'stack') && (
          <span style={{fontSize: size * 0.4, fontWeight: w, marginTop: -size * 0.04}}>
            {B.priceStyle === 'comma' ? ',' : ''}
            {price.cents || '00'}
          </span>
        )}
      </span>
      {strikeLine}
    </div>
  );
};

export const DatePills: React.FC<{dates: string[]; color: string}> = ({dates, color}) => {
  const L = useLayout();
  const B = useBrand();
  const u = L.unit;
  return (
    <div style={{position: 'absolute', left: L.dates.x * u, top: L.dates.y * u, transform: `rotate(${B.tilt}deg)`}}>
      {dates.map((d, i) => {
        const p = useEnter(i * 5);
        return (
          <div key={i} style={{transform: `translateX(${(1 - p) * -120}%)`, marginLeft: i === 0 && B.tilt ? 30 * u : 0}}>
            <span
              style={{
                display: 'inline-block',
                background: B.datePill.bg,
                color: B.datePill.fg || color,
                fontFamily: B.fonts.heavy,
                fontWeight: 900,
                fontSize: (L.portrait ? 30 : 28) * u,
                padding: `${4 * u}px ${12 * u}px`,
                marginBottom: 4 * u,
                boxShadow: '0 6px 18px rgba(0,0,0,0.18)',
              }}
            >
              {d}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export const LegalBar: React.FC<{text: string}> = ({text}) => {
  const L = useLayout();
  const B = useBrand();
  const u = L.unit;
  const p = useEnter(0);
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        padding: `${40 * u}px ${40 * u}px ${18 * u}px`,
        background: 'linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0.35))',
        color: 'white',
        textAlign: 'center',
        fontFamily: B.fonts.cond,
        fontWeight: 700,
        fontSize: (L.portrait ? 22 : 24) * u,
        opacity: p,
      }}
    >
      {text}
    </div>
  );
};

export const Sticker: React.FC<{text: string; sub?: string; color: string; textColor: string; size: number}> = ({
  text,
  sub,
  color,
  textColor,
  size,
}) => {
  const frame = useCurrentFrame();
  const B = useBrand();
  if (B.sticker === 'ticket') return <TicketSticker text={text} color={color} textColor={textColor} size={size} />;
  if (B.sticker === 'tag') return <TagSticker text={text} sub={sub} size={size} />;
  if (B.sticker === 'round') return <RoundSticker text={text} sub={sub} color={color} textColor={textColor} size={size} />;
  return (
    <div style={{position: 'relative', width: size, height: size, transform: `rotate(${Math.sin(frame / 14) * 4 - 8}deg)`}}>
      <svg width={size} height={size} viewBox="-100 -100 200 200" style={{position: 'absolute', overflow: 'visible'}}>
        <path d={starPath(18, 100, 86)} fill="#e30613" />
        <path d={starPath(18, 92, 79)} fill={color} />
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          color: textColor,
          fontFamily: B.fonts.heavy,
          fontWeight: 900,
          lineHeight: 0.95,
        }}
      >
        <div style={{fontSize: size * (text.length > 4 ? 0.24 : 0.3), letterSpacing: -1}}>{text}</div>
        {sub && <div style={{fontSize: size * 0.085, marginTop: size * 0.02, maxWidth: size * 0.62, fontFamily: B.fonts.cond, fontWeight: 700}}>{sub}</div>}
      </div>
    </div>
  );
};

/** Système U loyalty disc: plain disc, big figure, caption inside under it. */
const RoundSticker: React.FC<{text: string; sub?: string; color: string; textColor: string; size: number}> = ({
  text,
  sub,
  color,
  textColor,
  size,
}) => {
  const frame = useCurrentFrame();
  const B = useBrand();
  return (
    <div style={{width: size, height: size, borderRadius: '50%', background: color, color: textColor,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
      transform: `rotate(${Math.sin(frame / 14) * 3 - 6}deg)`, boxShadow: '0 14px 30px rgba(0,0,0,0.3)'}}>
      <div style={{fontFamily: B.fonts.heavy, fontWeight: 900, fontSize: size * 0.34, lineHeight: 0.95, letterSpacing: -2}}>
        {text}
      </div>
      {sub && (
        <div style={{fontFamily: B.fonts.heavy, fontWeight: 800, fontSize: size * 0.085, maxWidth: size * 0.7,
          marginTop: size * 0.03, lineHeight: 1.1}}>
          {sub}
        </div>
      )}
    </div>
  );
};

/** Lidl discount tag: red box, white heavy figure, small caption under it. */
const TagSticker: React.FC<{text: string; sub?: string; size: number}> = ({text, sub, size}) => {
  const frame = useCurrentFrame();
  const B = useBrand();
  const box = B.badgeBox ?? {bg: '#e60a14', fg: '#ffffff'};
  return (
    <div style={{display: 'inline-flex', flexDirection: 'column', alignItems: 'stretch',
      transform: `rotate(${Math.sin(frame / 14) * 2 - 5}deg)`, filter: 'drop-shadow(0 12px 18px rgba(0,0,0,0.3))'}}>
      <div style={{background: box.bg, color: box.fg, fontFamily: B.fonts.price ?? B.fonts.heavy, fontWeight: 900,
        fontSize: size * 0.36, lineHeight: 1, padding: `${size * 0.04}px ${size * 0.08}px`, textAlign: 'center'}}>
        {text}
      </div>
      {sub && (
        <div style={{background: B.tagSub?.bg ?? '#fff000', color: B.tagSub?.fg ?? '#0050aa', fontFamily: B.fonts.heavy, fontWeight: 800,
          fontSize: size * 0.075, padding: `${size * 0.025}px ${size * 0.05}px`, textAlign: 'center'}}>
          {sub}
        </div>
      )}
    </div>
  );
};

/** Leclerc loyalty sticker: yellow disc, "Ticket E.Leclerc" curved on top, amount, "avec la Carte" below. */
const TicketSticker: React.FC<{text: string; color: string; textColor: string; size: number}> = ({
  text,
  color,
  textColor,
  size,
}) => {
  const frame = useCurrentFrame();
  const B = useBrand();
  const m = text.match(/^(\d+)€(\d{2})?$/);
  const isAmount = Boolean(m);
  return (
    <div style={{position: 'relative', width: size, height: size, transform: `rotate(${Math.sin(frame / 14) * 3 - 6}deg)`}}>
      <svg width={size} height={size} viewBox="-100 -100 200 200" style={{position: 'absolute', overflow: 'visible'}}>
        <defs>
          <path id="tk-top" d="M -70 0 A 70 70 0 0 1 70 0" />
          <path id="tk-bot" d="M -86 0 A 86 86 0 0 0 86 0" />
        </defs>
        <circle r={98} fill={color} />
        <circle r={98} fill="none" stroke={textColor} strokeWidth={3} opacity={0.25} />
        {isAmount && (
          <>
            <text fill={textColor} fontFamily={B.fonts.heavy} fontWeight={800} fontSize={21} fontStyle="italic">
              <textPath href="#tk-top" startOffset="50%" textAnchor="middle">{B.stickerTitle}</textPath>
            </text>
            <text fill={textColor} fontFamily={B.fonts.heavy} fontWeight={800} fontSize={21} fontStyle="italic">
              <textPath href="#tk-bot" startOffset="50%" textAnchor="middle">{B.stickerFooter}</textPath>
            </text>
          </>
        )}
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: textColor,
          fontFamily: B.fonts.heavy,
          fontWeight: 900,
          lineHeight: 0.85,
        }}
      >
        {m ? (
          <div style={{display: 'flex', alignItems: 'flex-start'}}>
            <span style={{fontSize: size * 0.42, letterSpacing: -2}}>{m[1]}</span>
            <span style={{display: 'flex', flexDirection: 'column', marginLeft: size * 0.01}}>
              <span style={{fontSize: size * 0.2}}>€</span>
              {m[2] && <span style={{fontSize: size * 0.15}}>,{m[2]}</span>}
            </span>
          </div>
        ) : (
          <div style={{fontSize: size * 0.2, textAlign: 'center'}}>{text}</div>
        )}
      </div>
    </div>
  );
};

export const ease = Easing.bezier(0.65, 0, 0.35, 1);
