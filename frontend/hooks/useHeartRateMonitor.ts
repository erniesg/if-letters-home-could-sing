import { useState, useEffect } from 'react';
import { HeartRateAnalyzer } from '../lib/heartRate/utils';

export function useHeartRateMonitor(isEnabled: boolean) {
  const [currentRate, setCurrentRate] = useState(0);
  const [movingAverage, setMovingAverage] = useState(0);
  const [analyzer] = useState(() => new HeartRateAnalyzer());

  const handleHeartRateUpdate = (rate: number) => {
    setCurrentRate(rate);
    analyzer.addReading(rate);
    setMovingAverage(analyzer.getMovingAverage());

    console.log('Heart Rate Update:', {
      current: rate,
      movingAverage: analyzer.getMovingAverage(),
      timestamp: Date.now()
    });
  };

  return {
    currentRate,
    movingAverage,
    handleHeartRateUpdate
  };
}
