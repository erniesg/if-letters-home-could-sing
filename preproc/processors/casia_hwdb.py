import random
from preproc.utils import sample_dataset

def get_full_dataset():
    return list(range(1000))  # This is a placeholder, replace with actual dataset

def process(base_mapping, sample_percentage=1.0):
    full_dataset = get_full_dataset()
    sampled_dataset = sample_dataset(full_dataset, sample_percentage)

    for item in sampled_dataset:
        # Process the item here
        # This is a placeholder, replace with actual processing
        char = chr(random.randint(0x4E00, 0x9FFF))  # Random Chinese character
        yield char, None  # Replace None with actual image data
