'use client';

import { useState, useEffect } from 'react';
import { useAudioEngine } from '../../hooks/useAudioEngine';
import AudioInitializer from '../../components/AudioInitializer';

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

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Opera Pattern Test</h1>

      {!isAudioInitialized ? (
        <AudioInitializer
          onHeartRateUpdate={handleHeartRateUpdate}
          onInitialized={setIsAudioInitialized}
        />
      ) : (
        <>
          <div className="mb-8 space-y-4">
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
              <div className="text-sm font-medium">
                Heart Rate: {heartRate} BPM
              </div>
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

          <div className="text-lg space-y-2 mb-8">
            <div>Current Section: {currentSection}</div>
            <div>Current Bar: {Math.floor(debugInfo.currentBar / 16)} / {4}</div>
            <div>Step: {debugInfo.currentBar % 16} / 16</div>
            <div>Tempo: {debugInfo.tempo} BPM</div>
            <div>Status: {debugInfo.isPlaying ? 'Playing' : 'Stopped'}</div>
          </div>

          <div className="grid grid-cols-4 gap-4 text-center">
            {instruments.map(instrument => (
              <div
                key={instrument}
                className={`p-2 rounded ${debugInfo[instrument] ? 'bg-blue-500' : 'bg-gray-700'}`}
              >
                {instrument}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
