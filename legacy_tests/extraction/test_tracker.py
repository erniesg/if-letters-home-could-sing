import unittest
import os
import shutil
from preproc.tracker import ProgressTracker
from preproc.dataset import DatasetHandler

class TestProgressTracking(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_progress'
        os.makedirs(self.test_dir, exist_ok=True)
        self.tracker = ProgressTracker('test_dataset', self.test_dir)
        self.dataset_handler = DatasetHandler('test_dataset', list(range(100)))
        self.samples = self.dataset_handler.get_deterministic_sample(0.1)
        self.tracker.initialize_progress(self.samples)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_progress_initialization(self):
        samples = self.dataset_handler.get_deterministic_sample(0.1)
        self.tracker.initialize_progress(samples)
        for sample in samples:
            self.assertIn(sample, self.tracker.progress)
            self.assertEqual(self.tracker.progress[sample]['status'], 'Not Started')

    def test_progress_update(self):
        sample = self.samples[0]
        self.tracker.update_progress(sample, 'Completed')
        self.assertEqual(self.tracker.progress[sample]['status'], 'Completed')

    def test_is_sample_processed(self):
        sample = self.samples[0]
        self.tracker.update_progress(sample, 'Completed')
        self.assertTrue(self.tracker.is_sample_processed(sample))
        self.assertFalse(self.tracker.is_sample_processed(self.samples[-1]))

    def test_get_unprocessed_samples(self):
        samples = [0, 1, 2, 3, 4]
        self.tracker.initialize_progress(samples)
        self.tracker.update_progress(0, 'Completed')
        self.tracker.update_progress(2, 'Completed')
        unprocessed = self.tracker.get_unprocessed_samples(samples)
        self.assertEqual(unprocessed, [1, 3, 4])

    def test_deterministic_sampling(self):
        sample1 = self.dataset_handler.get_deterministic_sample(0.1)
        sample2 = self.dataset_handler.get_deterministic_sample(0.1)
        self.assertEqual(sample1, sample2)

    def test_incremental_sampling(self):
        sample1 = self.dataset_handler.get_deterministic_sample(0.1)
        sample2 = self.dataset_handler.get_deterministic_sample(0.2)
        incremental = self.dataset_handler.get_incremental_sample(0.1, 0.2)
        self.assertEqual(set(sample2) - set(sample1), set(incremental))

if __name__ == '__main__':
    unittest.main()
