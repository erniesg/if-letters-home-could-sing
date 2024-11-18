import random
from PIL import ImageFont, Image
import json
import os
import io
import logging

def is_char_in_font(char, font_file):
    """Validate if a character exists in font"""
    try:
        if isinstance(font_file, (str, bytes)):
            font = ImageFont.truetype(font_file, size=12)
        elif isinstance(font_file, io.BytesIO):
            font_file.seek(0)  # Reset buffer position
            font = ImageFont.truetype(font_file, size=12)
        else:
            raise ValueError(f"Unsupported font file type: {type(font_file)}")
            
        # Test character
        font.getmask(char)
        return True
    except Exception as e:
        logging.debug(f"Character '{char}' not in font: {str(e)}")
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

def decode_label(raw_bytes):
    """Decode binary label data to Unicode character"""
    try:
        # Convert two bytes to integer using big-endian
        char_code = int.from_bytes(raw_bytes, byteorder='big')
        # Convert to Unicode character
        return chr(char_code)
    except Exception as e:
        raise ValueError(f"Failed to decode label bytes {raw_bytes.hex()}: {str(e)}")

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
    """Save a PIL Image to S3 with proper error handling and mode conversion"""
    try:
        if not isinstance(image, Image.Image):
            raise ValueError("Input must be a PIL Image object")

        img_byte_arr = io.BytesIO()
        
        # Handle different image modes
        if image.mode == 'L':  # Grayscale
            if format.upper() == 'JPEG':
                # Convert grayscale to RGB for JPEG
                image = image.convert('RGB')
        elif image.mode in ('RGBA', 'P'):
            if format.upper() == 'JPEG':
                image = image.convert('RGB')
            elif format.upper() == 'PNG':
                image = image.convert('RGBA')
        
        # Save with optimizations
        image.save(
            img_byte_arr, 
            format=format,
            optimize=True,
            quality=quality if format.upper() == 'JPEG' else None
        )

        img_byte_arr = img_byte_arr.getvalue()

        s3_hook.load_bytes(
            bytes_data=img_byte_arr,
            key=key,
            bucket_name=bucket,
            replace=True
        )
        logging.info(f"Successfully saved image to {bucket}/{key}")
        return True
    except Exception as e:
        logging.error(f"Failed to save image to S3 {bucket}/{key}: {str(e)}")
        return False