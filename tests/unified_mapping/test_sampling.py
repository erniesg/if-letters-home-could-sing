import unittest
from preproc.utils import sample_dataset
from preproc.processors import puzzle_pieces_picker, m5hisdoc, casia_hwdb, hit_or3c

class TestSampling(unittest.TestCase):
    def test_sampling_with_percentage(self):
        sample_percentage = 0.1
        for processor in [puzzle_pieces_picker, m5hisdoc, casia_hwdb, hit_or3c]:
            full_dataset = processor.get_full_dataset()
            sampled_dataset = sample_dataset(full_dataset, sample_percentage)
            expected_size = int(len(full_dataset) * sample_percentage)
            self.assertEqual(len(sampled_dataset), expected_size)

if __name__ == '__main__':
    unittest.main()
