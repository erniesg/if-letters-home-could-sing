import { SampleMetadata } from './sampleAnalysis';

interface AudioEngineMetadata extends SampleMetadata {
  buffer: AudioBuffer;
}

interface InstrumentConfig {
  harmonics: number[];
  freq: number;
  type: OscillatorType;
}

interface AudioCharacteristics {
  intensity: number;    // Overall intensity/loudness
  duration: number;     // Length of sound
  attack: number;       // Attack speed
  decay: number;        // Decay rate
  peakFrequency: number; // Dominant frequency
}

export interface PlaySoundOptions {
  intensity: number;
  isAccent: boolean;
  tempo: number;
  position: number;
  sampleVariation?: SampleMetadata;
}

class AudioEngine {
  private audioContext: AudioContext;
  private analyser: AnalyserNode;
  private sampleMetadata: Map<string, AudioEngineMetadata[]> = new Map();
  private instruments: Map<string, InstrumentConfig>;
  private isInitialized: boolean = false;

  constructor() {
    this.audioContext = new AudioContext();
    this.analyser = this.audioContext.createAnalyser();
    this.instruments = new Map([
      ['bangu', { harmonics: [1, 2, 3], freq: 220, type: 'sine' }],
      ['daluo', { harmonics: [1, 1.5, 2], freq: 110, type: 'sine' }],
      ['xiaoluo', { harmonics: [1, 2, 4], freq: 440, type: 'sine' }],
      ['nanbo', { harmonics: [1, 2, 3], freq: 330, type: 'sine' }],
    ]);

    this.discoverAndLoadSamples().catch(console.error);
  }

  private async analyzeBuffer(buffer: AudioBuffer): Promise<AudioCharacteristics> {
    const offlineContext = new OfflineAudioContext(
      1,
      buffer.length,
      buffer.sampleRate
    );

    const source = offlineContext.createBufferSource();
    const analyser = offlineContext.createAnalyser();

    source.buffer = buffer;
    source.connect(analyser);
    analyser.connect(offlineContext.destination);

    const dataArray = new Float32Array(analyser.frequencyBinCount);
    source.start();

    const renderedBuffer = await offlineContext.startRendering();
    analyser.getFloatFrequencyData(dataArray);

    // Calculate characteristics
    let peakIntensity = 0;
    let peakFrequency = 0;
    let attackTime = 0;
    let decayRate = 0;

    // Calculate peak intensity and frequency
    dataArray.forEach((value, index) => {
      if (value > peakIntensity) {
        peakIntensity = value;
        peakFrequency = index * (buffer.sampleRate / analyser.frequencyBinCount);
      }
    });

    // Calculate attack time (time to reach peak)
    const channelData = renderedBuffer.getChannelData(0);
    for (let i = 0; i < channelData.length; i++) {
      if (Math.abs(channelData[i]) > 0.9 * peakIntensity) {
        attackTime = i / buffer.sampleRate;
        break;
      }
    }

    // Calculate decay rate
    let peakFound = false;
    let decayStart = 0;
    for (let i = 0; i < channelData.length; i++) {
      if (!peakFound && Math.abs(channelData[i]) >= peakIntensity) {
        peakFound = true;
        decayStart = i;
      }
      if (peakFound && Math.abs(channelData[i]) < 0.1 * peakIntensity) {
        decayRate = (i - decayStart) / buffer.sampleRate;
        break;
      }
    }

    return {
      intensity: peakIntensity,
      duration: buffer.duration,
      attack: attackTime,
      decay: decayRate,
      peakFrequency
    };
  }

  private findBestMatchingSample(instrument: string, options: PlaySoundOptions): AudioBuffer | null {
    const samples = this.sampleMetadata.get(instrument);
    if (!samples?.length) return null;

    // Find sample that best matches the intensity and accent
    const targetIntensity = options.isAccent ? options.intensity * 1.2 : options.intensity;

    const bestMatch = samples.reduce((best, current) => {
      const currentDiff = Math.abs(current.characteristics.amplitude - targetIntensity);
      const bestDiff = Math.abs(best.characteristics.amplitude - targetIntensity);
      return currentDiff < bestDiff ? current : best;
    });

    return bestMatch.buffer;
  }

