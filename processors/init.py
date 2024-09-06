from .puzzle_pieces_processor import PuzzlePiecesProcessor
from .m5hisdoc_processor import M5HisDocProcessor
from .casia_hwdb_processor import CasiaHWDBProcessor

def get_processor(dataset_name):
    if dataset_name == 'puzzle-pieces-picker':
        return PuzzlePiecesProcessor()
    elif dataset_name == 'm5hisdoc':
        return M5HisDocProcessor()
    elif dataset_name == 'casia-hwdb':
        return CasiaHWDBProcessor()
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")
