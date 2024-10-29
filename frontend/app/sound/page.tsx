'use client';

import { useState, useEffect } from 'react';
import { useAudioEngine } from '../../hooks/useAudioEngine';
import AudioInitializer from '../../components/AudioInitializer';
import { letters } from '../../lib/constants/letters'; // Import letters
import HeartRateVisualizer from '../../components/HeartRateVisualizer';
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

type InstrumentKey = keyof Pick<DebugInfo, 'bangu' | 'daluo' | 'xiaoluo' | 'nanbo'>;

export default function OperaTestPage() {
  // Group all state declarations at the top
  const [isAudioInitialized, setIsAudioInitialized] = useState(false);
  const [heartRate, setHeartRate] = useState(80);
  const [letter, setLetter] = useState<1 | 2>(1);
  const [currentSection, setCurrentSection] = useState<'entrance' | 'emotional' | 'exit'>('entrance');
  const [isManualFactorControl, setIsManualFactorControl] = useState(false);
  const [manualFactor, setManualFactor] = useState(1);
  const [debugInfo, setDebugInfo] = useState<DebugInfo>({
    currentBar: 0,
    barsInSection: 0,
    tempo: 0,
    isPlaying: false,
    bangu: false,
    daluo: false,
    xiaoluo: false,
    nanbo: false
  });

  const [showLetter, setShowLetter] = useState(false); // New state for showing the letter

  const engineState = useAudioEngine(
    heartRate,
    letter,
    isAudioInitialized,
    isManualFactorControl ? manualFactor : undefined
  );

  useEffect(() => {
    if (isAudioInitialized) {
      setCurrentSection(engineState.section);
      setDebugInfo(engineState.debug);

      // Check if the entrance section is finished
      if (engineState.section === 'emotional' && !showLetter) {
        setShowLetter(true);
      }
    }
  }, [engineState, isAudioInitialized]);

  const instruments: InstrumentKey[] = ['bangu', 'daluo', 'xiaoluo', 'nanbo'];

  const [isManualControl, setIsManualControl] = useState(false);
  const [manualHeartRate, setManualHeartRate] = useState(80);

  const handleHeartRateUpdate = (newRate: number) => {
    console.log('Heart Rate Updated:', newRate);
    if (!isManualControl) {
      setHeartRate(newRate);
    }
  };

  const [imageOpacity, setImageOpacity] = useState(0);

  useEffect(() => {
    if (isAudioInitialized && currentSection === 'entrance') {
      // Start fade in during entrance section
      const fadeInDuration = letters[letter].content.musicalMapping.sectionDurations.entrance;
      const startTime = Date.now();

      const fadeInterval = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / fadeInDuration, 1);
        setImageOpacity(progress);

        if (progress >= 1) {
          clearInterval(fadeInterval);
        }
      }, 16); // 60fps update

      return () => clearInterval(fadeInterval);
    }
  }, [isAudioInitialized, currentSection, letter]);

  // Add section display helper
  const getSectionDisplay = (section: 'entrance' | 'emotional' | 'exit') => {
    const displays = {
      entrance: 'Opening',
      emotional: 'Main Section',
      exit: 'Closing'
    };
    return displays[section];
  };

  // Add this section to the JSX where you want to display the section info
  const sectionDisplay = (
    <div className="mb-4 text-center">
      <div className="text-sm font-medium text-gray-400">Current Section</div>
      <div className="text-xl font-bold text-white">
        {getSectionDisplay(currentSection)}
      </div>
      <div className="text-sm text-gray-500">
        Bar {debugInfo.currentBar + 1} of {debugInfo.barsInSection}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col items-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white">
      <h1 className="text-4xl font-bold mb-8 p-4">Opera Pattern Test</h1>

      {!isAudioInitialized ? (
        <AudioInitializer
          onHeartRateUpdate={handleHeartRateUpdate}
          onInitialized={setIsAudioInitialized}
        />
      ) : (
        <div className="flex flex-col items-center w-full max-w-5xl px-4">

          <HeartRateVisualizer
            heartRate={heartRate}
            letter={letter}
          />
          <div className="mb-8 space-y-4 w-64">
            <div className="flex items-center justify-between w-64">
              <div className="text-sm font-medium">
                Factor: {isManualFactorControl ? manualFactor.toFixed(2) : 'Auto'}
              </div>
              <button
                onClick={() => setIsManualFactorControl(!isManualFactorControl)}
                className={`px-3 py-1 rounded text-sm ${
                  isManualFactorControl
                    ? 'bg-yellow-600 hover:bg-yellow-700'
                    : 'bg-gray-600 hover:bg-gray-700'
                }`}
              >
                {isManualFactorControl ? 'Manual Factor' : 'Auto Factor'}
              </button>
            </div>

            {isManualFactorControl && (
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={manualFactor}
                onChange={(e) => setManualFactor(Number(e.target.value))}
                className="w-64"
              />
            )}

            <div className="flex items-center justify-between w-64">
              {/* <div className="text-sm font-medium">
                Heart Rate: {heartRate} BPM
              </div> */}
              <button
                onClick={() => setIsManualControl(!isManualControl)}
                className={`px-3 py-1 rounded text-sm ${
                  isManualControl
                    ? 'bg-yellow-600 hover:bg-yellow-700'
                    : 'bg-gray-600 hover:bg-gray-700'
                }`}
              >
                {isManualControl ? 'Manual Control' : 'BLE Sync'}
              </button>
            </div>

            <input
              type="range"
              min="60"
              max="120"
              value={isManualControl ? manualHeartRate : heartRate}
              onChange={(e) => {
                const value = Number(e.target.value);
                setManualHeartRate(value);
                if (isManualControl) {
                  setHeartRate(value);
                }
              }}
              className="w-64"
              disabled={!isManualControl}
            />
          </div>

          <button
            onClick={() => setLetter(letter === 1 ? 2 : 1)}
            className="mb-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Switch to Letter {letter === 1 ? '2' : '1'}
          </button>

          {/* Image container with absolute max dimensions */}
          {showLetter && (
            <div
              className="relative flex items-center justify-center w-[200px] h-[200px]"
              style={{
                opacity: imageOpacity,
                transition: 'opacity 0.1s linear'
              }}
            >
              <img
                src={letters[letter].path}
                alt={`Letter ${letter}`}
                style={{
                  width: '30%',  // Force width to match container
                  height: '30%', // Force height to match container
                  objectFit: 'contain'  // Maintain aspect ratio within bounds
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
