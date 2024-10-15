import unittest
import os
import shutil
from PIL import Image
from preproc.processors.m5hisdoc import M5HisDocProcessor
from preproc.config import ConfigManager
from preproc.utils import sample_dataset

class TestM5HisDocProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = ConfigManager()
        cls.processor = M5HisDocProcessor()
        cls.test_output_dir = os.path.join(cls.config.get_settings()['DATA_DIR'], 'processed', 'M5HisDoc_test')
        os.makedirs(cls.test_output_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_output_dir)

    def test_sampling(self):
        full_dataset = self.processor.get_full_dataset()
        sample_size = max(1, int(len(full_dataset) * 0.0001))
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        self.assertEqual(len(sampled_dataset), sample_size)
        self.assertTrue(set(sampled_dataset).issubset(set(full_dataset)))

    def test_extraction(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for txt_file in sampled_dataset:
            extracted_chars = list(self.processor.process({}, txt_file))
            self.assertTrue(len(extracted_chars) > 0)

            for char, img in extracted_chars:
                self.assertIsInstance(char, str)
                self.assertIsInstance(img, Image.Image)

                # Save the extracted image for manual inspection
                img.save(os.path.join(self.test_output_dir, f"{txt_file}_{char}.png"))

    def test_extraction_validation(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for txt_file in sampled_dataset:
            label_path = os.path.join(self.processor.label_char_dir, txt_file)
            with open(label_path, 'r', encoding='utf-8') as f:
                expected_chars = [line.strip().split(',')[4] for line in f if len(line.strip().split(',')) == 5]

            extracted_chars = [char for char, _ in self.processor.process({}, txt_file)]

            self.assertEqual(len(expected_chars), len(extracted_chars),
                             f"Mismatch in number of characters for {txt_file}")
            self.assertEqual(expected_chars, extracted_chars,
                             f"Mismatch in extracted characters for {txt_file}")

if __name__ == '__main__':
    unittest.main()
