'use client';

import { useState, useEffect } from 'react';
import { useAudioEngine } from '../../hooks/useAudioEngine';
import { basePatterns } from '../../lib/audio/patterns';

export default function OperaTestPage() {
  // 1. Define all state hooks
  const [isAudioInitialized, setIsAudioInitialized] = useState(false);
  const [heartRate, setHeartRate] = useState(80);
  const [letter, setLetter] = useState<1 | 2>(1);
  const [currentSection, setCurrentSection] = useState<'entrance' | 'emotional' | 'exit'>('entrance');

  // 2. Always use the audio engine hook, but control its effect internally
  const audioEngine = useAudioEngine(heartRate, letter, isAudioInitialized);

  // 3. Update current section when audio engine changes
  useEffect(() => {
    if (isAudioInitialized) {
      setCurrentSection(audioEngine);
    }
  }, [audioEngine, isAudioInitialized]);

  const initializeAudio = () => {
    setIsAudioInitialized(true);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Opera Pattern Test</h1>

      {!isAudioInitialized ? (
        <button
          onClick={initializeAudio}
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

          <div className="text-lg mb-4">
            Current Section: {currentSection}
          </div>
        </>
      )}
    </div>
  );
}
