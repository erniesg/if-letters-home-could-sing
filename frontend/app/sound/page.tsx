'use client';

import { useState, useEffect } from 'react';
import { useAudioEngine } from '../../hooks/useAudioEngine';
import { letterPatterns } from '../../lib/audio/patterns';

export default function OperaTestPage() {
  const [heartRate, setHeartRate] = useState(80);
  const [letter, setLetter] = useState<1 | 2>(1);

  // Initialize audio engine with current heartRate and letter
  useAudioEngine(heartRate, letter);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Opera Pattern Test</h1>

      {/* Heart Rate Control */}
      <div className="mb-8">
        <label className="block text-sm font-medium mb-2">Heart Rate: {heartRate}</label>
        <input
          type="range"
          min="60"
          max="120"
          value={heartRate}
          onChange={(e) => setHeartRate(Number(e.target.value))}
          className="w-64"
        />
      </div>

      {/* Letter Pattern Selection */}
      <div className="mb-8">
        <button
          onClick={() => setLetter(letter === 1 ? 2 : 1)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full"
        >
          Switch to Letter {letter === 1 ? '2' : '1'}
        </button>
      </div>

      {/* Pattern Visualization */}
      <div className="grid grid-cols-16 gap-1 p-4 bg-gray-800 rounded-lg">
        {Object.entries(letterPatterns[`letter${letter}`]).map(([instrument, pattern]) => (
          <div key={instrument} className="flex items-center mb-2">
            <span className="w-20 text-sm">{instrument}</span>
            <div className="flex gap-1">
              {pattern.map((hit, i) => (
                <div
                  key={i}
                  className={`w-6 h-6 rounded ${
                    hit ? 'bg-blue-500' : 'bg-gray-600'
                  }`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
