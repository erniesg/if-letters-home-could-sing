'use client';

import { useState, useEffect } from 'react';
import { useAudioEngine } from '../../hooks/useAudioEngine';

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
  const [isAudioInitialized, setIsAudioInitialized] = useState(false);
  const [heartRate, setHeartRate] = useState(80);
  const [letter, setLetter] = useState<1 | 2>(1);
  const [currentSection, setCurrentSection] = useState<'entrance' | 'emotional' | 'exit'>('entrance');
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

  const engineState = useAudioEngine(heartRate, letter, isAudioInitialized);

  useEffect(() => {
    if (isAudioInitialized) {
      setCurrentSection(engineState.section);
      setDebugInfo(engineState.debug);
    }
  }, [engineState, isAudioInitialized]);

  const instruments: InstrumentKey[] = ['bangu', 'daluo', 'xiaoluo', 'nanbo'];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Opera Pattern Test</h1>

      {!isAudioInitialized ? (
        <button
          onClick={() => setIsAudioInitialized(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full mb-8"
        >
          Initialize Audio
        </button>
      ) : (
        <>
          <div className="mb-8">
            <label className="block text-sm font-medium mb-2">
              Heart Rate: {heartRate} BPM
            </label>
            <input
              type="range"
              min="60"
              max="120"
              value={heartRate}
              onChange={(e) => setHeartRate(Number(e.target.value))}
              className="w-64"
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
            <div>Current Bar: {debugInfo.currentBar} / {debugInfo.barsInSection}</div>
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
