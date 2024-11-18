import struct
import numpy as np
from PIL import Image
from tqdm import tqdm
import logging
import io
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from preproc.utils import decode_label, is_char_in_font
from preproc.counter import Counter
from preproc.tracker import ProgressTracker

class HitOr3cProcessor:
    def __init__(self, config):
        self.s3 = S3Hook()
        self.bucket = config['s3']['base_path'].split('/')[-1]
        # Construct proper S3 paths
        self.base_path = f"{config['s3']['unzipped_dir']}/{config['datasets']['hit_or3c']['folder']}"
        self.output_dir = config['s3']['output_dir']
        self.progress_dir = "progress"  # Store in root of bucket
        self.dataset_name = 'HIT_OR3C'
        self.chars_not_in_mapping = set()
        self.chars_not_in_font = set()
        self.logger = logging.getLogger(__name__)
        self.counter = Counter(self.dataset_name, self.progress_dir)
        self.progress_tracker = ProgressTracker(self.dataset_name, self.progress_dir)
        # Set font path
        self.font_path = f"{config['s3']['base_path']}/{config['s3']['font']}"
        # Download and cache font
        self.font_data = self._download_font(config['s3']['font'])
        self.font_file = io.BytesIO(self.font_data)
        self.font_path = self.font_file

    def _download_font(self, font_name):
        """Download font from S3 and return as bytes"""
        try:
            return self.s3.read_key(
                key=font_name,
                bucket_name=self.bucket
            )
        except Exception as e:
            self.logger.error(f"Failed to download font {font_name}: {e}")
            raise

    def get_full_dataset(self):
        prefix = f"{self.base_path}/"
        return sorted([
            obj.key.split('/')[-1]
            for obj in self.s3.list_objects(
                bucket_name=self.bucket,
                prefix=prefix
            ) if obj.key.endswith('_images')
        ])

    def read_labels(self):
        labels = []
        content = self.s3.read_key(
            key=f"{self.base_path}/labels.txt",
            bucket_name=self.bucket
        )
        for i in range(0, len(content), 2):
            raw_label = content[i:i+2]
            label = decode_label(raw_label)
            labels.append(label)
        return labels

    def read_images(self, file_path):
        full_path = f"{self.base_path}/{file_path}"
        data = self.s3.read_key(
            key=full_path,
            bucket_name=self.bucket
        )
        with io.BytesIO(data) as f:
            total_char_number = struct.unpack('<I', f.read(4))[0]
            height = struct.unpack('B', f.read(1))[0]
            width = struct.unpack('B', f.read(1))[0]

            images = []
            for _ in range(total_char_number):
                pix_gray = np.frombuffer(f.read(width * height), dtype=np.uint8).reshape(height, width)
                images.append(pix_gray)
        return images, (height, width)

    def process(self, char_to_id, samples, test_mode=False):
        if test_mode:
            samples = samples[:2]  # Process only first 2 folders in test mode

        self.progress_tracker.set_total_samples(len(samples))
        stats = {
            'processed': 0,
            'errors': [],
            'chars_not_in_mapping': set(),
            'chars_not_in_font': set(),
            'processing_errors': {}
        }

        labels = self.read_labels()
        label_index = 0

        for image_file in samples:
            try:
                images, _ = self.read_images(image_file)
                total_images = len(images)

                with tqdm(total=total_images, desc=f"Processing {image_file}") as pbar:
                    for image in images:
                        try:
                            label = labels[label_index]
                            label_index += 1

                            if label in char_to_id:
                                char_id = char_to_id[label]
                                if is_char_in_font(label, self.font_path):  # Font check with S3 font path
                                    pil_image = Image.fromarray(image)
                                    filename = self.counter.get_filename(char_id)
                                    yield char_id, pil_image, self.dataset_name, filename
                                    stats['processed'] += 1
                                else:
                                    stats['chars_not_in_font'].add(label)
                            else:
                                stats['chars_not_in_mapping'].add(label)

                            pbar.update(1)
                            self.progress_tracker.increment_processed()
                            tqdm.write(f"Processed images: {stats['processed']}/{total_images}")

                        except Exception as e:
                            stats['errors'].append(f"Error processing image {label_index} in {image_file}: {str(e)}")
                            continue

            except Exception as e:
                stats['processing_errors'][image_file] = str(e)
                continue

        self.logger.info(f"Processed {stats['processed']} images")
        if stats['chars_not_in_mapping']:
            self.logger.warning(f"Characters not in mapping: {stats['chars_not_in_mapping']}")
        if stats['chars_not_in_font']:
            self.logger.warning(f"Characters not in font: {stats['chars_not_in_font']}")
        if stats['errors']:
            self.logger.warning(f"Errors during processing: {len(stats['errors'])} errors")
        if stats['processing_errors']:
            self.logger.warning(f"Folder processing errors: {stats['processing_errors']}")

        return stats

    def get_chars_not_in_mapping(self):
        return self.chars_not_in_mapping

    def get_chars_not_in_font(self):
        return self.chars_not_in_font

def get_full_dataset(config):
    processor = HitOr3cProcessor(config)
    return processor.get_full_dataset()
