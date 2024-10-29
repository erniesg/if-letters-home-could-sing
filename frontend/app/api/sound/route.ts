import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { analyzeSample, SampleMetadata } from '../../../lib/audio/sampleAnalysis';

export async function GET() {
  try {
    const percussionDir = path.join(process.cwd(), 'public', 'percussion');

    // Check if directory exists
    if (!fs.existsSync(percussionDir)) {
      console.error('Percussion directory not found:', percussionDir);
      return NextResponse.json({ error: 'Percussion directory not found' }, { status: 404 });
    }

    const files = fs.readdirSync(percussionDir);
    const validFiles = files.filter(file => /\d+__[a-z]+__[a-z]+-\d+\.wav$/i.test(file));

    if (validFiles.length === 0) {
      return NextResponse.json({ error: 'No valid audio files found' }, { status: 404 });
    }

    // Analyze each file and create metadata
    const samplesMetadata: Record<string, SampleMetadata[]> = {};

    for (const file of validFiles) {
      try {
        const filePath = path.join(percussionDir, file);
        const characteristics = await analyzeSample(filePath);

        // Extract instrument name from filename
        const match = file.match(/\d+__[a-z]+__([a-z]+)-\d+\.wav$/i);
        if (match) {
          const instrument = match[1].toLowerCase();
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
