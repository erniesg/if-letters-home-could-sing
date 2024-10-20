import os
import struct
import numpy as np
from PIL import Image
from tqdm import tqdm
import logging
from preproc.config import HIT_OR3C_DIR, PROCESSED_DIR, FONT_PATH
from preproc.utils import decode_label, is_char_in_font, get_unicode_repr, sanitize_filename

class HitOr3cProcessor:
    def __init__(self):
        self.data_dir = HIT_OR3C_DIR
        self.output_dir = os.path.join(PROCESSED_DIR, 'HIT_OR3C')
        self.labels_file = os.path.join(self.data_dir, "labels.txt")
        self.dataset_name = 'HIT_OR3C'
        self.chars_not_in_mapping = set()
        self.chars_not_in_font = set()
        self.font_path = FONT_PATH
        self.logger = logging.getLogger(__name__)
        self.char_counters = {}

    def get_full_dataset(self):
        return sorted([f for f in os.listdir(self.data_dir) if f.endswith('_images')])

    def read_labels(self):
        labels = []
        with open(self.labels_file, 'rb') as f:
            content = f.read()
            for i in range(0, len(content), 2):
                raw_label = content[i:i+2]
                label = decode_label(raw_label)
                labels.append(label)
        return labels

    def read_images(self, file_path):
        images = []
        with open(os.path.join(self.data_dir, file_path), 'rb') as f:
            total_char_number = struct.unpack('<I', f.read(4))[0]
            height = struct.unpack('B', f.read(1))[0]
            width = struct.unpack('B', f.read(1))[0]

            for _ in range(total_char_number):
                pix_gray = np.frombuffer(f.read(width * height), dtype=np.uint8).reshape(height, width)
                images.append(pix_gray)
        return images, (height, width)

    def count_images_in_file(self, file_path):
        with open(os.path.join(self.data_dir, file_path), 'rb') as f:
            return struct.unpack('<I', f.read(4))[0]

    def process(self, char_to_id, samples):
        labels = self.read_labels()
        label_index = 0
        self.char_counters = {}  # Reset counters for each processing run

        for image_file in samples:
            images, _ = self.read_images(image_file)
            total_images = len(images)

            with tqdm(total=total_images, desc=f"Processing {image_file}") as pbar:
                for image in images:
                    label = labels[label_index]
                    label_index += 1

                    if label in char_to_id:
                        char_id = char_to_id[label]
                        if is_char_in_font(label, self.font_path):
                            pil_image = Image.fromarray(image)
                            self.char_counters[char_id] = self.char_counters.get(char_id, 0) + 1
                            filename = f"{self.dataset_name}_{char_id}_{self.char_counters[char_id]}.png"
                            yield char_id, pil_image, self.dataset_name, filename
                        else:
                            self.chars_not_in_font.add(label)
                    else:
                        self.chars_not_in_mapping.add(label)

                    pbar.update(1)

        self.logger.info(f"Processed {label_index} labels")
        if self.chars_not_in_mapping:
            self.logger.warning(f"Characters not in mapping: {self.chars_not_in_mapping}")
        if self.chars_not_in_font:
            self.logger.warning(f"Characters not in font: {self.chars_not_in_font}")

    def get_chars_not_in_mapping(self):
        return self.chars_not_in_mapping

    def get_chars_not_in_font(self):
        return self.chars_not_in_font
