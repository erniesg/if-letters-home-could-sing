# preproc/unified_char_mapping.py

import json
import os
import unicodedata
import logging
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from preproc.utils import is_char_in_font
from preproc.config import (
    FONT_PATH, PUZZLE_PIECES_DIR, M5HISDOC_DIR, HIT_OR3C_DIR,
    CASIA_HWDB_DIR, DATA_DIR, PROCESSED_DIR, DATASET_CONFIG
)

def get_gb2312_80_level1_set():
    gb2312_80_level1 = set()
    for i in range(0x4E00, 0x9FA6):  # Range for CJK Unified Ideographs
        char = chr(i)
        if 'CJK UNIFIED IDEOGRAPH' in unicodedata.name(char, ''):
            gb2312_80_level1.add(char)
    return gb2312_80_level1

def verify_dataset_paths():
    """Verify that enabled dataset paths exist"""
    for dataset, config in DATASET_CONFIG.items():
        if config['enabled']:
            if not os.path.exists(config['path']):
                logging.warning(f"Dataset {dataset} is enabled but path {config['path']} does not exist")
                return False
    return True

class UnifiedCharMapping:
    def __init__(self):
        self.char_to_id = {}
        self.id_to_char = {}
        self.next_id = 0
        self.output_dir = PROCESSED_DIR

        # Initialize new_chars based on config keys
        self.new_chars = {}
        for dataset in DATASET_CONFIG:
            self.new_chars[dataset] = set()
        # Add GB2312-80 separately as it's a character standard
        self.new_chars['GB2312-80'] = set()
        
        # Load baseline mapping from Puzzle Pieces
        self.load_puzzle_pieces_mapping()

        # Load baseline mapping from Puzzle Pieces
        self.load_puzzle_pieces_mapping()

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
        """Process M5HisDoc dataset characters"""
        if not os.path.exists(M5HISDOC_DIR):
            logging.warning(f"M5HisDoc directory not found at {M5HISDOC_DIR}")
            return

        char_dict_path = os.path.join(M5HISDOC_DIR, 'char_dict.txt')
        if not os.path.exists(char_dict_path):
            logging.warning(f"char_dict.txt not found at {char_dict_path}")
            return

        try:
            with open(char_dict_path, 'r', encoding='utf-8') as f:
                m5hisdoc_chars = set(f.read().strip().split())  # Split into individual characters
            logging.info(f"Found {len(m5hisdoc_chars)} unique characters in M5HisDoc")
            for char in m5hisdoc_chars:
                self.add_character(char, 'm5hisdoc')  # Must match key in DATASET_CONFIG
        except Exception as e:
            logging.error(f"Error processing M5HisDoc characters: {str(e)}")
            raise

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

    # Process M5HisDoc if enabled
    if DATASET_CONFIG['m5hisdoc']['enabled']:
        mapping.process_m5hisdoc()

    # Process GB2312-80 if any dataset needs it
    if any(DATASET_CONFIG[d]['enabled'] and DATASET_CONFIG[d].get('use_gb2312')
           for d in ['hit_or3c', 'casia_hwdb']):
        mapping.process_gb2312_80()

    mapping.save_mapping()
    mapping.print_summary()
    return mapping

def _read_label_file(file_path, encoding='utf-8'):
    """Helper to read label files in different formats"""
    ext = os.path.splitext(file_path)[1]
    if ext == '.json':
        with open(file_path, 'r', encoding=encoding) as f:
            return set(json.load(f).keys())
    else:
        with open(file_path, 'r', encoding=encoding) as f:
            return set(f.read().strip())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not verify_dataset_paths():
        logging.error("Some enabled dataset paths are missing. Please check your configuration.")
        exit(1)

    try:
        logging.info("Starting unified character mapping creation...")
        mapping = create_unified_mapping()
        logging.info("Character mapping creation completed successfully!")
    except Exception as e:
        logging.error(f"Error creating unified mapping: {str(e)}")
        exit(1)
