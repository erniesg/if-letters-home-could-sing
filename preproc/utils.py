import random
from PIL import ImageFont
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
        char = id_to_char[char_id]
        if char not in char_to_id or char_to_id[char] != char_id:
            return False
    return True

def count_extracted_images(output_dir):
    char_counts = {}
    for char_id in os.listdir(output_dir):
        char_dir = os.path.join(output_dir, char_id)
        char_counts[char_id] = {}
        for img_file in os.listdir(char_dir):
            if img_file.endswith('.png'):
                dataset_name = img_file.split('_')[0]
                char_counts[char_id][dataset_name] = char_counts[char_id].get(dataset_name, 0) + 1
    return char_counts
