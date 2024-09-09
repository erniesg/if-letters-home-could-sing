import os
import random
import struct
from codecs import decode
import numpy as np
from PIL import Image
from tqdm import tqdm
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from collections import Counter

# Set the base path to your dataset
BASE_PATH = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data"
SAMPLES_DIR = os.path.join(BASE_PATH, "samples")
FONT_PATH = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data/fonts/BabelStoneHan.ttf"

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

def load_and_save_gnt_file(filename):
    """
    Load characters and images from a given GNT file and save them as individual images.
    """
    samples = []
    char_counter = Counter()
    global_counter = 0
    with open(filename, "rb") as f:
        while True:
            try:
                packed_length = f.read(4)
                if packed_length == b'':
                    break

                length = struct.unpack("<I", packed_length)[0]
                raw_label = f.read(2)
                width = struct.unpack("<H", f.read(2))[0]
                height = struct.unpack("<H", f.read(2))[0]
                photo_bytes = f.read(height * width)

                label = decode_label(raw_label)
                unicode_repr = get_unicode_repr(label)

                image = np.frombuffer(photo_bytes, dtype=np.uint8).reshape(height, width)
                pil_image = Image.fromarray(image)

                # Update character counter
                char_counter[label] += 1

                # Save the image
                safe_label = sanitize_filename(label)
                save_path = os.path.join(SAMPLES_DIR, f"gnt_{safe_label}_{unicode_repr}_{char_counter[label]}_{global_counter}.png")
                pil_image.save(save_path)

                samples.append((image, label, unicode_repr, width, height, length))
                global_counter += 1

            except Exception as e:
                print(f"Error processing sample: {e}")
                continue

    return samples, char_counter

def process_gnt_files():
    """
    Process all GNT files in the dataset.
    """
    # Create samples directory if it doesn't exist
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    # Get all GNT directories
    gnt_dirs = [
        "Gnt1.0TrainPart1", "Gnt1.0TrainPart2", "Gnt1.0TrainPart3",
        "Gnt1.1Test", "Gnt1.1TrainPart1", "Gnt1.1TrainPart2",
        "Gnt1.2Test", "Gnt1.2TrainPart1", "Gnt1.2TrainPart2"
    ]

    # Select a random GNT directory
    random_dir = random.choice(gnt_dirs)
    dir_path = os.path.join(BASE_PATH, random_dir)

    # Get all GNT files in the selected directory
    gnt_files = [f for f in os.listdir(dir_path) if f.endswith('.gnt')]

    # Select a random GNT file
    random_gnt = random.choice(gnt_files)
    random_gnt_path = os.path.join(dir_path, random_gnt)
    print(f"Selected GNT file: {random_gnt_path}")

    # Load samples from the selected GNT file
    samples, char_counter = load_and_save_gnt_file(random_gnt_path)
    print(f"Total samples in this file: {len(samples)}")

    # Print file type, height, width, and size of each character image
    print("\nSample of character image details:")
    for i, (image, label, unicode_repr, width, height, length) in enumerate(random.sample(samples, min(5, len(samples)))):
        print(f"Character: {label} (Unicode: {unicode_repr}), Width: {width}, Height: {height}, Size: {length} bytes")

    # Find characters with greatest and least occurrences
    most_common = char_counter.most_common(1)[0]
    least_common = char_counter.most_common()[-1]

    print(f"\nCharacter with the most occurrences: '{most_common[0]}' ({most_common[1]} times)")
    print(f"Character with the least occurrences: '{least_common[0]}' ({least_common[1]} times)")

    # Set up the font for Chinese character display
    font_prop = FontProperties(fname=FONT_PATH)

    # Display a grid of random samples
    num_samples = min(25, len(samples))
    fig, axes = plt.subplots(5, 5, figsize=(15, 15))
    fig.suptitle(f"Random Samples from {random_gnt}", fontsize=16)

    for i, ax in enumerate(axes.flat):
        if i < num_samples:
            image, label, unicode_repr, width, height, _ = random.choice(samples)
            ax.imshow(image, cmap='gray')
            ax.axis('off')
            ax.set_title(f"Label: {label}\nUnicode: {unicode_repr}\nSize: {width}x{height}\nCount: {char_counter[label]}", fontproperties=font_prop)
        else:
            ax.axis('off')

    plt.tight_layout()
    plt.show()

    # Display statistics about image sizes
    widths = [sample[3] for sample in samples]
    heights = [sample[4] for sample in samples]

    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    plt.hist(widths, bins=20, edgecolor='black')
    plt.title("Distribution of Image Widths")
    plt.xlabel("Width")
    plt.ylabel("Frequency")

    plt.subplot(1, 2, 2)
    plt.hist(heights, bins=20, edgecolor='black')
    plt.title("Distribution of Image Heights")
    plt.xlabel("Height")
    plt.ylabel("Frequency")

    plt.tight_layout()
    plt.show()

    # Display histogram of character frequencies
    plt.figure(figsize=(12, 6))
    plt.hist(char_counter.values(), bins=50, edgecolor='black')
    plt.title("Histogram of Character Frequencies")
    plt.xlabel("Number of Occurrences")
    plt.ylabel("Number of Characters")
    plt.yscale('log')  # Use log scale for y-axis due to potential large differences
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    process_gnt_files()
