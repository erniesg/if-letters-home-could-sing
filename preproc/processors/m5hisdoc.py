import os
from PIL import Image
from preproc.config import M5HISDOC_DIR, PROCESSED_DIR, FONT_PATH
from preproc.utils import is_char_in_font, save_combined_image
from preproc.counter import Counter
from preproc.tracker import ProgressTracker
from tqdm import tqdm

class M5HisDocProcessor:
    def __init__(self):
        self.label_char_dir = os.path.join(M5HISDOC_DIR, 'M5HisDoc_regular', 'label_char')
        self.images_dir = os.path.join(M5HISDOC_DIR, 'M5HisDoc_regular', 'images')
        self.output_dir = os.path.join(PROCESSED_DIR, 'M5HisDoc')
        self.progress_dir = os.path.join(PROCESSED_DIR, 'progress')
        self.dataset_name = 'M5HisDoc'
        self.counter = Counter(self.dataset_name, self.progress_dir)
        self.progress_tracker = ProgressTracker(self.dataset_name, self.progress_dir)

    def get_full_dataset(self):
        return [f for f in os.listdir(self.label_char_dir) if f.endswith('.txt')]

    def process(self, char_to_id, samples):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.progress_dir, exist_ok=True)
        self.progress_tracker.set_total_samples(len(samples))
        for txt_file in tqdm(samples, desc=f"Processing {self.dataset_name} samples"):
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
                                filename = self.counter.get_filename(char_id)
                                yield char_id, char_img, self.dataset_name, filename
                self.progress_tracker.increment_processed()
                tqdm.write(f"Processed: {self.progress_tracker.processed_samples}/{self.progress_tracker.total_samples}")
            except Exception as e:
                print(f"Error processing file {txt_file}: {str(e)}")

def get_full_dataset():
    return M5HisDocProcessor().get_full_dataset()

def process(char_to_id, samples):
    return M5HisDocProcessor().process(char_to_id, samples)

def process_all(char_to_id, combined_dir):
    processor = M5HisDocProcessor()
    samples = processor.get_full_dataset()
    for char_id, image, dataset_name, filename in processor.process(char_to_id, samples):
        save_combined_image(char_id, image, dataset_name, filename, combined_dir)
        yield char_id, image, dataset_name, filename
