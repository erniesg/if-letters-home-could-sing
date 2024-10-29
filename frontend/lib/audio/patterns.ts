import { SampleMetadata, SampleCharacteristics } from './sampleAnalysis';

export interface LetterMetrics {
  emotionalIntensity: number;  // 0-1
  urgency: number;            // 0-1
  length: number;            // word count
  dominantEmotion: 'distress' | 'worry' | 'reassurance';
  emotionalProgression: {
    start: number;
    peak: number;
    end: number;
  };
}

export interface PatternContext {
  hit: number;
  intensity: number;
  isAccent: boolean;
  tempo: number;
  position: number;
  sampleVariation: SampleMetadata;
}

// Enhanced Hainanese opera-inspired patterns with more emotional variation
export const basePatterns = {
  entrance: {
    distress: {
      bangu:   [1,0,1,1, 0,1,0,1, 1,1,0,1, 0,1,1,0],
      daluo:   [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,1,0,0],
      xiaoluo: [0,1,0,1, 1,0,1,0, 0,1,0,1, 1,0,0,1],
      nanbo:   [1,0,0,1, 0,0,1,0, 0,0,1,0, 0,1,0,1]
    },
    worry: {
      bangu:   [1,0,1,0, 1,1,0,0, 1,0,1,0, 0,1,1,0],
      daluo:   [1,0,0,0, 0,1,0,0, 1,0,0,0, 0,0,1,0],
      xiaoluo: [0,1,0,1, 0,0,1,0, 0,1,0,1, 0,1,0,0],
      nanbo:   [0,0,1,0, 1,0,0,1, 0,0,1,0, 1,0,0,0]
    }
  },
  emotional: {
    distress: {
      bangu:   [1,1,0,1, 1,0,1,1, 1,1,1,0, 1,1,0,1],
      daluo:   [1,0,0,1, 0,1,0,1, 1,0,1,0, 0,1,1,1],
      xiaoluo: [0,1,1,0, 1,1,0,1, 0,1,1,0, 1,0,1,1],
      nanbo:   [1,0,1,1, 0,1,1,0, 1,1,0,1, 0,1,1,1]
    },
    worry: {
      bangu:   [1,0,1,1, 0,1,1,0, 1,1,0,1, 0,1,1,0],
      daluo:   [1,0,0,1, 1,0,0,1, 1,0,1,0, 0,1,0,1],
      xiaoluo: [0,1,1,0, 0,1,1,0, 0,1,0,1, 1,0,1,0],
      nanbo:   [1,0,1,0, 1,0,1,0, 0,1,1,0, 1,0,1,1]
    }
  },
  exit: {
    distress: {
      bangu:   [1,1,0,1, 1,0,0,1, 1,0,0,1, 0,0,1,0],
      daluo:   [1,0,0,1, 0,0,1,0, 1,0,0,0, 0,1,0,0],
      xiaoluo: [0,1,1,0, 0,1,0,0, 0,1,0,0, 0,0,0,1],
      nanbo:   [1,0,1,0, 0,1,0,0, 0,0,1,0, 0,0,0,0]
    },
    worry: {
      bangu:   [1,0,1,0, 1,0,0,1, 1,0,0,0, 0,0,0,1],
      daluo:   [1,0,0,1, 0,0,1,0, 0,0,0,1, 0,0,0,0],
      xiaoluo: [0,1,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,0],
      nanbo:   [0,0,1,0, 0,0,0,1, 0,0,0,0, 0,0,0,1]
    }
  }
};

// Maps heart rate to appropriate tempo range for Hainanese opera
export const mapHeartRateToTempo = (heartRate: number, emotionalIntensity: number): number => {
  const minHR = 60;
  const maxHR = 120;
  const minTempo = 65;
  const maxTempo = 95;

  // Blend heart rate and emotional intensity for tempo
  const heartRateInfluence = (heartRate - minHR) / (maxHR - minHR);
  const tempoRange = maxTempo - minTempo;
  const baseTemp = minTempo + (heartRateInfluence * tempoRange);

  // Emotional intensity can modify tempo by ±15%
  const emotionalModifier = 1 + ((emotionalIntensity - 0.5) * 0.3);

  return Math.floor(baseTemp * emotionalModifier);
};

