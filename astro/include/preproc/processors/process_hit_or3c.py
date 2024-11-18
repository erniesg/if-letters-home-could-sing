import os
import json
import shutil
from tqdm import tqdm
from collections import defaultdict
from preproc.config import PROCESSED_DIR, HIT_OR3C_DIR
from preproc.processors import hit_or3c
from preproc.utils import save_combined_image
from preproc.reporting import generate_summary_stats, print_summary_stats

def load_unified_mappings():
    char_to_id_path = os.path.join(PROCESSED_DIR, 'unified_char_to_id_mapping.json')
    id_to_char_path = os.path.join(PROCESSED_DIR, 'unified_id_to_char_mapping.json')

    with open(char_to_id_path, 'r', encoding='utf-8') as f:
        char_to_id = json.load(f)
    with open(id_to_char_path, 'r', encoding='utf-8') as f:
        id_to_char = json.load(f)

    return char_to_id, id_to_char

def reset_hit_or3c_data(combined_dir, processor):
    # Remove HIT-OR3C files from combined directory
    for root, dirs, files in os.walk(combined_dir):
        for file in files:
            if file.startswith('HIT_OR3C_'):
                os.remove(os.path.join(root, file))

    # Reset the processor
    processor.reset()

    # Remove the progress file
    progress_file = os.path.join(processor.progress_dir, f'{processor.dataset_name}_progress.json')
    if os.path.exists(progress_file):
        os.remove(progress_file)

    print("HIT-OR3C data has been reset.")

def process_hit_or3c():
    combined_dir = os.path.join(PROCESSED_DIR, 'combined')
    os.makedirs(combined_dir, exist_ok=True)

    char_to_id, id_to_char = load_unified_mappings()

    processor = hit_or3c.HitOr3cProcessor()

    # Reset HIT-OR3C data before processing
    reset_hit_or3c_data(combined_dir, processor)

    samples = processor.get_full_dataset()

    total_samples = len(samples)
    char_counts = defaultdict(lambda: defaultdict(int))
    chars_not_in_mapping = set()

    print("\nProcessing HIT-OR3C dataset...")
    with tqdm(total=total_samples, desc="Overall Progress") as overall_pbar:
        for result in processor.process(char_to_id, samples):
            if len(result) == 4:
                char_id, image, dataset_name, filename = result
                save_combined_image(char_id, image, dataset_name, filename, combined_dir)
                char_counts[char_id][dataset_name] += 1
            elif len(result) == 2:
                char, _ = result
                chars_not_in_mapping.add(char)
            overall_pbar.update(1)

    print("\nHIT-OR3C dataset processed successfully.")

    # Generate and print summary stats
    print("\nHIT-OR3C Summary:")
    stats = generate_summary_stats(char_counts, id_to_char)
    print_summary_stats(stats)

    # Print characters not in mapping
    if chars_not_in_mapping:
        print("\nCharacters not in mapping:")
        print(", ".join(chars_not_in_mapping))

    # Print characters not in font
    chars_not_in_font = processor.get_chars_not_in_font()
    if chars_not_in_font:
        print("\nCharacters not in font:")
        print(", ".join(chars_not_in_font))

if __name__ == "__main__":
    process_hit_or3c()
