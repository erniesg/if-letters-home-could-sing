import paramiko
import struct
import logging
import argparse
import os
from getpass import getpass

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
log = logging.getLogger('remouse')

def open_rm_inputs(*, address, key_path):
    log.debug(f"Connecting to input '{address}'")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        log.debug(f"Attempting to connect using SSH key: {key_path}")
        client.connect(
            address,
            username='root',
            key_filename=key_path,
            look_for_keys=True,
            disabled_algorithms=dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"])
        )
        log.debug("Connected successfully")
    except Exception as e:
        log.error(f"Failed to connect: {e}")
        return None

    log.debug("Detecting input devices...")
    stdin, stdout, stderr = client.exec_command('cat /proc/bus/input/devices')
    devices_info = stdout.read().decode('utf-8').strip()
    log.debug(f"Found devices info:\n{devices_info}")

    input_devices = {}
    for device in devices_info.split('\n\n'):
        if 'Handlers=event' in device:
            name = device.split('Name=')[1].split('"')[1]
            event_handler = device.split('Handlers=')[1].split('event')[1].split()[0]
            device_path = f"/dev/input/event{event_handler}"
            if 'Elan marker input' in name:
                input_devices['pen'] = device_path
            elif 'Elan touch input' in name:
                input_devices['touch'] = device_path
            elif 'Hall effect sensors' in name:
                input_devices['button'] = device_path

    log.debug(f"Detected devices: {input_devices}")

    streams = {}
    for device_type, device_path in input_devices.items():
        log.debug(f"Opening stream for {device_type} device: {device_path}")
        streams[device_type] = client.exec_command(f'cat {device_path}')[1]

    return streams

def capture_input(streams):
    log.info("Starting to capture input...")
    while True:
        for device_type, stream in streams.items():
            try:
                data = stream.read(16)
                if data:
                    e_time, e_millis, e_type, e_code, e_value = struct.unpack('2IHHi', data)
                    timestamp = e_time + e_millis / 1000000
                    log.info(f"{device_type} event: time={timestamp:.6f}, type={e_type}, code={e_code}, value={e_value}")

                    if device_type == "pen":
                        if e_type == 3:  # EV_ABS
                            if e_code == 0:
                                log.info(f"Pen X position: {e_value}")
                            elif e_code == 1:
                                log.info(f"Pen Y position: {e_value}")
                            elif e_code == 24:
                                log.info(f"Pen pressure: {e_value}")
                    elif device_type == "touch":
                        if e_type == 3:  # EV_ABS
                            if e_code == 53:
                                log.info(f"Touch X position: {e_value}")
                            elif e_code == 54:
                                log.info(f"Touch Y position: {e_value}")
                    elif device_type == "button":
                        if e_type == 1:  # EV_KEY
                            log.info(f"Button event: code={e_code}, value={e_value}")
            except Exception as e:
                log.error(f"Error reading from {device_type} stream: {e}")

def main():
    parser = argparse.ArgumentParser(description="Capture input from reMarkable tablet")
    parser.add_argument('--address', default='10.11.99.1', help="reMarkable IP address")
    parser.add_argument('--key', default=os.path.expanduser('~/.ssh/remarkable'), help="SSH private key file")
    args = parser.parse_args()

    streams = open_rm_inputs(address=args.address, key_path=args.key)
    if streams:
        capture_input(streams)
    else:
        log.error("Failed to open input streams. Exiting.")

if __name__ == "__main__":
    main()