export class PatternGenerator {
  private sampleCache: Record<string, SampleMetadata[]> = {};
  private isInitialized: boolean = false;
  private currentSection: 'entrance' | 'emotional' | 'exit' = 'entrance';
  private sectionProgress: number = 0;
  private stepsPerBar: number = 8;
  private barsPerSection: number = 2;
  private totalSteps: number = this.stepsPerBar * this.barsPerSection;

  private maxSectionCounts = {
    entrance: 1,  // 1 repetition of entrance
    emotional: 2, // 2 repetitions of emotional
    exit: 1      // 1 repetition of exit
  };

  private sectionRepetitions = {
    entrance: 0,
    emotional: 0,
    exit: 0
  };

  public isReady(): boolean {
    return this.isInitialized && Object.keys(this.sampleCache).length > 0;
  }

  public getCurrentSection(): 'entrance' | 'emotional' | 'exit' {
    return this.currentSection;
  }

  public getCurrentBar(): number {
    return Math.floor(this.sectionProgress / this.stepsPerBar);
  }

  private analyzeLetterContent(letter: number): LetterMetrics {
    // Metrics based on letter content analysis
    const metrics: Record<number, LetterMetrics> = {
      1: { // Daughter to mother - financial hardship
        emotionalIntensity: 0.7,
        urgency: 0.8,
        length: 42,
        dominantEmotion: 'distress',
        emotionalProgression: {
          start: 0.2,
          peak: 0.5,
          end: 0.8
        }
      },
      2: { // Mother to son - illness, reassurance
        emotionalIntensity: 0.6,
        urgency: 0.4,
        length: 56,
        dominantEmotion: 'reassurance',
        emotionalProgression: {
          start: 0.3,
          peak: 0.6,
          end: 0.9
        }
      }
    };
    return metrics[letter];
  }

  private generateInstrumentPattern(
    intensity: number,
    heartRateInfluence: number,
    role: string,
    basePattern: number[]
  ): number[] {
    if (!Array.isArray(basePattern)) {
      return new Array(16).fill(0);
    }

    const pattern = [...basePattern];
    const variationProbability = intensity * heartRateInfluence;

    // Add Hainanese opera-specific variations
    return pattern.map((hit, i) => {
      // Traditional accent patterns on beats 1 and 3
      const isMainBeat = i % 8 === 0;
      const isSecondaryBeat = i % 8 === 4;

      if (role === 'rhythmic') {
        // Bangu variations based on intensity
        if (isMainBeat && Math.random() < intensity) {
          return 1; // Ensure strong beats
        }
        if (Math.random() < variationProbability * 0.3) {
          return hit ? 0 : 1; // Subtle variations
        }
      }

      if (role === 'accent') {
        // Daluo emphasizes structural points
        if ((isMainBeat || isSecondaryBeat) && Math.random() < intensity) {
          return 1;
        }
      }

      if (role === 'ornamental') {
        // Xiaoluo adds flourishes between main beats
        if (!isMainBeat && !isSecondaryBeat && Math.random() < variationProbability * 0.4) {
          return Math.random() < intensity ? 1 : 0;
        }
      }

      return hit;
    });
  }

