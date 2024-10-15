import os

import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

FONT_PATH = os.path.join(DATA_DIR, 'fonts', 'BabelStoneHan.ttf')
PUZZLE_PIECES_DIR = os.path.join(DATA_DIR, 'Puzzle-Pieces-Picker Dataset')
M5HISDOC_DIR = os.path.join(DATA_DIR, 'M5HisDoc')
CASIA_HWDB_DIR = os.path.join(DATA_DIR, 'CASIA-HWDB')
COMBINED_DIR = os.path.join(DATA_DIR, 'combined')
LOGS_DIR = os.path.join(PROJECT_DIR, 'logs')
