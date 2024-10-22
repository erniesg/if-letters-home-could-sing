import unittest
import os
import shutil
import tempfile
from PIL import Image
import logging
from preproc.processors.hit_or3c import HitOr3cProcessor
from preproc.config import PROCESSED_DIR, HIT_OR3C_DIR, FONT_PATH
from preproc.dataset import DatasetHandler
from preproc.tracker import ProgressTracker
from preproc.utils import load_char_mappings, count_extracted_images, is_char_in_font
from preproc.reporting import generate_summary_stats, print_summary_stats

class TestHitOr3cProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.progress_dir = os.path.join(cls.temp_dir, 'progress')
        cls.output_dir = os.path.join(cls.temp_dir, 'HIT_OR3C')
        os.makedirs(cls.progress_dir, exist_ok=True)
        os.makedirs(cls.output_dir, exist_ok=True)

        cls.processor = HitOr3cProcessor()
        cls.processor.output_dir = cls.output_dir
        cls.processor.progress_dir = cls.progress_dir
        # Add this line to update the counter's directory
        cls.processor.counter.progress_dir = cls.progress_dir

        char_to_id_path = os.path.join(PROCESSED_DIR, 'unified_char_to_id_mapping.json')
        id_to_char_path = os.path.join(PROCESSED_DIR, 'unified_id_to_char_mapping.json')

        cls.char_to_id, cls.id_to_char = load_char_mappings(char_to_id_path, id_to_char_path)
        cls.font_path = FONT_PATH

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        self.test_output_dir = os.path.join(self.temp_dir, f'HIT_OR3C_test_{self.id()}')
        os.makedirs(self.test_output_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_get_full_dataset(self):
        full_dataset = self.processor.get_full_dataset()
        self.assertIsInstance(full_dataset, list)
        self.assertTrue(len(full_dataset) > 0)
        self.assertTrue(all(f.endswith('_images') for f in full_dataset))

    def test_extraction_and_progress(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('HIT_OR3C', full_dataset)
        sampled_dataset = dataset_handler.get_deterministic_sample(0.01)

        progress_tracker = ProgressTracker('HIT_OR3C', self.progress_dir)
        progress_tracker.initialize_progress(sampled_dataset)

        processed_count = 0
        unique_chars_in_sample = set()

        for char_id, img, dataset_name, filename in self.processor.process(self.char_to_id, sampled_dataset):
            self.assertIsInstance(char_id, str)
            self.assertIsInstance(img, Image.Image)
            self.assertEqual(dataset_name, 'HIT_OR3C')
            self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

            # Update this part to check the new filename format
            expected_filename_pattern = r'HIT_OR3C_\d+_\d+\.png'
            self.assertRegex(filename, expected_filename_pattern)

            unique_chars_in_sample.add(char_id)
            processed_count += 1

            output_folder = os.path.join(self.test_output_dir, char_id)
            os.makedirs(output_folder, exist_ok=True)
            img_path = os.path.join(output_folder, filename)
            img.save(img_path)

        for sample in sampled_dataset:
            progress_tracker.update_progress(sample, 'Completed')

        # Exclude progress file when comparing output folders
        output_folders = set(os.listdir(self.test_output_dir))
        self.assertEqual(output_folders, unique_chars_in_sample, "Mismatch in unique character IDs")

        # Use count_extracted_images on the extracted_images_dir
        char_counts = count_extracted_images(self.test_output_dir)

        total_saved_images = sum(sum(counts.values()) for counts in char_counts.values())
        self.assertEqual(total_saved_images, processed_count, "Mismatch in total image count")

        # Additional check: ensure all counted files are images
        for char_id, dataset_counts in char_counts.items():
            char_dir = os.path.join(self.test_output_dir, char_id)
            for file in os.listdir(char_dir):
                self.assertTrue(file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')),
                                f"Non-image file found: {file}")

        print(f"Processed {processed_count} images for {len(unique_chars_in_sample)} unique characters")

        # Print summary including characters not in mapping
        chars_not_in_mapping = self.processor.get_chars_not_in_mapping()
        chars_not_in_font = self.processor.get_chars_not_in_font()
        stats = generate_summary_stats(char_counts, self.id_to_char, chars_not_in_mapping)
        print_summary_stats(stats)

        print(f"Characters not in mapping: {len(chars_not_in_mapping)}")
        print(f"Characters not in font: {len(chars_not_in_font)}")

    def test_character_mapping(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('HIT_OR3C', full_dataset)
        sampled_dataset = dataset_handler.get_deterministic_sample(0.01)

        processed_chars = set()
        unmapped_chars = set()
        not_in_font_chars = set()

        for char_id, _, _, _ in self.processor.process(self.char_to_id, sampled_dataset):
            processed_chars.add(char_id)

        unmapped_chars = self.processor.get_chars_not_in_mapping()
        not_in_font_chars = self.processor.get_chars_not_in_font()

        self.logger.info(f"Processed characters: {len(processed_chars)}")
        self.logger.info(f"Unmapped characters: {len(unmapped_chars)}")
        self.logger.info(f"Characters not in font: {len(not_in_font_chars)}")

        self.assertTrue(len(processed_chars) > 0, "No characters were processed")
        if unmapped_chars:
            self.logger.warning(f"Unmapped characters found: {unmapped_chars}")
        if not_in_font_chars:
            self.logger.warning(f"Characters not in font found: {not_in_font_chars}")

    def test_progress_tracking(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('HIT_OR3C', full_dataset)
        samples = dataset_handler.get_deterministic_sample(0.01)

        progress_tracker = ProgressTracker('HIT_OR3C', self.progress_dir)
        progress_tracker.initialize_progress(samples)

        samples_to_complete = max(1, len(samples) // 2)  # Ensure at least one sample is processed
        for sample in samples[:samples_to_complete]:
            for _ in self.processor.process(self.char_to_id, [sample]):
                pass
            progress_tracker.update_progress(sample, 'Completed')

        unprocessed = progress_tracker.get_unprocessed_samples(samples)
        self.logger.info(f"Total samples: {len(samples)}")
        self.logger.info(f"Samples to complete: {samples_to_complete}")
        self.logger.info(f"Unprocessed samples: {len(unprocessed)}")

        self.assertLessEqual(len(unprocessed), len(samples) - samples_to_complete,
                             f"Expected at most {len(samples) - samples_to_complete} unprocessed samples, but got {len(unprocessed)}")

if __name__ == '__main__':
    unittest.main()
