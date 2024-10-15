import paramiko
import struct
import logging
import argparse
import os
import time
from pynput.mouse import Button, Controller
import pyautogui

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
log = logging.getLogger('remouse')

class RemarkableDrawer:
    def __init__(self, address, key=None):
        log.info("Initializing RemarkableDrawer")
        self.client = self._connect(address, key)
        self.rm_width, self.rm_height = 0, 0  # We'll determine these dynamically
        self.mac_width, self.mac_height = pyautogui.size()
        self.mouse = Controller()
        self.raw_x = self.raw_y = 0
        self.mapped_x = self.mapped_y = 0
        self.is_touching = False
        self.inputs = self._open_rm_inputs()
        self.pressure_threshold = 900  # Adjust based on calibration data

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

    def capture_input(self, duration=60):
        log.info(f"Capturing input for {duration} seconds")
        event_size = struct.calcsize('llHHI')
        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                for device_type, stream in self.inputs.items():
                    if stream.channel.recv_ready():
                        data = stream.read(event_size)
                        if len(data) == event_size:
                            timestamp, _, e_type, e_code, e_value = struct.unpack('llHHI', data)
                            self._handle_event(e_type, e_code, e_value)
                        elif len(data) > 0:
                            log.warning(f"Received unexpected data size from {device_type}: {len(data)} bytes")
                time.sleep(0.001)  # Small sleep to prevent CPU hogging
        except KeyboardInterrupt:
            log.info("Capture stopped by user")
        except Exception as e:
            log.error(f"Error capturing input: {e}")
        finally:
            log.info("Finished capturing input")
            if self.rm_width and self.rm_height:
                log.info(f"Estimated reMarkable Paper Pro resolution: {self.rm_width}x{self.rm_height}")

    def _handle_event(self, e_type, e_code, e_value):
        if e_type == 3:  # EV_ABS
            if e_code == 24:  # ABS_PRESSURE
                self._handle_pressure(e_value)
            elif self.is_touching:
                if e_code == 0:  # ABS_X
                    self.raw_x = e_value
                    self.rm_width = max(self.rm_width, e_value)
                    self.mapped_x = self._map_coordinate(e_value, 0, self.rm_width, 0, self.mac_width)
                elif e_code == 1:  # ABS_Y
                    self.raw_y = e_value
                    self.rm_height = max(self.rm_height, e_value)
                    self.mapped_y = self._map_coordinate(e_value, 0, self.rm_height, 0, self.mac_height)
        elif e_type == 0:  # EV_SYN
            self._update_mouse_position()

    def _handle_pressure(self, pressure):
        if pressure > self.pressure_threshold and not self.is_touching:
            self.is_touching = True
            self.mouse.press(Button.left)
            log.debug("Pen touched the surface")
        elif pressure <= self.pressure_threshold and self.is_touching:
            self.is_touching = False
            self.mouse.release(Button.left)
            log.debug("Pen lifted from surface")

    def _update_mouse_position(self):
        if self.is_touching:
            self.mouse.position = (self.mapped_x, self.mapped_y)
            log.debug(f"Raw coordinates: ({self.raw_x}, {self.raw_y})")
            log.debug(f"Mouse moved to: ({self.mapped_x}, {self.mapped_y})")

    def _map_coordinate(self, value, in_min, in_max, out_min, out_max):
        return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def main():
    parser = argparse.ArgumentParser(description="Map reMarkable Paper Pro input to computer mouse")
    parser.add_argument('--address', default='10.11.99.1', help="reMarkable IP address")
    parser.add_argument('--key', default=os.path.expanduser('~/.ssh/remarkable'), help="SSH private key file")
    parser.add_argument('--duration', type=int, default=10, help="Duration to capture input (seconds)")
    args = parser.parse_args()

    try:
        drawer = RemarkableDrawer(args.address, args.key)
        print(f"Connected to reMarkable Paper Pro.")
        print(f"Mac screen size: {drawer.mac_width}x{drawer.mac_height}")

        print(f"Mapping reMarkable input to mouse for {args.duration} seconds...")
        print("Start drawing on your reMarkable Paper Pro device.")
        print("Press Ctrl+C to stop the script.")

        drawer.capture_input(args.duration)
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        log.error(f"An error occurred: {e}")
        import traceback
        log.debug(traceback.format_exc())
    finally:
        print("Script execution completed.")

if __name__ == "__main__":
    main()
