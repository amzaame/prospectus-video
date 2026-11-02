import React from 'react';
import {Composition} from 'remotion';
import {Spot} from './Spot';
import {FPS, totalFrames} from './timing';
import type {Spot as SpotT} from './types';
import carrefour from './spots/carrefour.json';
import leclerc from './spots/leclerc.json';
import lidl from './spots/lidl.json';
import auchan from './spots/auchan.json';

// one entry per catalogue config written by extractor/make_spot.py
const SPOTS: Record<string, SpotT> = {
  Carrefour: carrefour as unknown as SpotT,
  Leclerc: leclerc as unknown as SpotT,
  Lidl: lidl as unknown as SpotT,
  Auchan: auchan as unknown as SpotT,
};

export const Root: React.FC = () => (
  <>
    {Object.entries(SPOTS).map(([name, spot]) => (
      <React.Fragment key={name}>
        <Composition id={`${name}-16x9`} component={Spot} width={1920} height={1080} fps={FPS}
          durationInFrames={totalFrames(spot)} defaultProps={{spot}}
          calculateMetadata={({props}) => ({durationInFrames: totalFrames(props.spot)})} />
        <Composition id={`${name}-9x16`} component={Spot} width={1080} height={1920} fps={FPS}
          durationInFrames={totalFrames(spot)} defaultProps={{spot}}
          calculateMetadata={({props}) => ({durationInFrames: totalFrames(props.spot)})} />
      </React.Fragment>
    ))}
  </>
);
