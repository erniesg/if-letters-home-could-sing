import random
from PIL import ImageFont

def is_char_in_font(char, font_path):
    try:
        font = ImageFont.truetype(font_path, size=12)
        font.getmask(char)
        return True
    except:
        return False

def sample_dataset(full_dataset, sample_percentage):
    if not 0 <= sample_percentage <= 1:
        raise ValueError("sample_percentage must be between 0 and 1")

    sample_size = int(len(full_dataset) * sample_percentage)
    return random.sample(full_dataset, sample_size)
