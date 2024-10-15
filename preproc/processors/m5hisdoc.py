import os
from PIL import Image
from preproc.config import M5HISDOC_DIR, PROCESSED_DIR, FONT_PATH
from preproc.utils import sample_dataset, is_char_in_font

class M5HisDocProcessor:
    def __init__(self):
        self.label_char_dir = os.path.join(M5HISDOC_DIR, 'M5HisDoc_regular', 'label_char')
        self.images_dir = os.path.join(M5HISDOC_DIR, 'M5HisDoc_regular', 'images')
        self.output_dir = os.path.join(PROCESSED_DIR, 'M5HisDoc')
        self.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        self.dataset_name = 'M5HisDoc'

    def get_full_dataset(self):
        return [f for f in os.listdir(self.label_char_dir) if f.endswith('.txt')]

    def process(self, char_to_id, samples):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.progress_dir, exist_ok=True)
        for txt_file in samples:
            img_file = txt_file.replace('.txt', '.jpg')
            img_path = os.path.join(self.images_dir, img_file)
            label_path = os.path.join(self.label_char_dir, txt_file)

            if not os.path.exists(img_path):
                print(f"Warning: Image file not found for {txt_file}")
                continue

            try:
                with Image.open(img_path) as img, open(label_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) == 5:
                            x1, y1, x2, y2, char = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
                            if is_char_in_font(char, FONT_PATH) and char in char_to_id:
                                char_img = img.crop((x1, y1, x2, y2))
                                char_id = char_to_id[char]
                                filename = f"{self.dataset_name}_{char_id}_{txt_file}_{x1}_{y1}.png"
                                yield char_id, char_img, self.dataset_name, filename
            except Exception as e:
                print(f"Error processing file {txt_file}: {str(e)}")

def get_full_dataset():
    return M5HisDocProcessor().get_full_dataset()

def process(char_to_id, samples):
    return M5HisDocProcessor().process(char_to_id, samples)
