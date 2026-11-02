import {Config} from '@remotion/cli/config';
import fs from 'fs';

// Use the local Chrome when Remotion's headless shell can't be downloaded.
const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
if (fs.existsSync(chrome)) {
  Config.setBrowserExecutable(chrome);
}
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
