export async function connectToBLEDevice() {
  if (!navigator.bluetooth) {
    throw new Error('Bluetooth not available');
  }

  try {
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
    const service = await server.getPrimaryService('heart_rate');
    const characteristic = await service.getCharacteristic('heart_rate_measurement');
    await characteristic.startNotifications();
    characteristic.addEventListener('characteristicvaluechanged', handleHeartRateMeasurement);

    return device;
  } catch {
    throw new Error('BLE connection failed');
  }
}

function handleHeartRateMeasurement(event: Event) {
  const value = (event.target as BluetoothRemoteGATTCharacteristic).value;
  if (value && value.byteLength >= 2) {
    const flags = value.getUint8(0);
    const rate16Bits = flags & 0x1;
    if (rate16Bits && value.byteLength < 3) {
      return null;
    }
    let heartRate: number;
    if (rate16Bits) {
      heartRate = value.getUint16(1, true);
    } else {
      heartRate = value.getUint8(1);
    }

    return heartRate;
  }
  return null;
}

export function disconnectFromBLEDevice(device: BluetoothDevice) {
  if (device.gatt?.connected) {
    device.gatt.disconnect();
  }
}

export { handleHeartRateMeasurement };
