export async function connectToBLEDevice() {
  console.log('Scanning for BLE devices...');
  try {
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ services: ['heart_rate'] }],
      optionalServices: ['device_information']
    });

    console.log('Selected device:', device.name);

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
    console.error('Error connecting to BLE device:', error);
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

    console.log('Received heart rate data:');
    console.log('  Flags:', flags.toString(2).padStart(8, '0'));
    console.log('  Heart Rate:', heartRate);

    // Log additional data if available
    let index = rate16Bits ? 3 : 2;
    if (flags & 0x4) {
      const contactStatus = value.getUint8(index);
      console.log('  Sensor Contact Status:', contactStatus ? 'Detected' : 'Not Detected');
      index++;
    }
    if (flags & 0x8) {
      const energyExpended = value.getUint16(index, true);
      console.log('  Energy Expended:', energyExpended);
      index += 2;
    }
    if (flags & 0x10) {
      const rrIntervals = [];
      while (index < value.byteLength) {
        rrIntervals.push(value.getUint16(index, true));
        index += 2;
      }
      console.log('  RR Intervals:', rrIntervals);
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
