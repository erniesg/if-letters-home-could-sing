import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
FONT_PATH = os.path.join(DATA_DIR, 'fonts', 'BabelStoneHan.ttf')
PUZZLE_PIECES_DIR = os.path.join(DATA_DIR, 'puzzle-pieces-picker')  # Matches actual directory name
M5HISDOC_DIR = os.path.join(DATA_DIR, 'M5HisDoc')
CASIA_HWDB_DIR = os.path.join(DATA_DIR, 'CASIA-HWDB')
HIT_OR3C_DIR = os.path.join(DATA_DIR, 'character')  # Add this line
COMBINED_DIR = os.path.join(DATA_DIR, 'combined')
LOGS_DIR = os.path.join(PROJECT_DIR, 'logs')
def validate_path(path, dataset_name):
    """Validate if a path exists and log warning if it doesn't"""
    if not os.path.exists(path):
        print(f"Warning: {dataset_name} path doesn't exist at: {path}")
        print(f"Current working directory: {os.getcwd()}")
        return False
    return True

# Validate critical paths
if not validate_path(PUZZLE_PIECES_DIR, "Puzzle Pieces"):
    print(f"Please ensure Puzzle Pieces dataset is in: {PUZZLE_PIECES_DIR}")
    print("Expected structure:")
    print("  data/")
    print("    puzzle-pieces-picker/")
    print("      Chinese_to_ID.json")
    print("      ID_to_Chinese.json")
    print("      ...")
# Dataset Processing Configuration
DATASET_CONFIG = {
    'puzzle_pieces': {
        'enabled': True,  # Must always be True as baseline
        'path': PUZZLE_PIECES_DIR,
        'label_file': 'Chinese_to_ID.json',  # Base mapping file
        'has_dataset_folder': True,  # Contains Dataset/ folder
        'has_font_folder': True      # Contains Font Generation/ folder
    },
    'm5hisdoc': {
        'enabled': True,
        'path': M5HISDOC_DIR,
        'label_file': 'char_dict.txt'
    },
    'hit_or3c': {
        'enabled': True,
        'path': HIT_OR3C_DIR,
        'use_gb2312': True  # Uses GB2312-80 standard
    },
    'casia_hwdb': {
        'enabled': False,  # Currently unavailable
        'path': CASIA_HWDB_DIR,
        'use_gb2312': True
    }
}
