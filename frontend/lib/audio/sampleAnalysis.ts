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

    // Get samples safely with proper typing
    let samples: number[];
    try {
      const rawSamples = wav.getSamples();

      if (rawSamples instanceof Float64Array) {
        samples = Array.from(rawSamples);
      } else if (Array.isArray(rawSamples)) {
        // Handle multi-channel audio
        if (Array.isArray(rawSamples[0])) {
          // Convert multi-channel to mono by averaging
          const channels = rawSamples as number[][];
          const length = channels[0].length;
          samples = new Array(length);

          for (let i = 0; i < length; i++) {
            let sum = 0;
            for (const channel of channels) {
              sum += channel[i];
            }
            samples[i] = sum / channels.length;
          }
        } else {
          // Single channel
          samples = rawSamples as number[];
        }
      } else {
        throw new Error('Unsupported sample format');
      }
    } catch (error) {
      console.error('Error processing samples:', error);
      throw error;
    }

    if (!samples || samples.length === 0) {
      throw new Error('No samples found in audio file');
    }

    // Calculate duration
    const duration = samples.length / sampleRate;

    // Calculate peak amplitude with bounds checking
    const maxPossibleValue = Math.pow(2, format.bitsPerSample - 1);
    let peakAmplitude = 0;

    // Use a regular for loop instead of map/reduce for better performance
    for (let i = 0; i < samples.length; i++) {
      const absValue = Math.abs(samples[i]);
      if (absValue > peakAmplitude) {
        peakAmplitude = absValue;
      }
    }
    const amplitude = peakAmplitude / maxPossibleValue;

    // Find attack time with early exit
    const attackThreshold = amplitude * 0.9;
    let attackSample = -1;
    for (let i = 0; i < samples.length; i++) {
      if (Math.abs(samples[i]) >= attackThreshold) {
        attackSample = i;
        break;
      }
    }
    const attack = attackSample >= 0 ? attackSample / sampleRate : 0.01;

    // Determine character
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
    console.error('Error analyzing sample:', error, 'File:', filePath);
    // Return default values instead of throwing
    return {
      duration: 0.1,
      amplitude: 0.5,
      character: 'medium'
    };
  }
}

// Remove or simplify complex frequency analysis if not needed
function calculateDominantFrequency(samples: number[], sampleRate: number): number {
  // Simplified frequency detection
  const fftSize = Math.min(2048, samples.length);
  let maxAmplitude = 0;
  let dominantFrequency = 440; // Default to A440

  for (let i = 0; i < fftSize; i++) {
    const amplitude = Math.abs(samples[i]);
    if (amplitude > maxAmplitude) {
      maxAmplitude = amplitude;
      dominantFrequency = (i * sampleRate) / fftSize;
    }
  }

  return dominantFrequency;
}

// Simplified decay calculation
function calculateDecay(samples: number[], sampleRate: number, attackSample: number): number {
  if (!Array.isArray(samples) || attackSample >= samples.length) {
    return 0.1;
  }

  const peakAmplitude = Math.abs(samples[attackSample]);
  const decayThreshold = peakAmplitude * 0.1;

  for (let i = attackSample; i < samples.length; i++) {
    if (Math.abs(samples[i]) <= decayThreshold) {
      return (i - attackSample) / sampleRate;
    }
  }

  return 0.1;
}
