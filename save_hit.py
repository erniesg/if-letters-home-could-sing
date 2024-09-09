import struct
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import os
import random
from matplotlib.font_manager import FontProperties
from collections import Counter
from PIL import Image

# Set the base path to your dataset
BASE_PATH = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data/character"
SAMPLES_DIR = os.path.join(BASE_PATH, "samples-hit")
FONT_PATH = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data/fonts/BabelStoneHan.ttf"

def decode_label(raw_label):
    encodings = ['gb2312', 'gbk', 'gb18030', 'utf-8', 'ascii']
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

class HITOR3C:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.labels_file = self.data_dir / "labels.txt"
        self.image_files = sorted([f for f in self.data_dir.glob("*_images") if f.is_file()])

    def read_labels(self):
        labels = []
        with open(self.labels_file, 'rb') as f:
            content = f.read()
            for i in range(0, len(content), 2):
                raw_label = content[i:i+2]
                label = decode_label(raw_label)
                labels.append(label)
        return labels

    def read_images(self, file_path):
        images = []
        with open(file_path, 'rb') as f:
            total_char_number = struct.unpack('<I', f.read(4))[0]
            height = struct.unpack('B', f.read(1))[0]
            width = struct.unpack('B', f.read(1))[0]
            print(f"Number of characters in image file: {total_char_number}")
            print(f"Image height: {height}, width: {width}")

            for _ in range(total_char_number):
                pix_gray = np.frombuffer(f.read(width * height), dtype=np.uint8).reshape(height, width)
                images.append(pix_gray)
        return images, (height, width)

    def process_and_save(self, output_dir, num_samples=20):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        labels = self.read_labels()
        print(f"Total labels: {len(labels)}")

        # Randomly select an image file
        sampled_image_file = random.choice(self.image_files)
        print(f"Sampling from image file: {sampled_image_file}")
        images, image_shape = self.read_images(sampled_image_file)

        samples_to_take = min(num_samples, len(labels), len(images))
        samples = []
        char_counter = Counter()

        for i in range(samples_to_take):
            label = labels[i]
            image = images[i]
            unicode_repr = get_unicode_repr(label)

            # Update character counter
            char_counter[label] += 1

            # Save the image
            safe_label = sanitize_filename(label)
            save_path = os.path.join(output_dir, f"hit_{safe_label}_{unicode_repr}_{char_counter[label]}_{i}.png")
            Image.fromarray(image).save(save_path)

            samples.append((image, label, unicode_repr, image_shape[1], image_shape[0]))

        print(f"Saved {samples_to_take} samples to {output_dir}")
        return samples, char_counter, image_shape

def visualize_samples(samples, char_counter, image_shape, num_samples=25):
    num_samples = min(num_samples, len(samples))
    rows = int(np.ceil(np.sqrt(num_samples)))
    fig, axes = plt.subplots(rows, rows, figsize=(15, 15))
    fig.suptitle("Random Samples from HIT-OR3C", fontsize=16)

    font_prop = FontProperties(fname=FONT_PATH)

    for i, ax in enumerate(axes.flat):
        if i < num_samples:
            image, label, unicode_repr, width, height = random.choice(samples)
            ax.imshow(image, cmap='gray')
            ax.axis('off')
            ax.set_title(f"Label: {label}\nUnicode: {unicode_repr}\nSize: {width}x{height}\nCount: {char_counter[label]}", fontproperties=font_prop)
        else:
            ax.axis('off')

    plt.tight_layout()
    plt.show()

def plot_statistics(samples, char_counter, image_shape):
    font_prop = FontProperties(fname=FONT_PATH)

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

    # Character frequency
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(char_counter)), sorted(char_counter.values(), reverse=True))
    plt.title("Character Frequency", fontproperties=font_prop)
    plt.xlabel("Characters (sorted by frequency)", fontproperties=font_prop)
    plt.ylabel("Frequency", fontproperties=font_prop)
    plt.yscale('log')
    plt.tight_layout()
    plt.show()

def main():
    data_dir = BASE_PATH
    output_dir = SAMPLES_DIR

    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")

    dataset = HITOR3C(data_dir)

    # Process and save samples
    samples, char_counter, image_shape = dataset.process_and_save(output_dir, num_samples=3897)  # Use the same number as in CASIA example

    # Print some statistics
    print(f"\nTotal samples: {len(samples)}")
    print(f"Unique characters: {len(char_counter)}")
    print(f"Image dimensions: {image_shape}")

    # Print sample of character image details
    print("\nSample of character image details:")
    for image, label, unicode_repr, width, height in random.sample(samples, min(5, len(samples))):
        print(f"Character: {label} (Unicode: {unicode_repr}), Width: {width}, Height: {height}")

    # Find characters with greatest and least occurrences
    most_common = char_counter.most_common(1)[0]
    least_common = char_counter.most_common()[-1]

    print(f"\nCharacter with the most occurrences: '{most_common[0]}' ({most_common[1]} times)")
    print(f"Character with the least occurrences: '{least_common[0]}' ({least_common[1]} times)")

    # Visualize samples
    visualize_samples(samples, char_counter, image_shape)

    # Plot statistics
    plot_statistics(samples, char_counter, image_shape)

if __name__ == "__main__":
    main()
