import unittest
import os
import shutil
from PIL import Image
from preproc.processors.m5hisdoc import M5HisDocProcessor
from preproc.config import DATA_DIR, PROCESSED_DIR, M5HISDOC_DIR, FONT_PATH
from preproc.utils import sample_dataset, load_char_mappings, validate_extraction, validate_output_structure, count_extracted_images
from preproc.reporting import generate_summary_stats
from preproc.dataset import DatasetHandler
from preproc.tracker import ProgressTracker

class TestM5HisDocProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processor = M5HisDocProcessor()
        cls.test_output_dir = os.path.join(PROCESSED_DIR, 'test_M5HisDoc')
        cls.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        os.makedirs(cls.test_output_dir, exist_ok=True)
        os.makedirs(cls.progress_dir, exist_ok=True)
        cls.char_to_id_path = os.path.join(DATA_DIR, 'processed', 'unified_char_to_id_mapping.json')
        cls.id_to_char_path = os.path.join(DATA_DIR, 'processed', 'unified_id_to_char_mapping.json')
        cls.char_to_id, cls.id_to_char = load_char_mappings(cls.char_to_id_path, cls.id_to_char_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_output_dir)

    def setUp(self):
        # Create a fresh test output directory for each test
        self.test_output_dir = os.path.join(PROCESSED_DIR, f'test_M5HisDoc_{self.id()}')
        os.makedirs(self.test_output_dir, exist_ok=True)

    def tearDown(self):
        # Clean up the test-specific output directory after each test
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_sampling(self):
        full_dataset = self.processor.get_full_dataset()
        sample_percentage = 0.0025  # Changed from 0.0001 to 0.0025
        sample_size = max(1, int(len(full_dataset) * sample_percentage))
        sampled_dataset = sample_dataset(full_dataset, sample_percentage)

        self.assertEqual(len(sampled_dataset), sample_size)
        self.assertTrue(set(sampled_dataset).issubset(set(full_dataset)))

    def test_extraction(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for char_id, img, dataset_name, filename in self.processor.process(self.char_to_id, sampled_dataset):
            self.assertIsInstance(char_id, str)
            self.assertIsInstance(img, Image.Image)
            self.assertEqual(dataset_name, 'M5HisDoc')
            self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

            # Update this part to check the new filename format
            expected_filename_pattern = r'M5HisDoc_\d+_\d+\.png'
            self.assertRegex(filename, expected_filename_pattern)

            # Save the extracted image
            output_folder = os.path.join(self.test_output_dir, char_id)
            os.makedirs(output_folder, exist_ok=True)
            img_path = os.path.join(output_folder, filename)
            img.save(img_path)

    def test_extraction_validation(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for txt_file in sampled_dataset:
            label_path = os.path.join(self.processor.label_char_dir, txt_file)
            extracted_chars = [char for char, _, _ in self.processor.process(self.char_to_id, txt_file)]
            self.assertTrue(validate_extraction(extracted_chars, label_path, self.char_to_id, FONT_PATH),
                            f"Extraction validation failed for {txt_file}")

    def test_output_structure(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for txt_file in sampled_dataset:
            for char, img, _ in self.processor.process(self.char_to_id, txt_file):
                char_id = self.char_to_id[char]
                char_dir = os.path.join(self.test_output_dir, char_id)
                os.makedirs(char_dir, exist_ok=True)
                img.save(os.path.join(char_dir, f"{char}_{len(os.listdir(char_dir))}.png"))

        self.assertTrue(validate_output_structure(self.test_output_dir, self.char_to_id, self.id_to_char),
                        "Output directory structure validation failed")

    def test_extracted_image_count(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        expected_counts = {}
        for txt_file in sampled_dataset:
            for char, _, dataset_name in self.processor.process(self.char_to_id, txt_file):
                char_id = self.char_to_id[char]
                if char_id not in expected_counts:
                    expected_counts[char_id] = {}
                expected_counts[char_id][dataset_name] = expected_counts[char_id].get(dataset_name, 0) + 1

        # Process and save images
        for txt_file in sampled_dataset:
            for char, img, dataset_name in self.processor.process(self.char_to_id, txt_file):
                char_id = self.char_to_id[char]
                char_dir = os.path.join(self.test_output_dir, char_id)
                os.makedirs(char_dir, exist_ok=True)
                img_path = os.path.join(char_dir, f"{dataset_name}_{char}_{len(os.listdir(char_dir))}.png")
                img.save(img_path)

        actual_counts = count_extracted_images(self.test_output_dir)

        self.assertEqual(expected_counts, actual_counts, "Mismatch in extracted image counts")

        # Additional checks for the structure
        for char_id, dataset_counts in actual_counts.items():
            self.assertIsInstance(char_id, str, f"Character ID {char_id} is not a string")
            self.assertIsInstance(dataset_counts, dict, f"Dataset counts for {char_id} is not a dictionary")
            for dataset_name, count in dataset_counts.items():
                self.assertEqual(dataset_name, 'M5HisDoc', f"Unexpected dataset name {dataset_name} for {char_id}")
                self.assertIsInstance(count, int, f"Count for {char_id} in {dataset_name} is not an integer")
                self.assertGreater(count, 0, f"Count for {char_id} in {dataset_name} is not positive")

    def test_summary_stats(self):
        # Create a mock char_counts dictionary
        mock_char_counts = {
            '00001': {'M5HisDoc': 10},
            '00002': {'M5HisDoc': 5},
            '00003': {'M5HisDoc': 15},
            '00004': {'M5HisDoc': 8},
            '00005': {'M5HisDoc': 12}
        }

        stats = generate_summary_stats(mock_char_counts, self.id_to_char)

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['total_chars'], 50)
        self.assertEqual(stats['unique_chars'], 5)
        self.assertAlmostEqual(stats['avg_count'], 10.0)
        self.assertEqual(stats['median_count'], 10)
        self.assertGreaterEqual(stats['std_dev'], 0)
        self.assertEqual(len(stats['most_common']), 5)
        self.assertEqual(len(stats['least_common']), 5)
        self.assertGreaterEqual(stats['gini'], 0)
        self.assertLessEqual(stats['gini'], 1)

        # Check if the most common and least common characters are correct
        self.assertEqual(stats['most_common'][0][1], 15)
        self.assertEqual(stats['most_common'][-1][1], 5)
        self.assertEqual(stats['least_common'][0][1], 5)
        self.assertEqual(stats['least_common'][-1][1], 15)

        # Check the order of most_common and least_common
        self.assertEqual([count for _, count in stats['most_common']], [15, 12, 10, 8, 5])
        self.assertEqual([count for _, count in stats['least_common']], [5, 8, 10, 12, 15])

    def test_deterministic_sampling(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('M5HisDoc', full_dataset)
        sample1 = dataset_handler.get_deterministic_sample(0.1)
        sample2 = dataset_handler.get_deterministic_sample(0.1)
        self.assertEqual(sample1, sample2)

    def test_incremental_sampling(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('M5HisDoc', full_dataset)
        sample1 = dataset_handler.get_deterministic_sample(0.1)
        sample2 = dataset_handler.get_deterministic_sample(0.2)
        incremental = dataset_handler.get_incremental_sample(0.1, 0.2)
        self.assertEqual(set(sample2) - set(sample1), set(incremental))

    def test_extraction_with_new_sampling(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('M5HisDoc', full_dataset)
        sampled_dataset = dataset_handler.get_deterministic_sample(0.0001)

        for txt_file in sampled_dataset:
            extracted_chars = list(self.processor.process(self.char_to_id, [txt_file]))
            self.assertTrue(len(extracted_chars) > 0)

            for char, img, dataset_name in extracted_chars:
                self.assertIsInstance(char, str)
                self.assertIsInstance(img, Image.Image)
                self.assertEqual(dataset_name, 'M5HisDoc')
                self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

    def test_progress_tracking(self):
        full_dataset = self.processor.get_full_dataset()
        print(f"Full dataset size: {len(full_dataset)}")

        # Adjust sampling percentage to ensure we get at least 10 samples
        sample_percentage = max(0.001, 10 / len(full_dataset))
        dataset_handler = DatasetHandler('M5HisDoc', full_dataset)
        samples = dataset_handler.get_deterministic_sample(sample_percentage)
        print(f"Sample size: {len(samples)}")

        progress_tracker = ProgressTracker('M5HisDoc', self.progress_dir)
        progress_tracker.initialize_progress(samples)

        print("Initial progress state:")
        print(progress_tracker.progress)

        samples_to_complete = min(5, len(samples) - 1)  # Ensure we leave at least one sample unprocessed
        for sample in samples[:samples_to_complete]:
            progress_tracker.update_progress(sample, 'Completed')
            print(f"Updated progress for sample {sample}")

        print("Progress state after updates:")
        print(progress_tracker.progress)

        unprocessed = progress_tracker.get_unprocessed_samples(samples)
        print(f"Unprocessed samples: {len(unprocessed)}")
        print(f"Expected unprocessed: {len(samples) - samples_to_complete}")

        self.assertEqual(len(unprocessed), len(samples) - samples_to_complete)

        # Check if we have enough samples for a meaningful test
        self.assertGreater(len(samples), samples_to_complete, "Not enough samples to test progress tracking")

    def test_counter_persistence(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('M5HisDoc', full_dataset)
        samples = dataset_handler.get_deterministic_sample(0.01)

        # Process some samples
        for txt_file in samples[:1]:  # Process only one file
            list(self.processor.process(self.char_to_id, [txt_file]))  # Consume the generator

        # Create a new processor instance
        new_processor = M5HisDocProcessor()

        # Process the same file again
        for _, _, _, filename in new_processor.process(self.char_to_id, [samples[0]]):
            # Check that the counter continues from where it left off
            self.assertNotIn('_1.png', filename)
            break  # We only need to check the first file

if __name__ == '__main__':
    unittest.main()
