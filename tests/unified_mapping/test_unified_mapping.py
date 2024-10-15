# tests/unified_mapping/test_unified_mapping.py

import unittest
import os
import json
import shutil
from io import StringIO
import sys
from preproc.unified_char_mapping import UnifiedCharMapping, get_gb2312_80_level1_set
from preproc.utils import is_char_in_font
from preproc.config import FONT_PATH, PUZZLE_PIECES_DIR, DATA_DIR, M5HISDOC_DIR

class TestUnifiedCharMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for test outputs
        cls.test_output_dir = os.path.join(DATA_DIR, 'test_processed')
        os.makedirs(cls.test_output_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Remove the temporary directory and its contents
        shutil.rmtree(cls.test_output_dir)

    def setUp(self):
        self.mapping = UnifiedCharMapping()
        self.mapping.output_dir = self.test_output_dir  # Use the test output directory
        with open(os.path.join(PUZZLE_PIECES_DIR, 'Chinese_to_ID.json'), 'r', encoding='utf-8') as f:
            self.original_mapping = json.load(f)

    def tearDown(self):
        # Clean up any files created during individual tests
        for filename in os.listdir(self.test_output_dir):
            file_path = os.path.join(self.test_output_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    def test_original_mapping_preserved(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        new_mapping = self.mapping.get_mapping()
        for char, id in self.original_mapping.items():
            self.assertEqual(new_mapping[char], id, f"Original mapping not preserved for character {char}")

    def test_no_out_of_font_chars(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        for char in self.mapping.get_mapping().keys():
            self.assertTrue(is_char_in_font(char, FONT_PATH), f"Character {char} not in BabelStone Han font")

    def test_no_duplicate_chars(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        mapping = self.mapping.get_mapping()
        self.assertEqual(len(mapping), len(set(mapping.keys())), "Duplicate characters found")

    def test_no_duplicate_ids(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        mapping = self.mapping.get_mapping()
        self.assertEqual(len(mapping), len(set(mapping.values())), "Duplicate IDs found")

    def test_new_chars_added(self):
        original_count = len(self.mapping.get_mapping())
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        new_count = len(self.mapping.get_mapping())
        self.assertGreater(new_count, original_count, "No new characters added")

    def test_gb2312_80_chars_added(self):
        gb2312_80_set = get_gb2312_80_level1_set()
        self.mapping.process_gb2312_80()
        for char in gb2312_80_set:
            self.assertIn(char, self.mapping.get_mapping(), f"GB2312-80 character {char} not added to mapping")

    def test_m5hisdoc_chars_added(self):
        m5hisdoc_path = os.path.join(M5HISDOC_DIR, 'char_dict.txt')
        with open(m5hisdoc_path, 'r', encoding='utf-8') as f:
            m5hisdoc_chars = set(f.read().strip())
        self.mapping.process_m5hisdoc()
        not_added = []
        not_in_font = []
        for char in m5hisdoc_chars:
            if char not in self.mapping.get_mapping():
                if is_char_in_font(char, FONT_PATH):
                    not_added.append(char)
                else:
                    not_in_font.append(char)
        if not_added:
            print(f"Characters in font but not added from M5HisDoc: {not_added}")
        if not_in_font:
            print(f"Characters not in BabelStone Han font: {not_in_font}")
        self.assertEqual(len(not_added), 0, f"{len(not_added)} M5HisDoc characters in font but not added to mapping")

    def test_save_mapping(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        self.mapping.save_mapping()
        output_path = os.path.join(self.test_output_dir, 'unified_char_mapping.json')
        self.assertTrue(os.path.exists(output_path), "Unified mapping file not created")
        with open(output_path, 'r', encoding='utf-8') as f:
            saved_mapping = json.load(f)
        self.assertEqual(self.mapping.get_mapping(), saved_mapping, "Saved mapping does not match the original")

    def test_print_summary(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        captured_output = StringIO()
        sys.stdout = captured_output
        self.mapping.print_summary()
        sys.stdout = sys.__stdout__  # Reset redirect
        summary = captured_output.getvalue()
        self.assertIn("Base characters (Puzzle Pieces):", summary)
        self.assertIn("New characters from M5HisDoc:", summary)
        self.assertIn("New characters from GB2312-80:", summary)
        self.assertIn("Total unique characters:", summary)

    def test_id_assignment(self):
        max_original_id = max(map(int, self.original_mapping.values()))
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        new_mapping = self.mapping.get_mapping()
        for char, id in new_mapping.items():
            if char not in self.original_mapping:
                self.assertGreater(int(id), max_original_id, f"New character {char} not assigned a new ID")

    def test_all_chars_in_mapping(self):
        self.mapping.process_m5hisdoc()
        self.mapping.process_gb2312_80()
        all_chars = set(self.original_mapping.keys())
        all_chars.update(get_gb2312_80_level1_set())
        with open(os.path.join(M5HISDOC_DIR, 'char_dict.txt'), 'r', encoding='utf-8') as f:
            all_chars.update(f.read().strip())
        not_in_mapping = []
        for char in all_chars:
            if is_char_in_font(char, FONT_PATH) and char not in self.mapping.get_mapping():
                not_in_mapping.append(char)
        if not_in_mapping:
            print(f"Characters in font but missing from final mapping: {not_in_mapping}")
        self.assertEqual(len(not_in_mapping), 0, f"{len(not_in_mapping)} characters in font but missing from final mapping")

if __name__ == '__main__':
    unittest.main()
