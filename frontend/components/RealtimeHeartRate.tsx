import React from 'react';

interface RealtimeHeartRateProps {
  heartRate: number;
}

const RealtimeHeartRate: React.FC<RealtimeHeartRateProps> = ({ heartRate }) => {
  const getColorForHeartRate = (rate: number): string => {
    if (rate < 60) return '#3b82f6'; // blue for low heart rate
    if (rate < 100) return '#10b981'; // green for normal heart rate
    if (rate < 140) return '#f59e0b'; // yellow for elevated heart rate
    return '#ef4444'; // red for high heart rate
  };

  const color = getColorForHeartRate(heartRate);

  return (
    <div className="relative">
      <div
        className="rounded-full flex items-center justify-center transition-all duration-300 animate-pulse"
        style={{
          width: '200px',
          height: '200px',
          backgroundColor: color,
          animationDuration: `${60 / heartRate}s`,
        }}
      >
        <span className="text-white text-4xl font-bold">{heartRate}</span>
      </div>
      <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-4 text-xl">
        BPM
      </div>
    </div>
  );
};

export default RealtimeHeartRate;
