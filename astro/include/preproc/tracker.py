import json
import os

class ProgressTracker:
    def __init__(self, dataset_name, progress_dir):
        self.dataset_name = dataset_name
        self.progress_dir = progress_dir
        self.progress_file = os.path.join(self.progress_dir, f'{self.dataset_name}_progress.json')
        self.progress = self.load_progress()
        self.total_images = 0
        self.total_samples = 0
        self.processed_samples = 0

    def initialize_progress(self, samples):
        for sample in samples:
            if sample not in self.progress:
                self.progress[sample] = {'status': 'Not Started'}
        self.save_progress()

    def update_progress(self, sample, status):
        if sample not in self.progress:
            self.progress[sample] = {'status': 'Not Started'}
        self.progress[sample]['status'] = status
        self.save_progress()

    def save_progress(self):
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f)

    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}

    def is_sample_processed(self, sample):
        return self.progress.get(sample, {}).get('status') == 'Completed'

    def get_unprocessed_samples(self, samples):
        return [sample for sample in samples if not self.is_sample_processed(sample)]

    def set_total_samples(self, total):
        self.total_samples = total

    def increment_processed(self):
        self.processed_samples += 1

    def get_progress(self):
        return self.processed_samples, self.total_samples
