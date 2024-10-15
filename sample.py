import os
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def load_labels(label_file):
    with open(label_file, 'r', encoding='utf-8') as f:
        return [line.strip().split(',') for line in f]

def draw_boxes(image, labels, color):
    for label in labels:
        x1, y1, x2, y2 = map(int, label[:4])
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

def draw_text_lines(image, text_lines):
    for line in text_lines:
        points = np.array([list(map(float, line[:8]))], dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(image, [points], True, (0, 255, 255), 2)

def put_chinese_text(img, text, position, font_path, font_size, color):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, font_size)
    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def sample_and_display(image_dir, char_label_dir, line_label_dir, font_path, num_samples=3):
    image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
    sampled_images = random.sample(image_files, num_samples)

    for img_file in sampled_images:
        img_path = os.path.join(image_dir, img_file)
        char_label_path = os.path.join(char_label_dir, img_file.replace('.jpg', '.txt'))
        line_label_path = os.path.join(line_label_dir, img_file.replace('.jpg', '.txt'))

        image = cv2.imread(img_path)
        char_labels = load_labels(char_label_path)
        line_labels = load_labels(line_label_path)

        draw_boxes(image, char_labels, (0, 255, 0))  # Green for characters
        draw_text_lines(image, line_labels)

        # Create a blank image for text with the same height as the input image
        text_image_width = 400
        text_image = np.zeros((image.shape[0], text_image_width, 3), dtype=np.uint8)
        text_image.fill(255)  # White background

        # Add character labels to text image
        text_image = put_chinese_text(text_image, "Character Labels:", (10, 10), font_path, 24, (0, 0, 0))
        for i, label in enumerate(char_labels[:20]):  # Display first 20 labels
            text_image = put_chinese_text(text_image, label[4], (10, 40 + i*30), font_path, 24, (0, 0, 0))

        # Add text line to text image
        text_image = put_chinese_text(text_image, "Text Line:", (10, 660), font_path, 24, (0, 0, 0))
        for i, line in enumerate(line_labels[:3]):  # Display first 3 lines
            text_image = put_chinese_text(text_image, line[-1], (10, 690 + i*30), font_path, 20, (0, 0, 0))

        # Display both images side by side
        combined_image = np.hstack((image, text_image))

        # Create a resizable window
        cv2.namedWindow(f"Sample: {img_file}", cv2.WINDOW_NORMAL)
        cv2.imshow(f"Sample: {img_file}", combined_image)
        cv2.waitKey(0)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    image_dir = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data/M5HisDoc/M5HisDoc_regular/images"
    char_label_dir = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data/M5HisDoc/M5HisDoc_regular/label_char"
    line_label_dir = "/Users/erniesg/code/erniesg/if-letters-home-could-sing/data/M5HisDoc/M5HisDoc_regular/label_textline"
    font_path = "/System/Library/Fonts/BabelStoneHan.ttf"

    sample_and_display(image_dir, char_label_dir, line_label_dir, font_path)
