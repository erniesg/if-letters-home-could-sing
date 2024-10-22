import os
import struct
from PIL import Image
import numpy as np
from tqdm import tqdm
from preproc.config import CASIA_HWDB_DIR, PROCESSED_DIR
from preproc.utils import decode_label, get_unicode_repr, save_combined_image
from preproc.counter import Counter
from preproc.tracker import ProgressTracker

class CasiaHwdbProcessor:
    def __init__(self):
        self.dataset_dir = CASIA_HWDB_DIR
        self.output_dir = os.path.join(PROCESSED_DIR, 'CASIA_HWDB')
        self.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        self.dataset_name = 'CASIA_HWDB'
        self.gnt_dirs = [
            "Gnt1.0TrainPart1", "Gnt1.0TrainPart2", "Gnt1.0TrainPart3",
            "Gnt1.1Test", "Gnt1.1TrainPart1", "Gnt1.1TrainPart2",
            "Gnt1.2Test", "Gnt1.2TrainPart1", "Gnt1.2TrainPart2"
        ]
        self.chars_not_in_mapping = set()
        self.counter = Counter(self.dataset_name, self.progress_dir)
        self.progress_tracker = ProgressTracker(self.dataset_name, self.progress_dir)

    def get_full_dataset(self):
        gnt_files = []
        for dir_name in self.gnt_dirs:
            dir_path = os.path.join(self.dataset_dir, dir_name)
            gnt_files.extend([os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.gnt')])
        return gnt_files

    def process(self, base_mapping, samples):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.progress_dir, exist_ok=True)
        self.progress_tracker.set_total_samples(len(samples))
        for gnt_file in samples:
            yield from self._process_gnt_file(gnt_file, base_mapping)
            self.progress_tracker.increment_processed()
            tqdm.write(f"Processed files: {self.progress_tracker.processed_samples}/{self.progress_tracker.total_samples}")

    def _process_gnt_file(self, gnt_file, base_mapping):
        total_images = self._count_images_in_gnt(gnt_file)
        self.progress_tracker.total_images += total_images

        processed_images = 0
        with open(gnt_file, "rb") as f, tqdm(total=total_images, desc=f"Processing {os.path.basename(gnt_file)}") as pbar:
            while True:
                try:
                    packed_length = f.read(4)
                    if packed_length == b'':
                        break

                    length = struct.unpack("<I", packed_length)[0]
                    raw_label = f.read(2)
                    width = struct.unpack("<H", f.read(2))[0]
                    height = struct.unpack("<H", f.read(2))[0]
                    photo_bytes = f.read(height * width)

                    label = decode_label(raw_label)
                    char_id = base_mapping.get(label)

                    if char_id is None:
                        self.chars_not_in_mapping.add(label)
                        pbar.update(1)
                        processed_images += 1
                        continue

                    image = np.frombuffer(photo_bytes, dtype=np.uint8).reshape(height, width)
                    pil_image = Image.fromarray(image)

                    filename = self.counter.get_filename(char_id)
                    save_path = os.path.join(self.output_dir, char_id, filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    pil_image.save(save_path)

                    yield char_id, pil_image, self.dataset_name, filename
                    pbar.update(1)
                    processed_images += 1

                except Exception as e:
                    print(f"Error processing sample in {gnt_file}: {e}")
                    pbar.update(1)
                    processed_images += 1
                    continue

        self.progress_tracker.update_progress(gnt_file, 'Completed')

    def _count_images_in_gnt(self, gnt_file):
        count = 0
        with open(gnt_file, "rb") as f:
            while True:
                packed_length = f.read(4)
                if packed_length == b'':
                    break
                length = struct.unpack("<I", packed_length)[0]
                f.seek(length - 4, 1)  # Skip to the next sample
                count += 1
        return count

    def get_chars_not_in_mapping(self):
        return self.chars_not_in_mapping

def get_full_dataset():
    return CasiaHwdbProcessor().get_full_dataset()

def process(base_mapping, samples):
    processor = CasiaHwdbProcessor()
    return processor.process(base_mapping, samples)

def process_all(base_mapping, combined_dir):
    processor = CasiaHwdbProcessor()
    samples = processor.get_full_dataset()
    for char_id, image, dataset_name, filename in processor.process(base_mapping, samples):
        save_combined_image(char_id, image, dataset_name, filename, combined_dir)
        yield char_id, image, dataset_name, filename
