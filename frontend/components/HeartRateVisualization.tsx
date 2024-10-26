'use client';

import { useState, useEffect } from 'react';

interface Cycle {
  score: {
    average_heart_rate: number;
  };
}

interface HeartRateVisualizationProps {
  cycles: Cycle[];
  currentHeartRate: number;
}

const HeartRateVisualization: React.FC<HeartRateVisualizationProps> = ({ cycles, currentHeartRate }) => {
  const [color, setColor] = useState('#ef4444');
  const [displayedHeartRate, setDisplayedHeartRate] = useState(currentHeartRate);
  const [cycleIndex, setCycleIndex] = useState(0);

  useEffect(() => {
    if (cycles.length === 0) return;

    const interval = setInterval(() => {
      setCycleIndex((prevIndex) => (prevIndex + 1) % cycles.length);
    }, 2000); // Change cycle every 2 seconds

    return () => clearInterval(interval);
  }, [cycles]);

  useEffect(() => {
    if (cycles.length === 0) return;

    const cycleHeartRate = cycles[cycleIndex].score.average_heart_rate;
    setDisplayedHeartRate(cycleHeartRate);
    setColor(getColorForHeartRate(cycleHeartRate));
  }, [cycleIndex, cycles]);

  const size = getSizeForHeartRate(displayedHeartRate);

  return (
    <div className="relative">
      <div
        className="rounded-full flex items-center justify-center transition-all duration-1000"
        style={{
          width: size,
          height: size,
          backgroundColor: color,
        }}
      >
        <span className="text-white text-3xl md:text-4xl font-bold">{displayedHeartRate}</span>
      </div>
      <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-4 text-xl">
        BPM
      </div>
    </div>
  );
};

function getColorForHeartRate(heartRate: number): string {
  if (heartRate < 60) return '#3b82f6'; // blue for low heart rate
  if (heartRate < 100) return '#10b981'; // green for normal heart rate
  if (heartRate < 140) return '#f59e0b'; // yellow for elevated heart rate
  return '#ef4444'; // red for high heart rate
}

function getSizeForHeartRate(heartRate: number): number {
  const minSize = 150;
  const maxSize = 250;
  const minRate = 40;
  const maxRate = 200;

  return Math.min(maxSize, Math.max(minSize,
    minSize + (heartRate - minRate) / (maxRate - minRate) * (maxSize - minSize)
  ));
}

export default HeartRateVisualization;
