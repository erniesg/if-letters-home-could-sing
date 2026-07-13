import unittest
import os
import shutil
import tempfile
from PIL import Image
from preproc.processors.casia_hwdb import CasiaHwdbProcessor
from preproc.config import PROCESSED_DIR, CASIA_HWDB_DIR
from preproc.dataset import DatasetHandler
from preproc.tracker import ProgressTracker
from preproc.utils import load_char_mappings, count_extracted_images
from preproc.reporting import generate_summary_stats, print_summary_stats

class TestCasiaHwdbProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.progress_dir = os.path.join(cls.temp_dir, 'progress')
        cls.output_dir = os.path.join(cls.temp_dir, 'CASIA_HWDB')
        os.makedirs(cls.progress_dir, exist_ok=True)
        os.makedirs(cls.output_dir, exist_ok=True)

        cls.processor = CasiaHwdbProcessor()
        cls.processor.output_dir = cls.output_dir
        cls.processor.progress_dir = cls.progress_dir
        # We keep the original dataset_dir
        cls.processor.dataset_dir = CASIA_HWDB_DIR
        # Update the progress tracker's directory
        cls.processor.progress_tracker.progress_dir = cls.progress_dir
        # Update the counter's directory
        cls.processor.counter.progress_dir = cls.progress_dir

        # Use the unified mapping files
        char_to_id_path = os.path.join(PROCESSED_DIR, 'unified_char_to_id_mapping.json')
        id_to_char_path = os.path.join(PROCESSED_DIR, 'unified_id_to_char_mapping.json')

        cls.char_to_id, cls.id_to_char = load_char_mappings(char_to_id_path, id_to_char_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        self.test_output_dir = os.path.join(self.temp_dir, f'CASIA_HWDB_test_{self.id()}')
        os.makedirs(self.test_output_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_get_full_dataset(self):
        full_dataset = self.processor.get_full_dataset()
        self.assertIsInstance(full_dataset, list)
        self.assertTrue(len(full_dataset) > 0)
        self.assertTrue(all(f.endswith('.gnt') for f in full_dataset))

    def test_extraction_and_progress(self):
        full_dataset = self.processor.get_full_dataset()
        test_gnt_file = full_dataset[0]

        # Initialize the progress tracker with the correct progress directory
        progress_tracker = ProgressTracker('CASIA_HWDB', self.progress_dir)
        progress_tracker.initialize_progress([test_gnt_file])

        processed_images = 0
        unique_chars_in_gnt = set()

        for char_id, img, dataset_name, filename in self.processor.process(self.char_to_id, [test_gnt_file]):
            self.assertIsInstance(char_id, str)
            self.assertIsInstance(img, Image.Image)
            self.assertEqual(dataset_name, 'CASIA_HWDB')
            self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

            # Update this part to check the new filename format
            expected_filename_pattern = r'CASIA_HWDB_\d+_\d+\.png'
            self.assertRegex(filename, expected_filename_pattern)

            unique_chars_in_gnt.add(char_id)
            processed_images += 1

            output_folder = os.path.join(self.test_output_dir, char_id)
            os.makedirs(output_folder, exist_ok=True)
            img_path = os.path.join(output_folder, filename)
            img.save(img_path)

        progress_tracker.update_progress(test_gnt_file, 'Completed')

        # Exclude progress file when comparing output folders
        output_folders = set(os.listdir(self.test_output_dir))
        self.assertEqual(output_folders, unique_chars_in_gnt, "Mismatch in unique character IDs")

        # Use count_extracted_images on the extracted_images_dir
        char_counts = count_extracted_images(self.test_output_dir)

        total_saved_images = sum(sum(counts.values()) for counts in char_counts.values())
        self.assertEqual(total_saved_images, processed_images, "Mismatch in total image count")

        # Additional check: ensure all counted files are images
        for char_id, dataset_counts in char_counts.items():
            char_dir = os.path.join(self.test_output_dir, char_id)
            for file in os.listdir(char_dir):
                self.assertTrue(file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')),
                                f"Non-image file found: {file}")

        print(f"Processed {processed_images} images for {len(unique_chars_in_gnt)} unique characters from {test_gnt_file}")

        # Print summary including characters not in mapping
        chars_not_in_mapping = self.processor.get_chars_not_in_mapping()
        stats = generate_summary_stats(char_counts, self.id_to_char, chars_not_in_mapping)
        print_summary_stats(stats)

    def test_resume_processing(self):
        # Test the ability to resume processing from where it left off
        pass

if __name__ == '__main__':
    unittest.main()
