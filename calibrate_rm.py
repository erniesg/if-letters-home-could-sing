import paramiko
import struct
import logging
import argparse
import os
import time
from pynput.mouse import Button, Controller
import pyautogui
import json

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
log = logging.getLogger('remouse')

class RemarkableCalibrator:
    def __init__(self, address, key=None):
        log.info("Initializing RemarkableCalibrator")
        self.client = self._connect(address, key)
        self.width, self.height = 1872, 2404  # Paper Pro dimensions
        self.inputs = self._open_rm_inputs()
        self.calibration_data = {
            "hover": [],
            "touch": [],
            "press": [],
            "move": []
        }

    def _connect(self, address, key):
        log.info(f"Connecting to {address}")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            key_path = key or os.path.expanduser('~/.ssh/remarkable')
            log.info(f"Attempting to connect using SSH key: {key_path}")
            client.connect(
                address,
                username='root',
                key_filename=key_path,
                look_for_keys=True,
                disabled_algorithms=dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"])
            )
            log.info("Connected successfully using SSH key")
        except Exception as e:
            log.error(f"Failed to connect with SSH key: {e}")
            raise
        return client

    def _open_rm_inputs(self):
        devices = {
            'pen': '/dev/input/event2'  # Elan marker input
        }
        streams = {}
        for device_type, device_path in devices.items():
            log.debug(f'Opening {device_type} device: {device_path}')
            streams[device_type] = self.client.exec_command(f'cat {device_path}')[1]
        return streams

    def calibrate(self):
        print("\n=== Calibration Process ===")
        self._calibrate_hover()
        self._calibrate_touch()
        self._calibrate_press()
        self._calibrate_move()
        self._save_calibration_data()

    def _calibrate_hover(self):
        print("\nHover Test:")
        print("1. Hold the pen about 1cm above the tablet surface.")
        print("2. Move the pen slowly across the surface without touching it.")
        print("3. This test will run for 5 seconds.")
        input("Press Enter to start the hover test...")
        self._capture_events(5, "hover")

    def _calibrate_touch(self):
        print("\nTouch Test:")
        print("1. Gently rest the pen on the tablet surface without pressing.")
        print("2. Hold it still for 5 seconds.")
        input("Press Enter to start the touch test...")
        self._capture_events(5, "touch")

    def _calibrate_press(self):
        print("\nPress Test:")
        print("1. Press the pen firmly against the tablet surface.")
        print("2. Vary the pressure from light to hard over 5 seconds.")
        input("Press Enter to start the press test...")
        self._capture_events(5, "press")

    def _calibrate_move(self):
        print("\nMovement Test:")
        print("1. Draw a few straight lines and curves on the tablet.")
        print("2. This test will run for 10 seconds.")
        input("Press Enter to start the movement test...")
        self._capture_events(10, "move")

    def _capture_events(self, duration, test_type):
        start_time = time.time()
        event_size = struct.calcsize('llHHI')

        print(f"Capturing {test_type} events for {duration} seconds...")
        while time.time() - start_time < duration:
            for device_type, stream in self.inputs.items():
                if stream.channel.recv_ready():
                    data = stream.read(event_size)
                    if len(data) == event_size:
                        timestamp, _, e_type, e_code, e_value = struct.unpack('llHHI', data)
                        event = {"type": e_type, "code": e_code, "value": e_value}
                        self.calibration_data[test_type].append(event)
                        log.debug(f"{test_type} event: {event}")
        print(f"{test_type.capitalize()} test completed.")

    def _save_calibration_data(self):
        filename = "remarkable_calibration_data.json"
        with open(filename, 'w') as f:
            json.dump(self.calibration_data, f, indent=2)
        print(f"\nCalibration data saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description="Calibrate reMarkable Paper Pro pen input")
    parser.add_argument('--address', default='10.11.99.1', help="reMarkable IP address")
    parser.add_argument('--key', default=os.path.expanduser('~/.ssh/remarkable'), help="SSH private key file")
    args = parser.parse_args()

    try:
        calibrator = RemarkableCalibrator(args.address, args.key)
        print(f"Connected to reMarkable Paper Pro. Screen size: {calibrator.width}x{calibrator.height}")
        calibrator.calibrate()
    except KeyboardInterrupt:
        print("\nCalibration stopped by user.")
    except Exception as e:
        log.error(f"An error occurred: {e}")
        import traceback
        log.debug(traceback.format_exc())
    finally:
        print("Calibration process completed.")

if __name__ == "__main__":
    main()
