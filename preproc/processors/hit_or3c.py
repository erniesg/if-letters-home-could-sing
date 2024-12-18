import os
import struct
import numpy as np
from PIL import Image
from tqdm import tqdm
import logging
from preproc.config import HIT_OR3C_DIR, PROCESSED_DIR, FONT_PATH
from preproc.utils import decode_label, is_char_in_font, get_unicode_repr, sanitize_filename, save_combined_image
from preproc.counter import Counter
from preproc.tracker import ProgressTracker

class HitOr3cProcessor:
    def __init__(self):
        self.data_dir = HIT_OR3C_DIR
        self.output_dir = os.path.join(PROCESSED_DIR, 'HIT_OR3C')
        self.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        self.labels_file = os.path.join(self.data_dir, "labels.txt")
        self.dataset_name = 'HIT_OR3C'
        self.chars_not_in_mapping = set()
        self.chars_not_in_font = set()
        self.font_path = FONT_PATH
        self.logger = logging.getLogger(__name__)
        self.counter = Counter(self.dataset_name, self.progress_dir)
        self.progress_tracker = ProgressTracker(self.dataset_name, self.progress_dir)

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
        self.progress_tracker.set_total_samples(len(samples))
        labels = self.read_labels()
        label_index = 0

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
                            filename = self.counter.get_filename(char_id)
                            yield char_id, pil_image, self.dataset_name, filename
                        else:
                            self.chars_not_in_font.add(label)
                    else:
                        self.chars_not_in_mapping.add(label)

                    pbar.update(1)
                    self.progress_tracker.increment_processed()
                    tqdm.write(f"Processed files: {self.progress_tracker.processed_samples}/{self.progress_tracker.total_samples}")

        self.logger.info(f"Processed {label_index} labels")
        if self.chars_not_in_mapping:
            self.logger.warning(f"Characters not in mapping: {self.chars_not_in_mapping}")
        if self.chars_not_in_font:
            self.logger.warning(f"Characters not in font: {self.chars_not_in_font}")

    def get_chars_not_in_mapping(self):
        return self.chars_not_in_mapping

    def get_chars_not_in_font(self):
        return self.chars_not_in_font

    def process_all(char_to_id, combined_dir):
        processor = HitOr3cProcessor()
        samples = processor.get_full_dataset()
        for char_id, image, dataset_name, filename in processor.process(char_to_id, samples):
            save_combined_image(char_id, image, dataset_name, filename, combined_dir)
            yield char_id, image, dataset_name, filename

def get_full_dataset():
    processor = HitOr3cProcessor()
    return processor.get_full_dataset()
