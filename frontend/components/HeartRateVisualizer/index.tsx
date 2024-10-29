'use client';

import { useEffect, useState } from 'react';
import { letters } from '../../lib/constants/letters';

interface HeartRateVisualizerProps {
  heartRate: number;
  letter: 1 | 2;
}

export default function HeartRateVisualizer({ heartRate, letter }: HeartRateVisualizerProps) {
  const [averageHeartRate, setAverageHeartRate] = useState(heartRate);

  useEffect(() => {
    setAverageHeartRate(prev => {
      const alpha = 0.1;
      return prev * (1 - alpha) + heartRate * alpha;
    });
  }, [heartRate]);

  const size = Math.max(80, Math.min(300, (heartRate - 60) * (220 / 60) + 80));
  const colors = {
    1: letters[1].color,
    2: letters[2].color
  };
  const opacity = Math.max(0.3, Math.min(1, (averageHeartRate - 60) * (0.7 / 60) + 0.3));
  const scaleFactor = 1 + (heartRate - 80) / 80;

  return (
    <div className="relative w-[400px] h-[400px] flex items-center justify-center mb-8">
      <div
        className="absolute rounded-full transition-all duration-300 ease-in-out"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          backgroundColor: colors[letter],
          opacity: opacity,
          transform: `scale(${scaleFactor})`,
          boxShadow: `0 0 ${size/3}px ${colors[letter]}`,
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        }}
      />
      <div className="relative z-10">
        <div
          className="text-white text-4xl font-bold flex flex-col items-center"
          style={{ textShadow: '0 0 10px rgba(0,0,0,0.5)' }}
        >
          <span className="text-5xl mb-1">{Math.round(heartRate)}</span>
          <span className="text-xl">BPM</span>
        </div>
      </div>
    </div>
  );
}
