# tests/test_base_mapping.py

import unittest
from preproc.base_mapping import BaseCharacterMapping
from preproc.config import PUZZLE_PIECES_DIR
import os

class TestBaseMapping(unittest.TestCase):
    def setUp(self):
        self.base_mapping = BaseCharacterMapping()
        chinese_to_id_path = os.path.join(PUZZLE_PIECES_DIR, 'Chinese_to_ID.json')
        id_to_chinese_path = os.path.join(PUZZLE_PIECES_DIR, 'ID_to_Chinese.json')
        self.base_mapping.load_initial_mapping(chinese_to_id_path, id_to_chinese_path)

    def test_initial_mapping_loaded(self):
        self.assertGreater(len(self.base_mapping.char_to_id), 0)
        self.assertEqual(len(self.base_mapping.char_to_id), len(self.base_mapping.id_to_char))

    def test_mapping_reversibility(self):
        for char, id in self.base_mapping.char_to_id.items():
            self.assertEqual(self.base_mapping.id_to_char[id], char)
            self.assertEqual(self.base_mapping.char_to_id[char], id)

if __name__ == '__main__':
    unittest.main()
