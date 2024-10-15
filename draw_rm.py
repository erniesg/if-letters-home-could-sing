import paramiko
import struct
import logging
import argparse
import os
import time
from PIL import Image, ImageDraw

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
log = logging.getLogger('remouse')

class RemarkableDrawer:
    def __init__(self, address, key=None):
        log.info("Initializing RemarkableDrawer")
        self.client = self._connect(address, key)
        self.rm_width, self.rm_height = 15725, 20951  # reMarkable Paper Pro dimensions
        self.raw_x = self.raw_y = 0
        self.is_touching = False
        self.inputs = self._open_rm_inputs()
        self.current_stroke = []
        self.strokes = []
        self.pressure_threshold = 600
        self.last_pen_lift_time = 0
        self.image = Image.new('RGB', (self.rm_width, self.rm_height), color='white')
        self.draw = ImageDraw.Draw(self.image)

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

    def capture_input(self):
        log.info("Starting continuous input capture")
        event_size = struct.calcsize('llHHI')

        try:
            while True:
                for device_type, stream in self.inputs.items():
                    if stream.channel.recv_ready():
                        data = stream.read(event_size)
                        if len(data) == event_size:
                            timestamp, _, e_type, e_code, e_value = struct.unpack('llHHI', data)
                            self._handle_event(e_type, e_code, e_value)
                        elif len(data) > 0:
                            log.warning(f"Received unexpected data size from {device_type}: {len(data)} bytes")

                # Check if it's time to save the image
                if not self.is_touching and time.time() - self.last_pen_lift_time > 3:
                    self.save_image()
                    self.clear()

                time.sleep(0.001)  # Small sleep to prevent CPU hogging
        except Exception as e:
            log.error(f"Error capturing input: {e}")

    def _handle_event(self, e_type, e_code, e_value):
        if e_type == 3:  # EV_ABS
            if e_code == 24:  # ABS_PRESSURE
                self._handle_pressure(e_value)
            elif e_code == 0:  # ABS_X
                self.raw_x = e_value
            elif e_code == 1:  # ABS_Y
                self.raw_y = e_value

            if self.is_touching:
                self.current_stroke.append((self.raw_x, self.raw_y))
                if len(self.current_stroke) > 1:
                    self.draw.line([self.current_stroke[-2], self.current_stroke[-1]], fill='black', width=2)

    def _handle_pressure(self, pressure):
        if pressure > self.pressure_threshold and not self.is_touching:
            self.is_touching = True
            self.current_stroke = [(self.raw_x, self.raw_y)]
            log.info(f"Pen touched the surface (Pressure: {pressure}, Tablet Coordinates: ({self.raw_x}, {self.raw_y}))")
        elif pressure <= self.pressure_threshold and self.is_touching:
            self.is_touching = False
            if len(self.current_stroke) > 1:
                self.strokes.append(self.current_stroke)
                log.info(f"Stroke completed with {len(self.current_stroke)} points")
                log.info(f"Stroke start: {self.current_stroke[0]}, end: {self.current_stroke[-1]}")
            self.current_stroke = []
            self.last_pen_lift_time = time.time()
            log.info(f"Pen lifted from surface (Pressure: {pressure}, Tablet Coordinates: ({self.raw_x}, {self.raw_y}))")

    def save_image(self):
        if self.strokes:
            timestamp = int(time.time())
            filename = f"remarkable_drawing_{timestamp}.png"
            self.image.save(filename)
            log.info(f"Drawing saved as {filename}")

    def clear(self):
        self.strokes = []
        self.current_stroke = []
        self.image = Image.new('RGB', (self.rm_width, self.rm_height), color='white')
        self.draw = ImageDraw.Draw(self.image)

    def get_strokes(self):
        return self.strokes

    def print_stroke_info(self):
        log.info(f"Total strokes: {len(self.strokes)}")
        for i, stroke in enumerate(self.strokes):
            log.info(f"Stroke {i+1}: {len(stroke)} points")
            log.info(f"  Start: {stroke[0]}")
            log.info(f"  End: {stroke[-1]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture reMarkable Paper Pro input")
    parser.add_argument('--address', default='10.11.99.1', help="reMarkable IP address")
    parser.add_argument('--key', default=os.path.expanduser('~/.ssh/remarkable'), help="SSH private key file")
    args = parser.parse_args()

    try:
        drawer = RemarkableDrawer(args.address, args.key)
        print(f"Connected to reMarkable Paper Pro.")
        print("Start drawing on your reMarkable Paper Pro device.")
        print("Press Ctrl+C to stop the script.")

        drawer.capture_input()
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        log.error(f"An error occurred: {e}")
        import traceback
        log.debug(traceback.format_exc())
    finally:
        print("Script execution completed.")
        drawer.print_stroke_info()
