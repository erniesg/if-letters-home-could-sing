import struct
import numpy as np
from PIL import Image, ImageFont
from tqdm import tqdm
import logging
import io
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from preproc.utils import decode_label, is_char_in_font
from preproc.counter import Counter
from preproc.tracker import ProgressTracker

class HitOr3cProcessor:
    def __init__(self, *, config: dict):
        self.bucket = config['s3']['base_path'].split('//')[1].split('/')[0]
        self.s3 = S3Hook()
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
        # Font handling
        try:
            self.font_data = self._download_font(config['s3']['font'])
            self.font_file = io.BytesIO(self.font_data)
            self.font_path = self.font_file
        except Exception as e:
            self.logger.error(f"Font initialization failed: {e}")
            raise

    def _download_font(self, font_name):
        """Download font from S3 and return as bytes"""
        try:
            # Read as raw bytes without decoding
            data = self.s3.get_key(
                key=font_name,
                bucket_name=self.bucket
            ).get()['Body'].read()
            
            # Validate font data
            if not data:
                raise ValueError("Empty font file")
            
            # Test if it's a valid font
            test_font = ImageFont.truetype(io.BytesIO(data), size=12)
            test_font.getmask('测')  # Test with a simple character
            
            return data
        except Exception as e:
            self.logger.error(f"Failed to download or validate font {font_name}: {e}")
            raise

    def get_full_dataset(self):
        """List all HIT-OR3C image files from S3"""
        try:
            # List all files (not folders) ending with _images
            files = self.s3.list_keys(
                bucket_name=self.bucket,
                prefix=self.base_path
            )
            
            # Filter for *_images files
            image_files = [
                f for f in files 
                if f.endswith('_images')  # Changed from endswith('_images/')
            ]
            
            if not image_files:
                self.logger.warning(f"No *_images files found in s3://{self.bucket}/{self.base_path}")
                # Debug: List what's actually there
                all_files = self.s3.list_keys(
                    bucket_name=self.bucket,
                    prefix=self.base_path
                )
                self.logger.info(f"Available files in {self.base_path}:")
                for f in all_files:
                    self.logger.info(f"  - {f}")
                return []
            
            self.logger.info(f"Found {len(image_files)} image files")
            return image_files
            
        except Exception as e:
            self.logger.error(f"Error listing dataset: {str(e)}")
            raise

    def read_labels(self):
        """Read binary labels file"""
        try:
            # Read raw bytes without decoding
            content = self.s3.get_key(
                key=f"{self.base_path}/labels.txt",
                bucket_name=self.bucket
            ).get()['Body'].read()
            
            self.logger.info(f"Read {len(content)} bytes from labels file")
            
            labels = []
            for i in range(0, len(content), 2):
                try:
                    raw_label = content[i:i+2]
                    label = decode_label(raw_label)
                    labels.append(label)
                except Exception as e:
                    self.logger.warning(f"Error decoding label at position {i}: {str(e)}")
                    continue
            
            self.logger.info(f"Decoded {len(labels)} labels")
            return labels
            
        except Exception as e:
            self.logger.error(f"Failed to read labels file: {str(e)}")
            raise

    def read_images(self, file_path):
        """Read and validate images from HIT-OR3C binary format"""
        full_path = f"{self.base_path}/{file_path}"
        try:
            data = self.s3.read_key(
                key=full_path,
                bucket_name=self.bucket
            )

            with io.BytesIO(data) as f:
                try:
                    # Read and validate header
                    total_char_number = struct.unpack('<I', f.read(4))[0]
                    if total_char_number <= 0 or total_char_number > 100000:  # Reasonable max limit
                        raise ValueError(f"Invalid character count: {total_char_number}")

                    height = struct.unpack('B', f.read(1))[0]
                    width = struct.unpack('B', f.read(1))[0]
                    if height <= 0 or width <= 0 or height > 255 or width > 255:
                        raise ValueError(f"Invalid dimensions: {width}x{height}")

                    # Calculate expected file size
                    expected_size = 6 + (width * height * total_char_number)  # header + image data
                    if len(data) != expected_size:
                        raise ValueError(f"File size mismatch: expected {expected_size}, got {len(data)}")

                    images = []
                    for i in range(total_char_number):
                        try:
                            pixel_data = f.read(width * height)
                            if len(pixel_data) != width * height:
                                self.logger.warning(f"Incomplete pixel data for image {i} in {file_path}")
                                continue

                            pix_gray = np.frombuffer(pixel_data, dtype=np.uint8).reshape(height, width)

                            # Basic image validation
                            if not np.any(pix_gray):  # Check if image is all zeros
                                self.logger.warning(f"Empty image detected at index {i} in {file_path}")
                                continue

                            images.append(pix_gray)
                        except Exception as e:
                            self.logger.warning(f"Error reading image {i} in {file_path}: {str(e)}")
                            continue

                    if not images:
                        raise ValueError("No valid images found in file")

                    return images, (height, width)

                except struct.error as e:
                    raise ValueError(f"Error unpacking binary data: {str(e)}")

        except Exception as e:
            self.logger.error(f"Failed to process image file {file_path}: {str(e)}")
            raise

    def process(self, char_to_id: dict, samples: list, test_mode: bool = False) -> tuple:
        if test_mode:
            samples = samples[:2]
            self.logger.info(f"Test mode: using {len(samples)} samples")

        self.progress_tracker.set_total_samples(len(samples))
        stats = {
            'processed': 0,
            'errors': [],
            'chars_not_in_mapping': set(),
            'chars_not_in_font': set(),
            'processing_errors': {}
        }

        try:
            self.logger.info("Reading labels file...")
            labels = self.read_labels()
            self.logger.info(f"Successfully read {len(labels)} labels")
            label_index = 0

            for image_file in samples:
                self.logger.info(f"Processing file: {image_file}")
                try:
                    images, dimensions = self.read_images(image_file)
                    height, width = dimensions
                    total_images = len(images)
                    self.logger.info(f"Found {total_images} images ({width}x{height})")

                    with tqdm(total=total_images, desc=f"Processing {image_file}") as pbar:
                        for image_idx, image in enumerate(images):
                            try:
                                if label_index >= len(labels):
                                    self.logger.error(f"Label index {label_index} exceeds available labels")
                                    break

                                label = labels[label_index]
                                self.logger.debug(f"Processing image {image_idx} with label: {label}")
                                label_index += 1
                                
                                # Validate image data
                                if image.shape != (height, width):
                                    raise ValueError(f"Image {image_idx} has incorrect shape {image.shape}")

                                if label in char_to_id:
                                    char_id = char_to_id[label]
                                    if is_char_in_font(label, self.font_path):
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

                            except Exception as e:
                                stats['errors'].append(f"Error processing image {label_index} in {image_file}: {str(e)}")
                                continue

                except Exception as e:
                    stats['processing_errors'][image_file] = str(e)
                    continue

        except Exception as e:
            stats['processing_errors']['labels_file'] = str(e)
            return stats

        return stats

    def get_chars_not_in_mapping(self):
        return self.chars_not_in_mapping

    def get_chars_not_in_font(self):
        return self.chars_not_in_font

@staticmethod
def get_full_dataset(config: dict) -> list:
    processor = HitOr3cProcessor(config=config)
    return processor.get_full_dataset()
