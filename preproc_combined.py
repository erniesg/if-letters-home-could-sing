import os
import json
import logging
import csv
from PIL import Image, ImageFont
from collections import defaultdict
import numpy as np
from tqdm import tqdm
import multiprocessing
from functools import partial
import pandas as pd
import struct
import lmdb
import io

# Constants
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(PROJECT_DIR, 'data', 'fonts', 'BabelStoneHan.ttf')
CHINESE_TO_ID_PATH = os.path.join(PROJECT_DIR, 'data', 'Puzzle-Pieces-Picker Dataset', 'Chinese_to_ID.json')
PUZZLE_PIECES_DIR = os.path.join(PROJECT_DIR, 'data', 'Puzzle-Pieces-Picker Dataset', 'Dataset')
M5HISDOC_DIR = os.path.join(PROJECT_DIR, 'data', 'M5HisDoc', 'M5HisDoc_regular')
CASIA_HWDB_DIR = os.path.join(PROJECT_DIR, 'data', 'CASIA-HWDB')
COMBINED_DIR = os.path.join(PROJECT_DIR, 'data', 'combined')
CHARACTERS_LMDB_PATH = os.path.join(COMBINED_DIR, 'characters.lmdb')
COMBINED_CHAR_SET_PATH = os.path.join(COMBINED_DIR, 'combined_char_set.json')
LOGS_DIR = os.path.join(PROJECT_DIR, 'logs')
PROGRESS_CSV_PATH = os.path.join(LOGS_DIR, 'char_progress.csv')
ERROR_CSV_PATH = os.path.join(LOGS_DIR, 'char_errors.csv')

BATCH_SIZE = 100
NUM_WORKERS = multiprocessing.cpu_count()
LMDB_MAP_SIZE = 100 * 1024 * 1024 * 1024  # 100GB

# Set up logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_lmdb():
    os.makedirs(COMBINED_DIR, exist_ok=True)
    return lmdb.open(CHARACTERS_LMDB_PATH, map_size=LMDB_MAP_SIZE)

CHARACTERS_ENV = initialize_lmdb()

