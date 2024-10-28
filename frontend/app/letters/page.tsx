'use client';

import { useState, useEffect } from 'react';
import { letters } from '../../lib/constants/letters';
import LetterReveal from '../../components/LetterReveal';
import { useAudioEngine } from '../../hooks/useAudioEngine';

export default function LettersGalleryPage() {
  const [isAudioInitialized, setIsAudioInitialized] = useState(false);
  const [heartRate, setHeartRate] = useState(80);
  const [currentLetter, setCurrentLetter] = useState<1 | 2>(1);
  const [isLetterVisible, setIsLetterVisible] = useState(false);

  useEffect(() => {
    // Initialize Lenis on client-side only
    const initLenis = async () => {
      const Lenis = (await import('@studio-freight/lenis')).default;
      const { addEffect } = await import('@react-three/fiber');

      const lenis = new Lenis();
      addEffect((t) => lenis.raf(t));
    };

    initLenis();
  }, []);

  const audioEngine = useAudioEngine(heartRate, currentLetter, isAudioInitialized);

  const handleInitialize = () => {
    setIsAudioInitialized(true);
    setIsLetterVisible(true);
  };


  return (
    <>
      <main className="min-h-screen bg-black text-white">
        <div className="frame p-8">
          <h1 className="text-4xl font-bold mb-8">Family Letters</h1>
          <div className="flex gap-4 mb-8">
            <button
              onClick={handleInitialize}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
              disabled={isAudioInitialized}
            >
              {isAudioInitialized ? 'Experience Started' : 'Begin Experience'}
            </button>
            {isAudioInitialized && (
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="60"
                  max="120"
                  value={heartRate}
                  onChange={(e) => setHeartRate(Number(e.target.value))}
                  className="w-32"
                />
                <span>{heartRate} BPM</span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 p-8">
          {Object.entries(letters).map(([id, letter]) => (
            <figure key={id} className="relative">
              <div className="aspect-[3/4] w-full">
                <LetterReveal
                  url={letter.path}
                  isVisible={isLetterVisible && currentLetter === Number(id)}
                  type={0}
                  className="w-full h-full"
                />
              </div>
              <figcaption className="mt-4 text-center">
                <h3 className="text-xl font-bold">{letter.type}</h3>
                <button
                  onClick={() => setCurrentLetter(Number(id) as 1 | 2)}
                  className="mt-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                  disabled={currentLetter === Number(id)}
                >
                  View This Letter
                </button>
              </figcaption>
            </figure>
          ))}
        </div>
      </main>
    </>
  );
}
