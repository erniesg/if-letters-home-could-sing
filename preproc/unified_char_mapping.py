# preproc/unified_char_mapping.py

import json
import os
import unicodedata
from preproc.utils import is_char_in_font
from preproc.config import FONT_PATH, PUZZLE_PIECES_DIR, M5HISDOC_DIR, DATA_DIR, PROCESSED_DIR

def get_gb2312_80_level1_set():
    gb2312_80_level1 = set()
    for i in range(0x4E00, 0x9FA6):  # Range for CJK Unified Ideographs
        char = chr(i)
        if 'CJK UNIFIED IDEOGRAPH' in unicodedata.name(char, ''):
            gb2312_80_level1.add(char)
    return gb2312_80_level1

class UnifiedCharMapping:
    def __init__(self):
        self.char_to_id = {}
        self.id_to_char = {}
        self.next_id = 0
        self.load_puzzle_pieces_mapping()
        self.new_chars = {
            'M5HisDoc': set(),
            'GB2312-80': set()
        }
        self.output_dir = PROCESSED_DIR  # Use PROCESSED_DIR from config

    def load_puzzle_pieces_mapping(self):
        with open(os.path.join(PUZZLE_PIECES_DIR, 'Chinese_to_ID.json'), 'r', encoding='utf-8') as f:
            self.char_to_id = json.load(f)
        self.id_to_char = {v: k for k, v in self.char_to_id.items()}
        self.next_id = max(map(int, self.char_to_id.values())) + 1

    def get_next_available_id(self):
        while str(self.next_id) in self.id_to_char:
            self.next_id += 1
        return str(self.next_id)

    def add_character(self, char, source):
        if char not in self.char_to_id and is_char_in_font(char, FONT_PATH):
            new_id = self.get_next_available_id()
            self.char_to_id[char] = new_id
            self.id_to_char[new_id] = char
            self.new_chars[source].add(char)
            return True
        return False

    def process_m5hisdoc(self):
        char_dict_path = os.path.join(M5HISDOC_DIR, 'char_dict.txt')
        with open(char_dict_path, 'r', encoding='utf-8') as f:
            m5hisdoc_chars = set(f.read().strip())  # Ensure uniqueness
        for char in m5hisdoc_chars:
            self.add_character(char, 'M5HisDoc')

    def process_gb2312_80(self):
        gb2312_80_set = get_gb2312_80_level1_set()
        for char in gb2312_80_set:
            self.add_character(char, 'GB2312-80')

    def get_mapping(self):
        return self.char_to_id

    def get_reverse_mapping(self):
        return self.id_to_char

    def save_mapping(self):
        os.makedirs(self.output_dir, exist_ok=True)
        char_to_id_path = os.path.join(self.output_dir, 'unified_char_to_id_mapping.json')
        id_to_char_path = os.path.join(self.output_dir, 'unified_id_to_char_mapping.json')

        with open(char_to_id_path, 'w', encoding='utf-8') as f:
            json.dump(self.char_to_id, f, ensure_ascii=False, indent=2)

        with open(id_to_char_path, 'w', encoding='utf-8') as f:
            json.dump(self.id_to_char, f, ensure_ascii=False, indent=2)

    def print_summary(self):
        print(f"Base characters (Puzzle Pieces): {len(self.char_to_id) - sum(len(chars) for chars in self.new_chars.values())}")
        for source, chars in self.new_chars.items():
            print(f"New characters from {source}: {len(chars)}")
        print(f"Total unique characters: {len(self.char_to_id)}")

def create_unified_mapping():
    mapping = UnifiedCharMapping()
    mapping.process_m5hisdoc()
    mapping.process_gb2312_80()
    mapping.save_mapping()
    mapping.print_summary()

if __name__ == "__main__":
    create_unified_mapping()
