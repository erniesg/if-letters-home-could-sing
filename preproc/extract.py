import os
import argparse
from tqdm import tqdm
from preproc.config import PROCESSED_DIR, DATA_DIR, FONT_PATH
from preproc.processors.m5hisdoc import M5HisDocProcessor
from preproc.utils import load_char_mappings, validate_extraction, validate_output_structure, count_extracted_images

def process_m5hisdoc(sample_percentage):
    processor = M5HisDocProcessor()
    output_dir = os.path.join(PROCESSED_DIR, 'M5HisDoc')
    os.makedirs(output_dir, exist_ok=True)

    char_to_id_path = os.path.join(DATA_DIR, 'processed', 'unified_char_to_id_mapping.json')
    id_to_char_path = os.path.join(DATA_DIR, 'processed', 'unified_id_to_char_mapping.json')
    char_to_id, id_to_char = load_char_mappings(char_to_id_path, id_to_char_path)

    for char, img, dataset_name in tqdm(processor.process(char_to_id, sample_percentage), desc="Processing M5HisDoc"):
        char_id = char_to_id[char]
        char_dir = os.path.join(output_dir, char_id)
        os.makedirs(char_dir, exist_ok=True)
        img_path = os.path.join(char_dir, f"{dataset_name}_{char}_{len(os.listdir(char_dir))}.png")
        img.save(img_path)

    # Validate extraction
    for txt_file in processor.get_full_dataset():
        label_path = os.path.join(processor.label_char_dir, txt_file)
        extracted_chars = [char for char, _, _ in processor.process(char_to_id, txt_file)]
        if not validate_extraction(extracted_chars, label_path, char_to_id, FONT_PATH):
            print(f"Validation failed for {txt_file}")

    # Validate output structure
    if not validate_output_structure(output_dir, char_to_id, id_to_char):
        print("Output directory structure validation failed")

    # Count extracted images
    char_counts = count_extracted_images(output_dir)
    print("Extracted character counts:", char_counts)

def main():
    parser = argparse.ArgumentParser(description="Extract characters from datasets")
    parser.add_argument("--datasets", nargs="+", choices=["m5hisdoc"], required=True, help="Datasets to process")
    parser.add_argument("--sample", type=float, default=1.0, help="Sample percentage (0.0 to 1.0)")

    args = parser.parse_args()

    for dataset in args.datasets:
        if dataset == "m5hisdoc":
            process_m5hisdoc(args.sample)
        # Add other dataset processing functions as needed

if __name__ == "__main__":
    main()
