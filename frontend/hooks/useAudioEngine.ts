import { useEffect, useRef, useState } from 'react';
import AudioEngine from '../lib/audio/AudioEngine';
import { PatternGenerator, PatternMap, PatternContext, mapHeartRateToTempo } from '../lib/audio/patterns';
import { SampleMetadata } from '../lib/audio/sampleAnalysis';

interface PlaySoundOptions {
  intensity: number;
  isAccent: boolean;
  tempo: number;
  position: number;
  sampleVariation?: SampleMetadata;
}

interface DebugInfo {
  currentBar: number;
  barsInSection: number;
  tempo: number;
  isPlaying: boolean;
  bangu: boolean;
  daluo: boolean;
  xiaoluo: boolean;
  nanbo: boolean;
}

interface AudioEngineState {
  section: 'entrance' | 'emotional' | 'exit';
  debug: DebugInfo;
}

export function useAudioEngine(
  heartRate: number,
  letter: 1 | 2,
  isInitialized: boolean,
  manualFactor?: number
): AudioEngineState {
  const engineRef = useRef<AudioEngine | null>(null);
  const generatorRef = useRef<PatternGenerator | null>(null);
  const patternRef = useRef<PatternMap | null>(null);
  const stepRef = useRef<number>(0);
  const [currentSection, setCurrentSection] = useState<'entrance' | 'emotional' | 'exit'>('entrance');
  const [debug, setDebug] = useState<DebugInfo>({
    currentBar: 0,
    barsInSection: 8,
    tempo: 0,
    isPlaying: false,
    bangu: false,
    daluo: false,
    xiaoluo: false,
    nanbo: false
  });

  // Add initialization check state
  const [isFullyInitialized, setIsFullyInitialized] = useState(false);

  // Initialize audio engine
  useEffect(() => {
    if (isInitialized && !engineRef.current) {
      const initializeAudio = async () => {
        try {
          engineRef.current = new AudioEngine();
          generatorRef.current = new PatternGenerator();

          // Wait for both systems to be fully ready
          await Promise.all([
            new Promise<void>((resolve) => {
              const checkEngine = () => {
                if (engineRef.current?.isReady()) {
                  resolve();
                } else {
                  setTimeout(checkEngine, 100);
                }
              };
              checkEngine();
            }),
            new Promise<void>((resolve) => {
              const checkGenerator = () => {
                if (generatorRef.current?.isReady()) {
                  resolve();
                } else {
                  setTimeout(checkGenerator, 100);
                }
              };
              checkGenerator();
            })
          ]);

          setIsFullyInitialized(true);
        } catch (error) {
          console.error('Failed to initialize audio:', error);
        }
      };

      initializeAudio();
    }

    return () => {
      if (engineRef.current) {
        engineRef.current.dispose();
      }
    };
  }, [isInitialized]);

  // Handle pattern generation and playback
  useEffect(() => {
    if (!isFullyInitialized || !engineRef.current || !generatorRef.current) return;

    // Fade in when starting
    engineRef.current.fadeIn(2);

    const factor = manualFactor !== undefined ? manualFactor : 0.5;
    const tempo = mapHeartRateToTempo(heartRate, factor);
    console.log(`Tempo: ${tempo}bpm | Heart Rate: ${heartRate}bpm | Factor: ${factor}`);
    setDebug(prev => ({
      ...prev,
      tempo,
      isPlaying: true
    }));

    const stepDuration = 60 / tempo / 4;

    try {
      patternRef.current = generatorRef.current.generatePattern(letter, heartRate);
    } catch (error) {
      console.error('Failed to generate pattern:', error);
      return;
    }

    const interval = setInterval(() => {
      if (!patternRef.current || !engineRef.current || !generatorRef.current) return;

      const currentBar = Math.floor(stepRef.current / 8);
      const instrumentStates = {} as Record<string, boolean>;

      Object.entries(patternRef.current).forEach(([instrument, pattern]) => {
        const hit = pattern[stepRef.current];
        instrumentStates[instrument] = !!hit?.hit;

        if (hit?.hit) {
          // Convert SampleMetadata to AudioEngineMetadata
          const playOptions: PlaySoundOptions = {
            intensity: hit.intensity,
            isAccent: hit.isAccent,
            tempo: hit.tempo,
            position: hit.position,
            sampleVariation: hit.sampleVariation
          };

          engineRef.current?.playSound(instrument, playOptions);
        }
      });

      setDebug(prev => ({
        ...prev,
        currentBar,
        ...instrumentStates
      }));

      stepRef.current = (stepRef.current + 1) % 8;

      if (stepRef.current === 0) {
        try {
          patternRef.current = generatorRef.current.generatePattern(letter, heartRate);
          const nextSection = generatorRef.current.getCurrentSection();
          if (nextSection !== currentSection) {
            setCurrentSection(nextSection);
          }
        } catch (error) {
          console.error('Failed to update pattern:', error);
        }
      }

      console.log('Step:', stepRef.current);
      console.log('Current Bar:', currentBar);
    }, stepDuration * 1000);

    return () => {
      if (engineRef.current) {
        engineRef.current.fadeOut(1);
        setTimeout(() => {
          clearInterval(interval);
          setDebug(prev => ({ ...prev, isPlaying: false }));
        }, 1000);
      }
    };
  }, [heartRate, letter, isFullyInitialized, manualFactor]);

  return {
    section: currentSection,
    debug
  };
}
