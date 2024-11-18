import random
from PIL import ImageFont, Image
import json
import os
import io
import logging

def is_char_in_font(char, font_file):
    try:
        if isinstance(font_file, str):
            font = ImageFont.truetype(font_file, size=12)
        else:
            # Handle BytesIO font file
            font = ImageFont.truetype(font_file, size=12)
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

def save_image_to_s3(s3_hook, image, bucket, key, format='PNG', quality=95):
    """
    Save a PIL Image to S3 with proper error handling and compression

    Args:
        s3_hook: Initialized S3Hook
        image: PIL Image object
        bucket: S3 bucket name
        key: S3 key (path) where image should be saved
        format: Image format to save as
        quality: JPEG quality (0-100) if saving as JPEG

    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        img_byte_arr = io.BytesIO()
        if format.upper() == 'JPEG':
            # Convert to RGB if saving as JPEG
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            image.save(img_byte_arr, format=format, quality=quality, optimize=True)
        else:
            image.save(img_byte_arr, format=format, optimize=True)

        img_byte_arr = img_byte_arr.getvalue()

        s3_hook.load_bytes(
            bytes_data=img_byte_arr,
            key=key,
            bucket_name=bucket,
            replace=True
        )
        return True
    except Exception as e:
        logging.error(f"Failed to save image to S3 {bucket}/{key}: {str(e)}")
        return False
