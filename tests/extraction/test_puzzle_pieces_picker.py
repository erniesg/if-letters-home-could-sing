import unittest
import os
import shutil
from PIL import Image
from preproc.processors.puzzle_pieces_picker import PuzzlePiecesPicker
from preproc.config import PROCESSED_DIR
from preproc.dataset import DatasetHandler
from preproc.tracker import ProgressTracker

class TestPuzzlePiecesPicker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processor = PuzzlePiecesPicker()
        cls.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        os.makedirs(cls.progress_dir, exist_ok=True)

    def setUp(self):
        self.test_output_dir = os.path.join(PROCESSED_DIR, f'PuzzlePiecesPicker_test_{self.id()}')
        os.makedirs(self.test_output_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_get_full_dataset(self):
        full_dataset = self.processor.get_full_dataset()
        self.assertIsInstance(full_dataset, list)
        self.assertTrue(len(full_dataset) > 0)
        self.assertTrue(all(isinstance(item, str) for item in full_dataset))

    def test_extraction(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('PuzzlePiecesPicker', full_dataset)
        sampled_dataset = dataset_handler.get_deterministic_sample(0.01)

        for char_id, img, dataset_name, filename in self.processor.process(sampled_dataset):
            self.assertIsInstance(char_id, str)
            self.assertIsInstance(img, Image.Image)
            self.assertEqual(dataset_name, 'PuzzlePiecesPicker')
            self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

            # Save the extracted image
            output_folder = os.path.join(self.test_output_dir, char_id)
            os.makedirs(output_folder, exist_ok=True)
            img_path = os.path.join(output_folder, filename)
            img.save(img_path)
            img.close()

    def test_extracted_image_count(self):
        full_dataset = self.processor.get_full_dataset()
        dataset_handler = DatasetHandler('PuzzlePiecesPicker', full_dataset)
        sampled_dataset = dataset_handler.get_deterministic_sample(0.01)

        expected_counts = {}
        actual_counts = {}

        for folder_id in sampled_dataset:
            source_folder = os.path.join(self.processor.dataset_dir, folder_id)
            expected_counts[folder_id] = len([f for f in os.listdir(source_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            actual_counts[folder_id] = 0

        for folder_id, img, _, _ in self.processor.process(sampled_dataset):
            output_folder = os.path.join(self.test_output_dir, folder_id)
            os.makedirs(output_folder, exist_ok=True)
            img_path = os.path.join(output_folder, f"PuzzlePiecesPicker_{len(os.listdir(output_folder))}.png")
            img.save(img_path)
            img.close()
            actual_counts[folder_id] += 1

        self.assertEqual(expected_counts, actual_counts, "Mismatch in extracted image counts")

    def test_progress_tracking(self):
        full_dataset = self.processor.get_full_dataset()
        print(f"Full dataset size: {len(full_dataset)}")

        sample_size = 15
        dataset_handler = DatasetHandler('PuzzlePiecesPicker', full_dataset)
        samples = dataset_handler.get_deterministic_sample(sample_size / len(full_dataset))
        samples = samples[:sample_size]  # Ensure we have exactly 15 samples
        print(f"Sample size: {len(samples)}")

        progress_tracker = ProgressTracker('PuzzlePiecesPicker', self.progress_dir)
        progress_tracker.initialize_progress(samples)

        print("Initial progress state:")
        print(progress_tracker.progress)

        samples_to_complete = 10  # Process 10 out of 15 samples
        for folder_id in samples[:samples_to_complete]:
            for _, img, _, _ in self.processor.process([folder_id]):
                img.close()
            progress_tracker.update_progress(folder_id, 'Completed')
            print(f"Updated progress for sample {folder_id}")

        print("Progress state after updates:")
        print(progress_tracker.progress)

        unprocessed = progress_tracker.get_unprocessed_samples(samples)
        print(f"Unprocessed samples: {len(unprocessed)}")
        print(f"Expected unprocessed: {len(samples) - samples_to_complete}")

        self.assertEqual(len(unprocessed), len(samples) - samples_to_complete)
        self.assertGreater(len(samples), samples_to_complete, "Not enough samples to test progress tracking")

if __name__ == '__main__':
    unittest.main()
