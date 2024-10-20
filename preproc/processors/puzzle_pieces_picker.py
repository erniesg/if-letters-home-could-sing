import os
from PIL import Image
from tqdm import tqdm
from preproc.config import PUZZLE_PIECES_DIR, PROCESSED_DIR

class PuzzlePiecesPicker:
    def __init__(self):
        self.dataset_dir = os.path.join(PUZZLE_PIECES_DIR, 'Dataset')
        self.output_dir = os.path.join(PROCESSED_DIR, 'PuzzlePiecesPicker')
        self.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        self.dataset_name = 'PuzzlePiecesPicker'
        self.folder_ids = [f for f in os.listdir(self.dataset_dir) if os.path.isdir(os.path.join(self.dataset_dir, f))]

    def get_full_dataset(self):
        return self.folder_ids

    def process(self, samples):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.progress_dir, exist_ok=True)
        char_counters = {}
        total_folders = len(samples)
        total_images = sum(len([f for f in os.listdir(os.path.join(self.dataset_dir, folder_id))
                                if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                           for folder_id in samples)

        print(f"Processing {total_folders} folders containing {total_images} images")

        with tqdm(total=total_folders, desc=f"Processing {self.dataset_name} folders") as folder_pbar:
            for folder_id in samples:
                char_counters[folder_id] = char_counters.get(folder_id, 0)
                folder_path = os.path.join(self.dataset_dir, folder_id)
                images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

                with tqdm(total=len(images), desc=f"Folder {folder_id}", leave=False) as image_pbar:
                    for img_file in images:
                        img_path = os.path.join(folder_path, img_file)
                        try:
                            with Image.open(img_path) as img:
                                char_counters[folder_id] += 1
                                filename = f"{self.dataset_name}_{folder_id}_{char_counters[folder_id]}.png"
                                yield folder_id, img.copy(), self.dataset_name, filename
                        except Exception as e:
                            print(f"Error processing image {img_path}: {e}")
                        image_pbar.update(1)
                folder_pbar.update(1)

def get_full_dataset():
    return PuzzlePiecesPicker().get_full_dataset()

def process(samples):
    processor = PuzzlePiecesPicker()
    return processor.process(samples)
