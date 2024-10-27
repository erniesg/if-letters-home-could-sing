'use client';

import { useState, useCallback } from 'react';
import RealtimeHeartRate from '../../components/RealtimeHeartRate';
import { connectToBLEDevice, disconnectFromBLEDevice, handleHeartRateMeasurement } from '../../lib/ble';

export default function RealtimeHRPage() {
  const [heartRate, setHeartRate] = useState(0);
  const [device, setDevice] = useState<BluetoothDevice | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const handleHeartRateChange = useCallback((event: Event) => {
    const newHeartRate = handleHeartRateMeasurement(event);
    if (newHeartRate !== null) {
      setHeartRate(newHeartRate);
    }
  }, []);

  const connectToBLE = async () => {
    try {
      const connectedDevice = await connectToBLEDevice();
      setDevice(connectedDevice);

      const server = await connectedDevice.gatt?.connect();
      const service = await server?.getPrimaryService('heart_rate');
      const characteristic = await service?.getCharacteristic('heart_rate_measurement');

      await characteristic?.startNotifications();
      characteristic?.addEventListener('characteristicvaluechanged', handleHeartRateChange);

      setIsConnected(true);
    } catch (error) {
      console.error('Error setting up BLE connection:', error);
    }
  };

  const disconnectFromBLE = () => {
    if (device) {
      disconnectFromBLEDevice(device);
      setIsConnected(false);
      setHeartRate(0);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Real-time Heart Rate</h1>
      {!isConnected ? (
        <button
          onClick={connectToBLE}
          className="mb-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
        >
          Connect to BLE Device
        </button>
      ) : (
        <button
          onClick={disconnectFromBLE}
          className="mb-8 bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
        >
          Disconnect
        </button>
      )}
      <RealtimeHeartRate heartRate={heartRate} />
    </div>
  );
}