  public generatePattern(letter: number, heartRate: number): PatternMap {
    const metrics = this.analyzeLetterContent(letter);
    const heartRateInfluence = (heartRate - 60) / 60; // Normalize to 0-1 range

    // Progress through sections
    this.sectionProgress = (this.sectionProgress + 1) % this.totalSteps;

    // Change section when we complete all bars
    if (this.sectionProgress === 0) {
      this.currentSection = this.getNextSection();
    }

    // Get the appropriate patterns based on section and emotion
    const emotion = metrics.dominantEmotion === 'reassurance' ? 'worry' : metrics.dominantEmotion;
    const patterns = basePatterns[this.currentSection]?.[emotion] || basePatterns.entrance.worry;

    console.log('Section Progress:', this.sectionProgress);
    console.log('Current Section:', this.currentSection);
    console.log('Current Bar:', this.getCurrentBar());
    return {
      bangu: this.generateInstrumentPattern(
        metrics.emotionalIntensity,
        heartRateInfluence,
        'rhythmic',
        patterns.bangu
      ).map((hit, position) => ({
        hit,
        intensity: metrics.emotionalIntensity,
        isAccent: position % 4 === 0,
        tempo: mapHeartRateToTempo(heartRate, metrics.emotionalIntensity),
        position,
        sampleVariation: this.selectSample('bangu', metrics.emotionalIntensity, position % 4 === 0)
      })),
      daluo: this.generateInstrumentPattern(
        metrics.urgency,
        heartRateInfluence,
        'accent',
        patterns.daluo
      ).map((hit, position) => ({
        hit,
        intensity: metrics.urgency,
        isAccent: position % 4 === 0,
        tempo: mapHeartRateToTempo(heartRate, metrics.emotionalIntensity),
        position,
        sampleVariation: this.selectSample('daluo', metrics.urgency, position % 4 === 0)
      })),
      xiaoluo: this.generateInstrumentPattern(
        metrics.emotionalIntensity * 0.8,
        heartRateInfluence,
        'ornamental',
        patterns.xiaoluo
      ).map((hit, position) => ({
        hit,
        intensity: metrics.emotionalIntensity * 0.8,
        isAccent: position % 4 === 0,
        tempo: mapHeartRateToTempo(heartRate, metrics.emotionalIntensity),
        position,
        sampleVariation: this.selectSample('xiaoluo', metrics.emotionalIntensity * 0.8, position % 4 === 0)
      })),
      nanbo: this.generateInstrumentPattern(
        metrics.urgency * 0.6,
        heartRateInfluence,
        'punctuation',
        patterns.nanbo
      ).map((hit, position) => ({
        hit,
        intensity: metrics.urgency * 0.6,
        isAccent: position % 4 === 0,
        tempo: mapHeartRateToTempo(heartRate, metrics.emotionalIntensity),
        position,
        sampleVariation: this.selectSample('nanbo', metrics.urgency * 0.6, position % 4 === 0)
      }))
    };
  }

  private getNextSection(): 'entrance' | 'emotional' | 'exit' {
    // Increment repetition count for current section
    this.sectionRepetitions[this.currentSection]++;

    // Check if current section should advance based on repetition count
    if (this.sectionRepetitions[this.currentSection] >= this.maxSectionCounts[this.currentSection]) {
      if (this.currentSection === 'entrance') {
        this.currentSection = 'emotional';
      } else if (this.currentSection === 'emotional') {
        this.currentSection = 'exit';
      }
      // Reset section progress when changing sections
      this.sectionProgress = 0;
    }

    return this.currentSection;
  }

  private selectSample(
    instrument: string,
    intensity: number,
    isAccent: boolean
  ): SampleMetadata {
    const samples = this.sampleCache[instrument];
    if (!samples?.length) {
      return {
        filename: '',
        instrument,
        characteristics: {
          amplitude: intensity,
          duration: 0.1,
          character: 'medium'
        }
      };
    }

    const targetAmplitude = isAccent ? intensity * 1.2 : intensity;
    const targetCharacter = intensity > 0.7 ? 'hard' :
                          intensity > 0.4 ? 'medium' : 'soft';

    return samples.reduce((best, current) => {
      if (!best || !current) return best || current;

      const currentDiff = Math.abs(current.characteristics.amplitude - targetAmplitude);
      const bestDiff = Math.abs(best.characteristics.amplitude - targetAmplitude);

      if (current.characteristics.character === targetCharacter && currentDiff < bestDiff) {
        return current;
      }
      return best;
    }, samples[0]);
  }

  private async initializeSampleCache(): Promise<void> {
    try {
      const response = await fetch('/api/sound');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const samplesMetadata: Record<string, SampleMetadata[]> = await response.json();
      this.sampleCache = samplesMetadata;
      this.isInitialized = true;

    } catch (error) {
      console.error('Failed to initialize sample cache:', error);
      this.sampleCache = {};
    }
  }

  constructor() {
    this.initializeSampleCache().catch(console.error);
  }
}

export type PatternMap = {
  [key in 'bangu' | 'daluo' | 'xiaoluo' | 'nanbo']: PatternContext[];
};
