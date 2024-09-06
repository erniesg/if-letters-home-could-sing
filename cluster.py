import numpy as np
import pandas as pd
import os
import pickle
from tqdm import tqdm
from PIL import Image as PILImage
import openpyxl
from io import BytesIO
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from tensorboard.plugins import projector
import csv
import time
import torch
import torchvision.models as models
import torchvision.transforms as transforms
import tensorflow as tf
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import math
import shutil
from paddleocr import PaddleOCR
from collections import Counter


import re

def preprocess_text(text):
    # Convert to lowercase
    text = str(text).lower()
    # Remove special characters and extra spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_excluded(material, excluded_materials):
    material_words = set(material.split())
    for excluded in excluded_materials:
        excluded_words = set(excluded.split())
        if excluded_words.issubset(material_words) and len(material_words) == len(excluded_words):
            return True
    return False

def analyze_and_extract_images(xlsx_path, output_dir):
    df = pd.read_excel(xlsx_path)
    workbook = openpyxl.load_workbook(xlsx_path)
    sheet = workbook.active

    embedded_images = list(sheet._images)
    rows_with_images = len(set(img.anchor._from.row for img in embedded_images))

    os.makedirs(output_dir, exist_ok=True)
    extracted_images = []

    for img in embedded_images:
        row = img.anchor._from.row + 1
        accession_no = df.iloc[row - 2]['Accession No.']  # -2 because DataFrame index starts at 0 and we have a header row
        if pd.notna(accession_no):
            image_path = os.path.join(output_dir, f"{accession_no}.png")
            with open(image_path, 'wb') as f:
                f.write(img._data())
            extracted_images.append(accession_no)

    print(f"1. Rows with images analyzed: {rows_with_images}")
    print(f"2. Number of images extracted: {len(extracted_images)}")
    return extracted_images, df

def preprocess_images(input_dir, output_dir, extracted_images, size=(224, 224)):
    os.makedirs(output_dir, exist_ok=True)
    processed_images = []

    for accession_no in extracted_images:
        input_path = os.path.join(input_dir, f"{accession_no}.png")
        output_path = os.path.join(output_dir, f"{accession_no}.jpg")

        if os.path.exists(input_path):
            try:
                with PILImage.open(input_path) as img:
                    img = img.convert('RGB')
                    img = img.resize(size)
                    img.save(output_path, 'JPEG')
                processed_images.append(accession_no)
            except Exception as e:
                print(f"Error processing {accession_no}: {str(e)}")

    print(f"3. Number of images preprocessed into jpg: {len(processed_images)}")
    return processed_images

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")

def detect_languages(image_dir, accession_numbers, batch_size=32):
    print("Detecting languages...")
    languages = []
    language_counter = Counter()

    device = get_device()
    ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=(device != "cpu"))

    for i in tqdm(range(0, len(accession_numbers), batch_size), desc="Detecting languages"):
        batch_accessions = accession_numbers[i:i+batch_size]

        for accession_no in batch_accessions:
            img_path = os.path.join(image_dir, f"{accession_no}.png")

            if os.path.exists(img_path):
                try:
                    language = detect_language(img_path, ocr)
                except Exception as e:
                    print(f"\nError detecting language for {img_path}: {str(e)}")
                    language = 'Unknown'
            else:
                print(f"\nImage not found: {img_path}")
                language = 'Unknown'

            languages.append(language)
            language_counter[language] += 1

        # Print progress every batch
        print(f"\nProcessed {i + len(batch_accessions)} images out of {len(accession_numbers)}")
        print(f"Current language detection summary:")
        print(f"Chinese: {language_counter['Chinese']}")
        print(f"Other: {language_counter['Other']}")
        print(f"Unknown: {language_counter['Unknown']}")

    print("\nFinal language detection summary:")
    print(f"Chinese: {language_counter['Chinese']}")
    print(f"Other: {language_counter['Other']}")
    print(f"Unknown: {language_counter['Unknown']}")

    return languages

def extract_features(image_dir, accession_numbers, n_components=2, batch_size=32):
    images = []
    processed_accession_numbers = []

    print(f"Starting feature extraction for {len(accession_numbers)} images...")

    for i in tqdm(range(0, len(accession_numbers), batch_size), desc="Processing images"):
        batch_accessions = accession_numbers[i:i+batch_size]

        for accession_no in batch_accessions:
            img_path = os.path.join(image_dir, f"{accession_no}.png")

            if os.path.exists(img_path):
                try:
                    img = PILImage.open(img_path).convert('RGB').resize((64, 64))
                    img_array = np.array(img).flatten()
                    images.append(img_array)
                    processed_accession_numbers.append(accession_no)
                except Exception as e:
                    print(f"\nError processing image {img_path}: {str(e)}")
            else:
                print(f"\nImage not found: {img_path}")

    print("Converting images to numpy array...")
    images_array = np.array(images)

    print(f"Performing t-SNE on {images_array.shape[0]} images...")
    tsne = TSNE(n_components=n_components, random_state=42)
    embedded_features = tsne.fit_transform(images_array)

    print(f"\nNumber of features processed: {len(embedded_features)}")
    return embedded_features, processed_accession_numbers

