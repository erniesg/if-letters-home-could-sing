import os
import json
from tqdm import tqdm
from collections import defaultdict
from preproc.config import PROCESSED_DIR
from preproc.processors import m5hisdoc, casia_hwdb, hit_or3c
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

def process_dataset(processor, samples, char_to_id, combined_dir, overall_pbar):
    char_counts = defaultdict(lambda: defaultdict(int))
    chars_not_in_mapping = set()

    # Special case for PuzzlePiecesPicker
    if isinstance(processor, puzzle_pieces_picker.PuzzlePiecesPicker):
        process_method = lambda samples: processor.process(samples)
    else:
        process_method = lambda samples: processor.process(char_to_id, samples)

    for result in process_method(samples):
        if len(result) == 4:
            char_id, image, dataset_name, filename = result
            save_combined_image(char_id, image, dataset_name, filename, combined_dir)
            char_counts[char_id][dataset_name] += 1
        elif len(result) == 2:
            char, _ = result
            chars_not_in_mapping.add(char)
        overall_pbar.update(1)

    return char_counts, chars_not_in_mapping

def process_all():
    combined_dir = os.path.join(PROCESSED_DIR, 'combined')
    os.makedirs(combined_dir, exist_ok=True)

    char_to_id, id_to_char = load_unified_mappings()

    # Get total samples for all datasets
    total_samples = (
        len(puzzle_pieces_picker.get_full_dataset()) +
        len(m5hisdoc.get_full_dataset()) +
        len(casia_hwdb.get_full_dataset()) +
        len(hit_or3c.get_full_dataset())
    )

    all_char_counts = defaultdict(lambda: defaultdict(int))
    all_chars_not_in_mapping = set()

    # Create overall progress bar
    with tqdm(total=total_samples, desc="Overall Progress") as overall_pbar:
        # Process PuzzlePiecesPicker
        print("\nProcessing PuzzlePiecesPicker dataset...")
        processor = puzzle_pieces_picker.PuzzlePiecesPicker()
        samples = processor.get_full_dataset()
        ppp_char_counts, _ = process_dataset(processor, samples, None, combined_dir, overall_pbar)

        # Process M5HisDoc
        print("\nProcessing M5HisDoc dataset...")
        processor = m5hisdoc.M5HisDocProcessor()
        samples = processor.get_full_dataset()
        m5_char_counts, m5_chars_not_in_mapping = process_dataset(processor, samples, char_to_id, combined_dir, overall_pbar)

        # Process CASIA-HWDB
        print("\nProcessing CASIA-HWDB dataset...")
        processor = casia_hwdb.CasiaHwdbProcessor()
        samples = processor.get_full_dataset()
        casia_char_counts, casia_chars_not_in_mapping = process_dataset(processor, samples, char_to_id, combined_dir, overall_pbar)

        # Process HIT-OR3C
        print("\nProcessing HIT-OR3C dataset...")
        processor = hit_or3c.HitOr3cProcessor()
        samples = processor.get_full_dataset()
        hit_char_counts, hit_chars_not_in_mapping = process_dataset(processor, samples, char_to_id, combined_dir, overall_pbar)

    print("\nAll datasets processed and combined successfully.")

    # Merge all char counts
    for char_counts in [ppp_char_counts, m5_char_counts, casia_char_counts, hit_char_counts]:
        for char_id, dataset_counts in char_counts.items():
            for dataset, count in dataset_counts.items():
                all_char_counts[char_id][dataset] += count

    all_chars_not_in_mapping.update(m5_chars_not_in_mapping, casia_chars_not_in_mapping, hit_chars_not_in_mapping)

    # Generate and print summary stats for each dataset
    datasets = [
        ("PuzzlePiecesPicker", ppp_char_counts),
        ("M5HisDoc", m5_char_counts),
        ("CASIA-HWDB", casia_char_counts),
        ("HIT-OR3C", hit_char_counts)
    ]

    for dataset_name, char_counts in datasets:
        print(f"\n{dataset_name} Summary:")
        stats = generate_summary_stats(char_counts, id_to_char)
        print_summary_stats(stats)

    # Generate and print overall summary stats
    print("\nOverall Summary:")
    overall_stats = generate_summary_stats(all_char_counts, id_to_char, all_chars_not_in_mapping)
    print_summary_stats(overall_stats)

if __name__ == "__main__":
    process_all()
