import os
import json
from PIL import Image
from tqdm import tqdm
from preproc.config import PUZZLE_PIECES_DIR
from preproc.utils import sample_dataset

class PuzzlePiecesPicker:
    def __init__(self):
        self.dataset_dir = os.path.join(PUZZLE_PIECES_DIR, 'Dataset')
        self.chinese_to_id_path = os.path.join(PUZZLE_PIECES_DIR, 'Chinese_to_ID.json')
        self.id_to_chinese_path = os.path.join(PUZZLE_PIECES_DIR, 'ID_to_Chinese.json')
        self.chinese_to_id = self.load_json(self.chinese_to_id_path)
        self.id_to_chinese = self.load_json(self.id_to_chinese_path)
        self.folder_ids = [f for f in os.listdir(self.dataset_dir) if os.path.isdir(os.path.join(self.dataset_dir, f))]

    @staticmethod
    def load_json(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_full_dataset(self):
        return self.folder_ids

    def process(self, base_mapping, sample_percentage=1.0):
        sampled_folders = sample_dataset(self.folder_ids, sample_percentage)

        for folder_id in tqdm(sampled_folders, desc="Processing Puzzle Pieces"):
            char = self.id_to_chinese.get(folder_id)
            if char is None:
                print(f"Warning: No character found for folder ID {folder_id}")
                continue

            folder_path = os.path.join(self.dataset_dir, folder_id)
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

            for img_file in images:
                img_path = os.path.join(folder_path, img_file)
                try:
                    with Image.open(img_path) as img:
                        yield char, img
                except Exception as e:
                    print(f"Error processing image {img_path}: {e}")

def get_full_dataset():
    return PuzzlePiecesPicker().get_full_dataset()

def process(base_mapping, sample_percentage=1.0):
    processor = PuzzlePiecesPicker()
    return processor.process(base_mapping, sample_percentage)
