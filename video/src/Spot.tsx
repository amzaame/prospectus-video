import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {BrandContext, STYLES} from './brand';
import {Background, DatePills, LegalBar} from './components';
import {Intro, OfferScene, Outro} from './scenes';
import {INTRO, OFFER, OUTRO, OVERLAP, offerStart, outroStart} from './timing';
import type {Spot as SpotT} from './types';

export const Spot: React.FC<{spot: SpotT}> = ({spot}) => {
  const n = spot.offers.length;
  return (
    <BrandContext.Provider value={STYLES[spot.theme.style ?? 'carrefour']}>
    <AbsoluteFill style={{background: spot.theme.bg}}>
      <Background color={spot.theme.bg} />
      {spot.offers.map((o, i) => (
        <Sequence key={o.id} from={offerStart(i)} durationInFrames={OFFER} name={`${o.id} ${o.brand || o.name}`}>
          <OfferScene offer={o} spot={spot} index={i} />
        </Sequence>
      ))}
      <Sequence from={0} durationInFrames={INTRO} name="Intro">
        <Intro spot={spot} />
      </Sequence>
      <Sequence from={INTRO - OVERLAP} durationInFrames={outroStart(n) - INTRO + OVERLAP + 6} name="Mentions">
        <LegalBar text={spot.legal} />
      </Sequence>
      <Sequence from={8} durationInFrames={outroStart(n) - 2} name="Dates">
        <DatePills dates={spot.dates} color={spot.theme.bg} />
      </Sequence>
      <Sequence from={outroStart(n)} durationInFrames={OUTRO} name="Outro">
        <Outro spot={spot} />
      </Sequence>
    </AbsoluteFill>
    </BrandContext.Provider>
  );
};
