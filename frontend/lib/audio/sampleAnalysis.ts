import { WaveFile } from 'wavefile';
import fs from 'fs';

export interface SampleCharacteristics {
  duration: number;      // Duration in seconds
  amplitude: number;     // Peak amplitude (0-1)
  character: 'soft' | 'medium' | 'hard';  // Timbral character
}

export interface SampleMetadata {
  filename: string;
  instrument: string;
  characteristics: SampleCharacteristics;
}

// Extend WaveFile format interface
interface WaveFormat {
  sampleRate: number;
  bitsPerSample: number;
  numChannels: number;
}

export async function analyzeSample(filePath: string): Promise<SampleCharacteristics> {
  try {
    const buffer = await fs.promises.readFile(filePath);
    const wav = new WaveFile(buffer);

    // Type assertion for wav.fmt
    const format = wav.fmt as WaveFormat;
    const sampleRate = format.sampleRate;

    // Convert Float64Array to number[]
    const rawSamples = wav.getSamples();
    const samples = Array.from(rawSamples as Float64Array);

    if (!samples || !samples.length) {
      throw new Error('No samples found in audio file');
    }

    const duration = samples.length / sampleRate;

    // Calculate peak amplitude (normalize to 0-1 range)
    const maxPossibleValue = Math.pow(2, format.bitsPerSample - 1);
    const amplitude = Math.max(...samples.map(Math.abs)) / maxPossibleValue;

    // Analyze attack
    const attackThreshold = amplitude * 0.9;
    const attackSample = samples.findIndex(s => Math.abs(s) >= attackThreshold);
    const attack = attackSample / sampleRate;

    // Determine character based on amplitude and attack
    let character: 'soft' | 'medium' | 'hard';
    if (amplitude > 0.8 && attack < 0.05) {
      character = 'hard';
    } else if (amplitude > 0.4 || attack < 0.1) {
      character = 'medium';
    } else {
      character = 'soft';
    }

    return {
      duration,
      amplitude,
      character
    };
  } catch (error) {
    console.error('Error analyzing sample:', error);
    return {
      duration: 0.1,
      amplitude: 0.5,
      character: 'medium'
    };
  }
}

function calculateDominantFrequency(samples: number[], sampleRate: number): number {
  // Simple peak frequency detection
  let maxAmplitude = 0;
  let dominantFrequency = 0;

  // Create a simple FFT-like analysis
  const fftSize = 2048;
  const fft = new Float32Array(fftSize);

  // Copy samples to FFT buffer
  for (let i = 0; i < Math.min(samples.length, fftSize); i++) {
    fft[i] = samples[i];
  }

  // Find peak frequency (simplified)
  for (let i = 0; i < fft.length / 2; i++) {
    const frequency = i * sampleRate / fft.length;
    const amplitude = Math.abs(fft[i]);

    if (amplitude > maxAmplitude) {
      maxAmplitude = amplitude;
      dominantFrequency = frequency;
    }
  }

  return dominantFrequency;
}

function calculateDecay(samples: number[], sampleRate: number, attackSample: number): number {
  if (!Array.isArray(samples)) {
    return 0.1; // Default decay time
  }

  const peakAmplitude = Math.max(...samples.slice(attackSample).map(Math.abs));
  const decayThreshold = peakAmplitude * 0.1;

  const decaySample = samples.slice(attackSample).findIndex(
    s => Math.abs(s) <= decayThreshold
  );

  return decaySample > 0 ? decaySample / sampleRate : 0.1;
}
