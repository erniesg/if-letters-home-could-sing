import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { analyzeSample, SampleMetadata } from '../../../lib/audio/sampleAnalysis';

export async function GET() {
  try {
    const percussionDir = path.join(process.cwd(), 'public', 'percussion');

    if (!fs.existsSync(percussionDir)) {
      console.error('Percussion directory not found:', percussionDir);
      return NextResponse.json({ error: 'Percussion directory not found' }, { status: 404 });
    }

    const files = fs.readdirSync(percussionDir);
    const wavFiles = files.filter(file => file.endsWith('.wav'));

    if (wavFiles.length === 0) {
      return NextResponse.json({ error: 'No wav files found' }, { status: 404 });
    }

    const samplesMetadata: Record<string, SampleMetadata[]> = {};

    for (const file of wavFiles) {
      try {
        const filePath = path.join(percussionDir, file);
        const characteristics = await analyzeSample(filePath);

        const instrumentMatch = file.toLowerCase().match(/(bangu|daluo|xiaoluo|nanbo)/);
        
        if (instrumentMatch) {
          const instrument = instrumentMatch[1];
          if (!samplesMetadata[instrument]) {
            samplesMetadata[instrument] = [];
          }

          samplesMetadata[instrument].push({
            filename: file,
            instrument,
            characteristics
          });
        }
      } catch (error) {
        console.error(`Error analyzing ${file}:`, error);
      }
    }

    return NextResponse.json(samplesMetadata);

  } catch (error) {
    console.error('Error in sound API:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
