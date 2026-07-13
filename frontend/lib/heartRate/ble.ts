export async function connectToBLEDevice() {
  console.log('Starting BLE connection process...');

  // Check if Bluetooth is available
  if (!navigator.bluetooth) {
    console.error('Bluetooth not available');
    throw new Error('Bluetooth not available');
  }

  try {
    console.log('Requesting Bluetooth device...');
    const device = await navigator.bluetooth.requestDevice({
      filters: [
        { services: ['heart_rate'] },
        { namePrefix: 'WHOOP' }  // Add WHOOP specific filter
      ],
      optionalServices: ['device_information']
    });

    if (!device.gatt) {
      throw new Error('Bluetooth GATT is unavailable');
    }
    const server = await device.gatt.connect();
    console.log('Connected to GATT server');

    const service = await server.getPrimaryService('heart_rate');
    console.log('Heart rate service obtained');

    const characteristic = await service.getCharacteristic('heart_rate_measurement');
    console.log('Heart rate measurement characteristic obtained');

    await characteristic.startNotifications();
    console.log('Notifications started');

    characteristic.addEventListener('characteristicvaluechanged', handleHeartRateMeasurement);

    console.log('BLE device connection setup complete');
    return device;
  } catch (error) {
    console.error('Unable to connect to BLE device');
    throw error;
  }
}

function handleHeartRateMeasurement(event: Event) {
  const value = (event.target as BluetoothRemoteGATTCharacteristic).value;
  if (value) {
    const flags = value.getUint8(0);
    const rate16Bits = flags & 0x1;
    let heartRate: number;
    if (rate16Bits) {
      heartRate = value.getUint16(1, true);
    } else {
      heartRate = value.getUint8(1);
    }

    return heartRate;
  } else {
    console.warn('Received empty value from heart rate measurement');
    return null;
  }
}

export function disconnectFromBLEDevice(device: BluetoothDevice) {
  if (device.gatt?.connected) {
    console.log('Disconnecting from BLE device...');
    device.gatt.disconnect();
    console.log('Disconnected from BLE device');
  } else {
    console.log('Device already disconnected or not connected');
  }
}

export { handleHeartRateMeasurement };