  public playSound(instrument: string, options: PlaySoundOptions) {
    const samples = this.sampleMetadata.get(instrument);
    if (!samples?.length) return;

    // Find the matching sample with buffer
    const matchingSample = samples.find(sample =>
      sample.filename === options.sampleVariation?.filename
    ) || samples[0];

    if (!matchingSample?.buffer) return;

    try {
      const source = this.audioContext.createBufferSource();
      const gain = this.audioContext.createGain();

      source.buffer = matchingSample.buffer;

      // Scale intensity to volume (0-1 range)
      const baseVolume = options.intensity * 0.8;
      const accentBoost = options.isAccent ? 0.2 : 0;
      const randomVariation = Math.random() * 0.1 - 0.05;
      gain.gain.value = Math.min(1, baseVolume + accentBoost + randomVariation);

      // Add subtle pitch variations
      const pitchVariation = 1 + (Math.random() * 0.1 - 0.05);
      source.playbackRate.value = pitchVariation;

      source.connect(gain);
      gain.connect(this.analyser);
      gain.connect(this.audioContext.destination);

      source.start(this.audioContext.currentTime);
    } catch (error) {
      console.error(`Error playing ${instrument}:`, error);
    }
  }

  public playPattern(instrument: string, pattern: number[], tempo: number) {
    const beatDuration = 60 / tempo;
    pattern.forEach((hit, index) => {
      if (hit) {
        this.playNote(instrument, 0.1, index * beatDuration);
      }
    });
  }

  public playNote(instrument: string, duration: number = 0.1, delay: number = 0) {
    const config = this.instruments.get(instrument);
    if (!config) return;

    // Create multiple oscillators for harmonics
    config.harmonics.forEach((harmonic, index) => {
      const osc = this.audioContext.createOscillator();
      const gain = this.audioContext.createGain();

      osc.frequency.value = config.freq * harmonic;
      osc.type = config.type;

      // Adjust gain for each harmonic
      const harmonicGain = 0.5 / (index + 1);
      gain.gain.value = harmonicGain;

      osc.connect(gain);
      gain.connect(this.audioContext.destination);

      const now = this.audioContext.currentTime;
      const startTime = now + delay;

      // Add slight variations to make it sound more natural
      const randomDelay = Math.random() * 0.02;
      gain.gain.setValueAtTime(harmonicGain, startTime + randomDelay);
      gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);

      osc.start(startTime);
      osc.stop(startTime + duration);
    });
  }

  public dispose() {
    this.audioContext.close();
  }

  public isReady(): boolean {
    return this.isInitialized && this.sampleMetadata.size > 0;
  }

  private async discoverAndLoadSamples() {
    try {
      const response = await fetch('/api/sound');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const samplesMetadata: Record<string, SampleMetadata[]> = await response.json();

      // Load audio buffers for each sample
      for (const [instrument, samples] of Object.entries(samplesMetadata)) {
        const metadata: AudioEngineMetadata[] = [];

        for (const sample of samples) {
          try {
            const response = await fetch(`/percussion/${sample.filename}`);
            if (!response.ok) {
              throw new Error(`Failed to fetch ${sample.filename}`);
            }

            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

            metadata.push({
              ...sample,
              buffer: audioBuffer
            });

            console.log(`Loaded ${sample.filename}`);
          } catch (error) {
            console.error(`Error loading ${sample.filename}:`, error);
          }
        }

        if (metadata.length > 0) {
          this.sampleMetadata.set(instrument, metadata);
          console.log(`Loaded ${metadata.length} samples for ${instrument}`);
        }
      }

      this.isInitialized = true;
    } catch (error) {
      console.error('Error discovering samples:', error);
    }
  }
}

export default AudioEngine;
