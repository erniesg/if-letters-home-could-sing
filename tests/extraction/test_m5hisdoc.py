import unittest
import os
import shutil
from PIL import Image
from preproc.processors.m5hisdoc import M5HisDocProcessor
from preproc.config import DATA_DIR, PROCESSED_DIR, M5HISDOC_DIR, FONT_PATH
from preproc.utils import sample_dataset, load_char_mappings, validate_extraction, validate_output_structure, count_extracted_images

class TestM5HisDocProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processor = M5HisDocProcessor()
        cls.test_output_dir = os.path.join(PROCESSED_DIR, 'M5HisDoc_test')
        os.makedirs(cls.test_output_dir, exist_ok=True)
        cls.char_to_id_path = os.path.join(DATA_DIR, 'processed', 'unified_char_to_id_mapping.json')
        cls.id_to_char_path = os.path.join(DATA_DIR, 'processed', 'unified_id_to_char_mapping.json')
        cls.char_to_id, cls.id_to_char = load_char_mappings(cls.char_to_id_path, cls.id_to_char_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_output_dir)

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

        for txt_file in sampled_dataset:
            extracted_chars = list(self.processor.process(self.char_to_id, txt_file))
            self.assertTrue(len(extracted_chars) > 0)

            for char, img, dataset_name in extracted_chars:
                self.assertIsInstance(char, str)
                self.assertIsInstance(img, Image.Image)
                self.assertEqual(dataset_name, 'M5HisDoc')
                self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

                # Save the extracted image for manual inspection
                img.save(os.path.join(self.test_output_dir, f"{dataset_name}_{txt_file}_{char}.png"))

    def test_extraction_validation(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for txt_file in sampled_dataset:
            label_path = os.path.join(self.processor.label_char_dir, txt_file)
            extracted_chars = [char for char, _ in self.processor.process(self.char_to_id, txt_file)]

            self.assertTrue(validate_extraction(extracted_chars, label_path, self.char_to_id, FONT_PATH),
                            f"Extraction validation failed for {txt_file}")

    def test_output_structure(self):
        full_dataset = self.processor.get_full_dataset()
        sampled_dataset = sample_dataset(full_dataset, 0.0001)

        for txt_file in sampled_dataset:
            for char, img in self.processor.process(self.char_to_id, txt_file):
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

        actual_counts = count_extracted_images(self.test_output_dir)
        self.assertEqual(expected_counts, actual_counts, "Mismatch in extracted image counts")

if __name__ == '__main__':
    unittest.main()
