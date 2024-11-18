import random

class DatasetHandler:
    def __init__(self, dataset_name, full_dataset):
        self.dataset_name = dataset_name
        self.full_dataset = full_dataset

    def get_deterministic_sample(self, sample_size_or_percentage, seed=42):
        if isinstance(sample_size_or_percentage, float) and 0 < sample_size_or_percentage <= 1:
            sample_size = int(len(self.full_dataset) * sample_size_or_percentage)
        elif isinstance(sample_size_or_percentage, int) and sample_size_or_percentage > 0:
            sample_size = min(sample_size_or_percentage, len(self.full_dataset))
        else:
            raise ValueError("sample_size_or_percentage must be a float between 0 and 1 or a positive integer")

        random.seed(seed)
        return sorted(random.sample(self.full_dataset, sample_size))

    def get_incremental_sample(self, start_size_or_percentage, end_size_or_percentage, seed=42):
        start_sample = self.get_deterministic_sample(start_size_or_percentage, seed)
        end_sample = self.get_deterministic_sample(end_size_or_percentage, seed)
        return sorted(set(end_sample) - set(start_sample))
