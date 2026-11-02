import React from 'react';
import {Composition} from 'remotion';
import {Spot} from './Spot';
import {FPS, totalFrames} from './timing';
import type {Spot as SpotT} from './types';

// every config written by extractor/make_spot.py into ./spots becomes <Name>-16x9 and <Name>-9x16
declare const require: {
  context: (dir: string, deep: boolean, filter: RegExp) => {keys: () => string[]; (key: string): unknown};
};
const ctx = require.context('./spots', false, /\.json$/);
const SPOTS: Record<string, SpotT> = Object.fromEntries(
  ctx.keys().map((key) => {
    const name = key.replace(/^\.\//, '').replace(/\.json$/, '');
    return [name.charAt(0).toUpperCase() + name.slice(1), ctx(key) as SpotT];
  }),
);

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