# Main execution
def find_optimal_clusters_elbow(features, max_clusters=20):
    inertias = []
    for k in range(1, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(features)
        inertias.append(kmeans.inertia_)

    plt.plot(range(1, max_clusters + 1), inertias, marker='o')
    plt.xlabel('Number of clusters')
    plt.ylabel('Inertia')
    plt.title('Elbow Method for Optimal k')
    plt.savefig('elbow_plot.png')
    plt.close()

    # You can implement automatic elbow detection here if needed
    print("Elbow plot saved as 'elbow_plot.png'. Please examine it to determine the optimal number of clusters.")
    optimal_clusters = int(input("Enter the optimal number of clusters based on the elbow plot: "))
    return optimal_clusters


def load_and_filter_excel_data(xlsx_path, png_dir, excluded_materials):
    df = pd.read_excel(xlsx_path, dtype={'Material': str})
    valid_accession_numbers = [os.path.splitext(f)[0] for f in os.listdir(png_dir) if f.endswith('.png')]
    df_filtered = df[df['Accession No.'].astype(str).isin(valid_accession_numbers)].copy()

    required_columns = ['Accession No.', 'Artist', 'Object Name', 'Dating', 'Material', 'Dimensions', 'Geo. Association', 'Grade', 'Online label text']
    missing_columns = [col for col in required_columns if col not in df_filtered.columns]
    if missing_columns:
        print(f"Warning: Missing columns in Excel file: {missing_columns}")
        for col in missing_columns:
            df_filtered[col] = 'Unknown'

    df_filtered = df_filtered.dropna(subset=['Accession No.', 'Material'])
    df_filtered['Accession No.'] = df_filtered['Accession No.'].astype(str)

    # Preprocess Material column
    df_filtered['Material_processed'] = df_filtered['Material'].apply(preprocess_text)

    # Preprocess excluded materials
    excluded_materials_processed = [preprocess_text(material) for material in excluded_materials]

    # Filter out excluded materials using the new matching function
    df_filtered = df_filtered[~df_filtered['Material_processed'].apply(
        lambda x: is_excluded(x, excluded_materials_processed)
    )]

    # Remove the temporary column
    df_filtered = df_filtered.drop('Material_processed', axis=1)

    print(f"Total rows in Excel: {len(df)}")
    print(f"Rows with corresponding images and valid materials: {len(df_filtered)}")
    return df_filtered

def tsne_on_images(image_dir, n_components=2):
    png_files = [f for f in os.listdir(image_dir) if f.endswith('.png')]
    images = []
    accession_numbers = []

    for filename in tqdm(png_files, desc="Loading images"):
        accession_no = os.path.splitext(filename)[0]
        img_path = os.path.join(image_dir, filename)
        try:
            img = PILImage.open(img_path).convert('RGB').resize((64, 64))  # Resize to a manageable size
            img_array = np.array(img).flatten()
            images.append(img_array)
            accession_numbers.append(accession_no)
        except Exception as e:
            print(f"\nError loading image {accession_no}: {str(e)}")

    print("Converting images to numpy array...")
    images_array = np.array(images)

    print(f"Performing t-SNE on {images_array.shape[0]} images...")
    tsne = TSNE(n_components=n_components, random_state=42)
    embedded_features = tsne.fit_transform(images_array)

    return embedded_features, accession_numbers

def find_optimal_clusters(features, max_clusters=30):
    silhouette_scores = []
    for n_clusters in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(features)
        silhouette_avg = silhouette_score(features, cluster_labels)
        silhouette_scores.append(silhouette_avg)
        print(f"For n_clusters = {n_clusters}, the average silhouette score is : {silhouette_avg}")

    optimal_clusters = silhouette_scores.index(max(silhouette_scores)) + 2
    return optimal_clusters

def cluster_features(features, n_clusters):
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(features)

    cluster_sizes = np.bincount(cluster_labels)
    print(f"5. Number of clusters created: {n_clusters}")
    print(f"   Average images per cluster: {np.mean(cluster_sizes):.2f}")
    for i, size in enumerate(cluster_sizes):
        print(f"   Cluster {i}: {size} images")

    return cluster_labels

def create_sprite_image(image_dir, accession_numbers, output_file, image_size=(64, 64)):
    """
    Create a sprite image from a list of image files.
    """
    images = []
    for accession_no in accession_numbers:
        img_path = os.path.join(image_dir, f"{accession_no}.png")
        if os.path.exists(img_path):
            img = PILImage.open(img_path).convert("RGB").resize(image_size)
            images.append(img)
        else:
            print(f"Image not found for accession number: {accession_no}")
            images.append(PILImage.new("RGB", image_size, color=(255, 255, 255)))

    sprite_size = int(math.ceil(math.sqrt(len(images))))

    sprite_image = PILImage.new(
        mode='RGB',
        size=(image_size[0] * sprite_size, image_size[1] * sprite_size),
        color=(255, 255, 255)  # White background
    )

    for i, img in enumerate(images):
        row = i // sprite_size
        col = i % sprite_size
        sprite_image.paste(
            img,
            (col * image_size[0], row * image_size[1])
        )

    sprite_image.save(output_file)
    return sprite_size

def create_sprite_image_per_cluster(image_dir, accession_numbers, cluster_labels, output_dir, image_size=(64, 64)):
    """
    Create a sprite image for each cluster.
    """
    os.makedirs(output_dir, exist_ok=True)

    unique_clusters = np.unique(cluster_labels)

    for cluster in unique_clusters:
        cluster_accessions = [acc for acc, label in zip(accession_numbers, cluster_labels) if label == cluster]

        images = []
        for accession_no in cluster_accessions:
            img_path = os.path.join(image_dir, f"{accession_no}.png")
            if os.path.exists(img_path):
                img = PILImage.open(img_path).convert("RGB").resize(image_size)
                images.append(img)
            else:
                print(f"Image not found for accession number: {accession_no}")
                images.append(PILImage.new("RGB", image_size, color=(255, 255, 255)))

        sprite_size = int(math.ceil(math.sqrt(len(images))))

        sprite_image = PILImage.new(
            mode='RGB',
            size=(image_size[0] * sprite_size, image_size[1] * sprite_size),
            color=(255, 255, 255)  # White background
        )

        for i, img in enumerate(images):
            row = i // sprite_size
            col = i % sprite_size
            sprite_image.paste(
                img,
                (col * image_size[0], row * image_size[1])
            )

        output_file = os.path.join(output_dir, f'sprite_cluster_{cluster}.png')
        sprite_image.save(output_file)
        print(f"Sprite image for cluster {cluster} saved as {output_file}")

def prepare_tensorboard(features, metadata, log_dir, selected_columns, image_dir, accession_numbers, languages):
    os.makedirs(log_dir, exist_ok=True)

    # Ensure metadata and features are in the same order
    metadata_filtered = metadata[metadata['Accession No.'].astype(str).isin(accession_numbers)].copy()
    metadata_filtered = metadata_filtered.set_index('Accession No.').loc[accession_numbers].reset_index()

    metadata_for_tensorboard = metadata_filtered[selected_columns].copy()
    metadata_for_tensorboard['Language'] = languages

    # Function to clean and escape field values
    def clean_field(value):
        if isinstance(value, str):
            # Replace newlines with space and escape any remaining tabs
            return value.replace('\n', ' ').replace('\r', '').replace('\t', '\\t')
        return value

    # Apply the cleaning function to all fields
    metadata_for_tensorboard = metadata_for_tensorboard.map(clean_field)

    metadata_path = os.path.join(log_dir, 'metadata.tsv')
    metadata_for_tensorboard.to_csv(metadata_path, sep='\t', index=False, quoting=csv.QUOTE_NONE, escapechar='\\')

    features_tensor = tf.Variable(features)
    checkpoint = tf.train.Checkpoint(embedding=features_tensor)
    checkpoint.save(os.path.join(log_dir, "embedding.ckpt"))

    config = projector.ProjectorConfig()
    embedding = config.embeddings.add()
    embedding.tensor_name = "embedding/.ATTRIBUTES/VARIABLE_VALUE"
    embedding.metadata_path = 'metadata.tsv'

    # Create and set up sprite image
    sprite_file = os.path.join(log_dir, 'sprite.png')
    sprite_size = create_sprite_image(image_dir, accession_numbers, sprite_file)

    embedding.sprite.image_path = 'sprite.png'
    embedding.sprite.single_image_dim.extend([64, 64])  # Adjust if your image size is different

    projector.visualize_embeddings(log_dir, config)

    print(f"TensorBoard data prepared and saved to {log_dir}")
    print(f"Metadata file created: {metadata_path}")
    print(f"Sprite image created: {sprite_file}")
    print(f"Number of data points: {len(features)}")
    print(f"Feature dimensionality: {features.shape[1]}")
    print(f"Metadata columns: {', '.join(metadata_for_tensorboard.columns)}")
    return metadata_for_tensorboard




# Main execution
xlsx_path = './data/collection.xlsx'
png_dir = './data/images_png'
log_dir = './logs'
feature_file = './data/features.pkl'

# Flag to control which steps to run
run_steps = {
    'extract_images': False,
    'extract_features': True,
    'detect_languages': False,
    'cluster_and_visualize': True
}

# List of excluded materials
excluded_materials = [
    "acrylic, metal",
    "albumen paper on card mount albumen paper paper (fiber product) ink",
    "aluminium (metal) polymers paper (fiber product) ink",
    "archival pigment printed on archival paper acid-free paper pigment",
    "brass (alloy)",
    "ceramic ceramic (material) colour (pigment) ceramic glaze",
    "copper (metal)",
    "digital file [nhb]",
    "fabric (nylon) nylon",
    "gelatin prints photographic gelatin silver gelatin paper",
    "ink",
    "leather leather",
    "leather, paper ink leather paper (fiber product)",
    "marble, metal",
    "metal",
    "metal stainless steel",
    "metal and nylon metal nylon",
    "metal and wood",
    "paper paper fiber product",
    "pewter (tin alloy)",
    "photograph photographic paper ink",
    "photographic paper",
    "photographic paper ink",
    "photographic paper ink colour (pigment)",
    "plastic, paper plastic (material) vinyl paper (fiber product) ink",
    "silver silver (metal) oak (wood) metal cloth",
    "vinyl paper (fiber product)",
    "wood",
    "wood wood (plant material) cloth",
    "wood, metal"
]

# Load and filter Excel data
print("\nLoading and filtering Excel data...")
df_filtered = load_and_filter_excel_data(xlsx_path, png_dir, excluded_materials)
valid_accession_numbers = df_filtered['Accession No.'].tolist()

# Step 3: Extract features using t-SNE
if run_steps['extract_features']:
    print("\nStep 3: Extracting features using t-SNE...")
    features, accession_numbers = extract_features(png_dir, valid_accession_numbers, n_components=2)
    print("Saving extracted features...")
    with open(feature_file, 'wb') as f:
        pickle.dump((features, accession_numbers), f)
    print("Features saved successfully.")
else:
    print("\nLoading pre-extracted features...")
    with open(feature_file, 'rb') as f:
        features, accession_numbers = pickle.load(f)
    print(f"Loaded {len(features)} pre-extracted features.")

# Step 4: Detect languages (optional)
if run_steps['detect_languages']:
    print("\nStep 4: Detecting languages...")
    languages = detect_languages(png_dir, accession_numbers)
    print("Saving language detection results...")
    with open('./data/languages.pkl', 'wb') as f:
        pickle.dump(languages, f)
    print("Language detection results saved successfully.")
else:
    print("\nSkipping language detection.")
    languages = ['Unknown'] * len(accession_numbers)

# Step 5 & 6: Cluster and visualize
if run_steps['cluster_and_visualize']:
    print("\nFinding optimal number of clusters...")
    optimal_clusters = find_optimal_clusters(features)
    print(f"Optimal number of clusters: {optimal_clusters}")

    print("\nStep 5: Clustering features...")
    cluster_labels = cluster_features(features, optimal_clusters)

    print("\nCreating sprite images for each cluster...")
    create_sprite_image_per_cluster(png_dir, accession_numbers, cluster_labels, './data/cluster_sprites')

    print("\nStep 6: Preparing data for TensorBoard...")
    df_processed = df_filtered[df_filtered['Accession No.'].astype(str).isin(accession_numbers)].copy()
    df_processed['cluster_id'] = cluster_labels

    selected_columns = ['Accession No.', 'Artist', 'Object Name', 'Dating', 'Material', 'Dimensions', 'Geo. Association', 'Grade', 'Online label text', 'cluster_id']
    metadata_for_tensorboard = prepare_tensorboard(features, df_processed, log_dir, selected_columns, png_dir, accession_numbers, languages)

# Print summary
print(f"\nProcessing complete.")
print(f"Total rows in Excel: {len(df_filtered)}")
print(f"Features extracted: {len(features)}")
print(f"Rows with corresponding images: {len(df_processed)}")
print(f"Number of clusters: {optimal_clusters}")
print(f"Average images per cluster: {np.mean(np.bincount(cluster_labels)):.2f}")
print(f"Rows in metadata for TensorBoard: {len(metadata_for_tensorboard)}")
print("Run 'tensorboard --logdir=./logs' to view the results.")
