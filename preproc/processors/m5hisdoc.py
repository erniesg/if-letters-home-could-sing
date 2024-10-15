import os
from PIL import Image
from preproc.config import M5HISDOC_DIR
from preproc.utils import sample_dataset

class M5HisDocProcessor:
    def __init__(self):
        self.label_char_dir = os.path.join(M5HISDOC_DIR, 'M5HisDoc_regular', 'label_char')
        self.images_dir = os.path.join(M5HISDOC_DIR, 'M5HisDoc_regular', 'images')

    def get_full_dataset(self):
        return [f for f in os.listdir(self.label_char_dir) if f.endswith('.txt')]

    def process(self, base_mapping, sample_percentage=1.0):
        full_dataset = self.get_full_dataset()
        sampled_files = sample_dataset(full_dataset, sample_percentage)

        for txt_file in sampled_files:
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
                            char_img = img.crop((x1, y1, x2, y2))
                            yield char, char_img
            except Exception as e:
                print(f"Error processing file {txt_file}: {str(e)}")

def get_full_dataset():
    return M5HisDocProcessor().get_full_dataset()

def process(base_mapping, sample_percentage=1.0):
    return M5HisDocProcessor().process(base_mapping, sample_percentage)
