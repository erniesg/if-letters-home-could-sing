'use client';

import { useState, useCallback } from 'react';
import { connectToBLEDevice, disconnectFromBLEDevice, handleHeartRateMeasurement } from '../../lib/ble';
import { HeartRateAnalyzer } from '../../lib/heartRate/utils';
import { AudioInitializerProps, InitializerStatus } from './types';
import AudioEngine from '../../lib/audio/AudioEngine';
import { PatternGenerator } from '../../lib/audio/patterns'; // Fixed import path

export default function AudioInitializer({ onHeartRateUpdate, onInitialized }: AudioInitializerProps) {
  const [device, setDevice] = useState<BluetoothDevice | null>(null);
  const [status, setStatus] = useState<InitializerStatus>({
    ble: 'idle',
    audio: 'idle'
  });
  const [heartRateAnalyzer] = useState(() => new HeartRateAnalyzer(10));

  const handleHeartRateChange = useCallback((event: Event) => {
    const newHeartRate = handleHeartRateMeasurement(event);
    if (newHeartRate !== null) {
      heartRateAnalyzer.addReading(newHeartRate);
      const avgRate = heartRateAnalyzer.getMovingAverage();
      console.log('Heart Rate Update:', { new: newHeartRate, avg: avgRate });
      onHeartRateUpdate(avgRate);
    }
  }, [heartRateAnalyzer, onHeartRateUpdate]);

  const initialize = async () => {
    try {
      // Initialize BLE
      setStatus(prev => ({ ...prev, ble: 'connecting' }));
      const bleDevice = await connectToBLEDevice();
      setDevice(bleDevice);

      const server = await bleDevice.gatt?.connect();
      const service = await server?.getPrimaryService('heart_rate');
      const characteristic = await service?.getCharacteristic('heart_rate_measurement');

      await characteristic?.startNotifications();
      characteristic?.addEventListener('characteristicvaluechanged', handleHeartRateChange);

      setStatus(prev => ({ ...prev, ble: 'connected' }));

      // Initialize Audio
      setStatus(prev => ({ ...prev, audio: 'loading' }));

      // Create temporary AudioEngine to check sample loading
      const tempEngine = new AudioEngine();
      const tempGenerator = new PatternGenerator();

      // Wait for both systems to be ready
      await Promise.all([
        new Promise<void>((resolve) => {
          const checkEngine = () => {
            if (tempEngine.isReady()) {
              resolve();
            } else {
              setTimeout(checkEngine, 100);
            }
          };
          checkEngine();
        }),
        new Promise<void>((resolve) => {
          const checkGenerator = () => {
            if (tempGenerator.isReady()) {
              resolve();
            } else {
              setTimeout(checkGenerator, 100);
            }
          };
          checkGenerator();
        })
      ]);

      setStatus(prev => ({ ...prev, audio: 'ready' }));
      onInitialized(true);

    } catch (error) {
      console.error('Initialization error:', error);
      setStatus({ ble: 'error', audio: 'error' });
      onInitialized(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-sm space-y-1">
        <div>BLE Status: {status.ble}</div>
        <div>Audio Status: {status.audio}</div>
      </div>

      {status.ble === 'idle' && (
        <button
          onClick={initialize}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full"
        >
          Initialize System
        </button>
      )}

      {status.audio === 'loading' && (
        <div className="text-center text-yellow-500">Loading audio samples...</div>
      )}
    </div>
  );
}
