import random
from PIL import ImageFont, Image
import json
import os

def is_char_in_font(char, font_path):
    try:
        font = ImageFont.truetype(font_path, size=12)
        font.getmask(char)
        return True
    except:
        return False

def sample_dataset(full_dataset, sample_percentage):
    if not 0 < sample_percentage <= 1:
        raise ValueError("sample_percentage must be between 0 and 1")

    sample_size = int(len(full_dataset) * sample_percentage)
    return random.sample(full_dataset, sample_size)

def load_char_mappings(char_to_id_path, id_to_char_path):
    with open(char_to_id_path, 'r', encoding='utf-8') as f:
        char_to_id = json.load(f)
    with open(id_to_char_path, 'r', encoding='utf-8') as f:
        id_to_char = json.load(f)
    return char_to_id, id_to_char

def validate_extraction(extracted_chars, label_path, char_to_id, font_path):
    with open(label_path, 'r', encoding='utf-8') as f:
        expected_chars = [line.strip().split(',')[4] for line in f
                          if len(line.strip().split(',')) == 5 and
                          is_char_in_font(line.strip().split(',')[4], font_path) and
                          line.strip().split(',')[4] in char_to_id]

    return expected_chars == extracted_chars

def validate_output_structure(output_dir, char_to_id, id_to_char):
    for char_id in os.listdir(output_dir):
        if char_id not in id_to_char:
            return False
        char_dir = os.path.join(output_dir, char_id)
        if not os.path.isdir(char_dir):
            return False
        if not any(file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')) for file in os.listdir(char_dir)):
            return False
    return True

def count_extracted_images(output_dir):
    char_counts = {}
    for char_id in os.listdir(output_dir):
        char_dir = os.path.join(output_dir, char_id)
        if not os.path.isdir(char_dir):
            continue
        char_counts[char_id] = {}
        for img_file in os.listdir(char_dir):
            if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                dataset_name = img_file.split('_')[0]
                char_counts[char_id][dataset_name] = char_counts[char_id].get(dataset_name, 0) + 1
    return char_counts

def decode_label(raw_label):
    encodings = ['gbk', 'gb18030', 'utf-8', 'ascii']
    for encoding in encodings:
        try:
            return raw_label.decode(encoding)
        except UnicodeDecodeError:
            continue
    return f"unknown_{raw_label.hex()}"

def get_unicode_repr(label):
    return 'U+' + ''.join([f'{ord(c):04X}' for c in label])

def sanitize_filename(label):
    return ''.join(c if c.isalnum() else '_' for c in label)

def save_combined_image(char_id, image, dataset_name, filename, combined_dir):
    combined_char_dir = os.path.join(combined_dir, char_id)
    os.makedirs(combined_char_dir, exist_ok=True)
    combined_filename = f"{dataset_name}_{filename}"
    combined_path = os.path.join(combined_char_dir, combined_filename)
    image.save(combined_path)