def load_json(file_path):
    logging.info(f"Loading JSON from {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, file_path):
    logging.info(f"Saving JSON to {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_char_in_font(char, font):
    try:
        font.getmask(char)
        return True
    except:
        return False

def filter_characters(char_mapping, font):
    logging.info("Filtering characters based on font availability")
    filtered_mapping = {}
    error_chars = []

    for char, id in tqdm(char_mapping.items(), desc="Filtering characters"):
        if is_char_in_font(char, font):
            filtered_mapping[char] = id
        else:
            error_chars.append(('Puzzle Pieces', id, f'Character not in font: {char}'))

    logging.info(f"Ignored {len(error_chars)} characters from Puzzle Pieces Picker")
    return filtered_mapping, error_chars

def process_batch(batch, process_func, extra_args):
    return [process_func(item, *extra_args) for item in batch]

def process_in_batches(items, process_func, num_workers, batch_size, desc, *args):
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    with multiprocessing.Pool(num_workers) as pool:
        results = list(tqdm(
            pool.imap(partial(process_batch, process_func=process_func, extra_args=args), batches),
            total=len(batches),
            desc=desc
        ))
    return [item for sublist in results for item in sublist if item is not None]

def append_row(df, new_row):
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

def initialize_progress_and_errors():
    progress_df = pd.DataFrame(columns=['iterable', 'source', 'status'])
    errors_df = pd.DataFrame(columns=['iterable', 'source', 'error'])

    # Initialize Puzzle Pieces
    for char_id in os.listdir(PUZZLE_PIECES_DIR):
        progress_df = append_row(progress_df, {'iterable': char_id, 'source': 'Puzzle Pieces', 'status': 0})

    # Initialize M5HisDoc
    label_char_dir = os.path.join(M5HISDOC_DIR, 'label_char')
    for txt_file in os.listdir(label_char_dir):
        if txt_file.endswith('.txt'):
            progress_df = append_row(progress_df, {'iterable': txt_file, 'source': 'M5HisDoc', 'status': 0})

    # Initialize CASIA-HWDB
    for root, _, files in os.walk(CASIA_HWDB_DIR):
        for file in files:
            if file.endswith('.gnt'):
                progress_df = append_row(progress_df, {'iterable': file, 'source': 'CASIA-HWDB', 'status': 0})

    progress_df.set_index('iterable', inplace=True)
    return progress_df, errors_df

def load_or_initialize_progress_and_errors():
    if os.path.exists(PROGRESS_CSV_PATH) and os.path.exists(ERROR_CSV_PATH):
        progress_df = pd.read_csv(PROGRESS_CSV_PATH, index_col='iterable')
        errors_df = pd.read_csv(ERROR_CSV_PATH)
    else:
        progress_df, errors_df = initialize_progress_and_errors()
        save_progress_and_errors(progress_df, errors_df)
    return progress_df, errors_df

def save_progress_and_errors(progress_df, errors_df):
    progress_df.to_csv(PROGRESS_CSV_PATH)
    errors_df.to_csv(ERROR_CSV_PATH, index=False)

def generate_new_id(used_ids):
    new_id = max(int(id) for id in used_ids) + 1
    while f"{new_id:05d}" in used_ids:
        new_id += 1
    new_id = f"{new_id:05d}"
    used_ids.add(new_id)
    return new_id, used_ids

def save_image_to_lmdb(env, key, image):
    with env.begin(write=True) as txn:
        bio = io.BytesIO()
        image.save(bio, format='PNG')
        txn.put(key.encode(), bio.getvalue())

def process_puzzle_piece(char_item, progress_df, errors_df, used_ids):
    char, char_id = char_item
    src_dir = os.path.join(PUZZLE_PIECES_DIR, char_id)

    if not os.path.exists(src_dir):
        errors_df = append_row(errors_df, {'iterable': char_id, 'source': 'Puzzle Pieces', 'error': 'Source directory not found'})
        return char, 0, used_ids, errors_df

    count = 0
    for img_file in os.listdir(src_dir):
        with Image.open(os.path.join(src_dir, img_file)) as img:
            key = f"{char_id}_puzzle_{count}"
            save_image_to_lmdb(CHARACTERS_ENV, key, img)
            count += 1

    progress_df.loc[char_id, 'status'] = 1
    return char, count, used_ids, errors_df

def process_m5hisdoc_file(txt_file, char_mapping, font, progress_df, errors_df, used_ids):
    img_file = txt_file.replace('.txt', '.jpg')
    img_path = os.path.join(M5HISDOC_DIR, 'images', img_file)

    if not os.path.exists(img_path):
        errors_df = append_row(errors_df, {'iterable': txt_file, 'source': 'M5HisDoc', 'error': 'Image file not found'})
        return None, used_ids, errors_df

    file_char_mapping = {}
    file_char_count = defaultdict(int)

    try:
        with Image.open(img_path) as img:
            if img.mode == 'CMYK':
                img = img.convert('RGB')

            with open(os.path.join(M5HISDOC_DIR, 'label_char', txt_file), 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parts = line.strip().split(',')
                    if len(parts) == 5:
                        try:
                            x1, y1, x2, y2, char = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
                        except ValueError:
                            errors_df = append_row(errors_df, {'iterable': txt_file, 'source': 'M5HisDoc', 'error': f'Invalid format: {line.strip()}'})
                            continue

                        if not is_char_in_font(char, font):
                            errors_df = append_row(errors_df, {'iterable': txt_file, 'source': 'M5HisDoc', 'error': f'Character not in font: {char}'})
                            continue

                        if char not in char_mapping:
                            char_id, used_ids = generate_new_id(used_ids)
                            file_char_mapping[char] = char_id
                        else:
                            char_id = char_mapping[char]

                        char_img = img.crop((x1, y1, x2, y2))
                        key = f"{char_id}_m5hisdoc_{txt_file}_{x1}_{y1}"
                        save_image_to_lmdb(CHARACTERS_ENV, key, char_img)
                        file_char_count[char] += 1
                    else:
                        errors_df = append_row(errors_df, {'iterable': txt_file, 'source': 'M5HisDoc', 'error': f'Unexpected format: {line.strip()}'})
    except Exception as e:
        errors_df = append_row(errors_df, {'iterable': txt_file, 'source': 'M5HisDoc', 'error': f'Error processing file: {str(e)}'})

    progress_df.loc[txt_file, 'status'] = 1
    return file_char_mapping, file_char_count, used_ids, errors_df

def process_casia_hwdb(file_path, char_mapping, font, progress_df, errors_df, used_ids):
    file_char_mapping = {}
    file_char_count = defaultdict(int)

    try:
        with open(file_path, 'rb') as f:
            while True:
                sample_size = f.read(4)
                if not sample_size:
                    break
                sample_size = struct.unpack('I', sample_size)[0]

                tag_code = f.read(2)
                width, height = struct.unpack('HH', f.read(4))

                bitmap = f.read(width * height)

                char = tag_code.decode('gb2312', errors='ignore')

                if not is_char_in_font(char, font):
                    errors_df = append_row(errors_df, {'iterable': os.path.basename(file_path), 'source': 'CASIA-HWDB', 'error': f'Character not in font: {char}'})
                    continue

                if char not in char_mapping:
                    char_id, used_ids = generate_new_id(used_ids)
                    file_char_mapping[char] = char_id
                else:
                    char_id = char_mapping[char]

                img = Image.frombytes('L', (width, height), bitmap)
                key = f"{char_id}_casia_hwdb_{os.path.basename(file_path)}_{file_char_count[char]}"
                save_image_to_lmdb(CHARACTERS_ENV, key, img)

                file_char_count[char] += 1

        progress_df.loc[os.path.basename(file_path), 'status'] = 1

    except Exception as e:
        errors_df = append_row(errors_df, {'iterable': os.path.basename(file_path), 'source': 'CASIA-HWDB', 'error': f'Error processing file: {str(e)}'})

    return file_char_mapping, file_char_count, used_ids, errors_df

def process_datasets(initial_char_mapping, font):
    progress_df, errors_df = load_or_initialize_progress_and_errors()
    used_ids = set(initial_char_mapping.values())

    # Process Puzzle Pieces dataset
    logging.info("Processing Puzzle Pieces dataset")
    puzzle_pieces_items = [(char, id) for char, id in initial_char_mapping.items()
                           if id in progress_df.index and progress_df.loc[id, 'status'] == 0]

    if puzzle_pieces_items:
        puzzle_results = process_in_batches(puzzle_pieces_items, process_puzzle_piece, NUM_WORKERS, BATCH_SIZE, "Copying Puzzle Pieces", progress_df, errors_df, used_ids)
        puzzle_char_count = {char: count for char, count, _, _ in puzzle_results}
        used_ids = set.union(*[ids for _, _, ids, _ in puzzle_results])
        errors_df = pd.concat([errors_df] + [err_df for _, _, _, err_df in puzzle_results])
    else:
        logging.info("All Puzzle Pieces already processed. Skipping.")
        puzzle_char_count = {}

    # Process M5HisDoc dataset
    logging.info("Processing M5HisDoc dataset")
    label_char_dir = os.path.join(M5HISDOC_DIR, 'label_char')
    txt_files = [f for f in os.listdir(label_char_dir) if f.endswith('.txt')
                 and f in progress_df.index and progress_df.loc[f, 'status'] == 0]

    if txt_files:
        m5hisdoc_results = process_in_batches(txt_files, process_m5hisdoc_file, NUM_WORKERS, BATCH_SIZE, "Processing M5HisDoc files", initial_char_mapping, font, progress_df, errors_df, used_ids)
        m5hisdoc_char_mapping = {}
        m5hisdoc_char_count = defaultdict(int)
        for result in m5hisdoc_results:
            if result:
                file_char_mapping, file_char_count, used_ids, errors_df = result
                m5hisdoc_char_mapping.update(file_char_mapping)
                for char, count in file_char_count.items():
                        m5hisdoc_char_count[char] += count
    else:
        logging.info("All M5HisDoc files already processed. Skipping.")
        m5hisdoc_char_mapping = {}
        m5hisdoc_char_count = defaultdict(int)

    # Process CASIA-HWDB dataset
    logging.info("Processing CASIA-HWDB dataset")
    gnt_files = [os.path.join(root, f) for root, _, files in os.walk(CASIA_HWDB_DIR) for f in files if f.endswith('.gnt')
                 and f in progress_df.index and progress_df.loc[f, 'status'] == 0]

    if gnt_files:
        casia_hwdb_results = process_in_batches(gnt_files, process_casia_hwdb, NUM_WORKERS, BATCH_SIZE, "Processing CASIA-HWDB files", initial_char_mapping, font, progress_df, errors_df, used_ids)
        casia_hwdb_char_mapping = {}
        casia_hwdb_char_count = defaultdict(int)
        for result in casia_hwdb_results:
            if result:
                file_char_mapping, file_char_count, used_ids, errors_df = result
                casia_hwdb_char_mapping.update(file_char_mapping)
                for char, count in file_char_count.items():
                    casia_hwdb_char_count[char] += count
    else:
        logging.info("All CASIA-HWDB files already processed. Skipping.")
        casia_hwdb_char_mapping = {}
        casia_hwdb_char_count = defaultdict(int)

    # Combine results
    updated_char_mapping = initial_char_mapping.copy()
    updated_char_mapping.update(m5hisdoc_char_mapping)
    updated_char_mapping.update(casia_hwdb_char_mapping)

    new_chars_from_m5hisdoc = set(m5hisdoc_char_mapping.keys()) - set(initial_char_mapping.keys())
    new_chars_from_casia_hwdb = set(casia_hwdb_char_mapping.keys()) - set(initial_char_mapping.keys())

    # Save progress and errors
    save_progress_and_errors(progress_df, errors_df)

    return updated_char_mapping, puzzle_char_count, m5hisdoc_char_count, casia_hwdb_char_count, new_chars_from_m5hisdoc, new_chars_from_casia_hwdb, used_ids

def analyze_dataset():
    logging.info("Analyzing combined dataset")
    class_counts = defaultdict(lambda: {'total': 0, 'puzzle': 0, 'm5hisdoc': 0, 'casia_hwdb': 0})

    with CHARACTERS_ENV.begin() as txn:
        cursor = txn.cursor()
        for key, _ in cursor:
            key = key.decode()
            class_id, source, _ = key.split('_', 2)
            class_counts[class_id]['total'] += 1
            class_counts[class_id][source] += 1

    num_classes = len(class_counts)
    samples_per_class = [count['total'] for count in class_counts.values()]
    avg_samples = np.mean(samples_per_class)
    min_samples = np.min(samples_per_class)
    max_samples = np.max(samples_per_class)
    total_puzzle = sum(count['puzzle'] for count in class_counts.values())
    total_m5hisdoc = sum(count['m5hisdoc'] for count in class_counts.values())
    total_casia_hwdb = sum(count['casia_hwdb'] for count in class_counts.values())

    logging.info(f"Number of classes: {num_classes}")
    logging.info(f"Average samples per class: {avg_samples:.2f}")
    logging.info(f"Minimum samples in a class: {min_samples}")
    logging.info(f"Maximum samples in a class: {max_samples}")
    logging.info(f"Total samples from Puzzle Pieces Picker: {total_puzzle}")
    logging.info(f"Total samples from M5HisDoc: {total_m5hisdoc}")
    logging.info(f"Total samples from CASIA-HWDB: {total_casia_hwdb}")

    # Print top 10 and bottom 10 most common characters
    sorted_classes = sorted(class_counts.items(), key=lambda x: x[1]['total'], reverse=True)

    logging.info("Top 10 most common characters:")
    for class_id, counts in sorted_classes[:10]:
        logging.info(f"{class_id}: {counts['total']}")

    logging.info("Bottom 10 least common characters:")
    for class_id, counts in sorted_classes[-10:]:
        logging.info(f"{class_id}: {counts['total']}")

def identify_duplicates(char_mapping):
    char_count = defaultdict(list)
    id_count = defaultdict(list)

    for char, id in char_mapping.items():
        char_count[char].append(id)
        id_count[id].append(char)

    duplicate_chars = {char: ids for char, ids in char_count.items() if len(ids) > 1}
    duplicate_ids = {id: chars for id, chars in id_count.items() if len(chars) > 1}

    if duplicate_chars:
        logging.error("Duplicate characters found in the mapping:")
        for char, ids in duplicate_chars.items():
            logging.error(f"Character '{char}' has multiple IDs: {', '.join(ids)}")

    if duplicate_ids:
        logging.error("Duplicate IDs found in the mapping:")
        for id, chars in duplicate_ids.items():
            logging.error(f"ID '{id}' is assigned to multiple characters: {', '.join(chars)}")

    return duplicate_chars, duplicate_ids

def main():
    logging.info("Starting preprocessing of combined dataset")

    # Load the font
    font = ImageFont.truetype(FONT_PATH, size=12)

    # Load and filter the initial character mapping
    initial_mapping = load_json(CHINESE_TO_ID_PATH)
    logging.info(f"Loaded {len(initial_mapping)} characters from initial mapping")

    filtered_mapping, _ = filter_characters(initial_mapping, font)
    logging.info(f"Filtered mapping contains {len(filtered_mapping)} characters")

    try:
        # Process datasets
        updated_mapping, puzzle_char_count, m5hisdoc_char_count, casia_hwdb_char_count, new_chars_m5hisdoc, new_chars_casia_hwdb, used_ids = process_datasets(filtered_mapping, font)

        # Identify duplicates
        duplicate_chars, duplicate_ids = identify_duplicates(updated_mapping)

        if duplicate_chars or duplicate_ids:
            logging.error("Duplicates found in the mapping. Please review the results above.")

            # Optionally, save the duplicates to a file for further analysis
            duplicates_file = os.path.join(LOGS_DIR, 'duplicate_mappings.json')
            with open(duplicates_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'duplicate_characters': {str(k): v for k, v in duplicate_chars.items()},
                    'duplicate_ids': duplicate_ids
                }, f, ensure_ascii=False, indent=2)
            logging.info(f"Saved duplicate mappings to {duplicates_file}")
        else:
            logging.info("No duplicates found in the character mapping.")

        # Save the updated character mapping
        save_json(updated_mapping, COMBINED_CHAR_SET_PATH)

        # Save new characters introduced by M5HisDoc and CASIA-HWDB
        new_chars_file = os.path.join(LOGS_DIR, 'new_chars.txt')
        with open(new_chars_file, 'w', encoding='utf-8') as f:
            f.write("New characters from M5HisDoc:\n")
            for char in sorted(new_chars_m5hisdoc):
                f.write(f"{char}\n")
            f.write("\nNew characters from CASIA-HWDB:\n")
            for char in sorted(new_chars_casia_hwdb):
                f.write(f"{char}\n")
        logging.info(f"Saved {len(new_chars_m5hisdoc)} new characters from M5HisDoc and {len(new_chars_casia_hwdb)} new characters from CASIA-HWDB to {new_chars_file}")

        # Analyze the combined dataset
        analyze_dataset()

        logging.info("Preprocessing completed successfully")
    finally:
        CHARACTERS_ENV.close()

if __name__ == "__main__":
    main()
