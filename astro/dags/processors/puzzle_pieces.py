import os
from PIL import Image
from airflow.hooks.S3_hook import S3Hook

class PuzzlePiecesProcessor:
    def __init__(self, temp_dir):
        self.dataset_dir = os.path.join(temp_dir, 'Dataset')
        self.dataset_name = 'puzzle_pieces'
        self.s3_hook = S3Hook(aws_conn_id='aws_default')

    def get_full_dataset(self):
        return [f for f in os.listdir(self.dataset_dir)
                if os.path.isdir(os.path.join(self.dataset_dir, f))]

    def process(self, samples, s3_output_base):
        """Process samples and upload to S3 - ID folders already correct"""
        processed_count = 0
        errors = []

        for folder_id in samples:
            folder_path = os.path.join(self.dataset_dir, folder_id)
            images = [f for f in os.listdir(folder_path)
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

            for img_file in images:
                img_path = os.path.join(folder_path, img_file)
                try:
                    # Direct upload to S3 with correct name format
                    s3_key = f"{folder_id}/{self.dataset_name}_{folder_id}_{processed_count}.png"
                    bucket = s3_output_base.split('/')[2]
                    key = f"{'/'.join(s3_output_base.split('/')[3:])}/{s3_key}"

                    self.s3_hook.load_file(
                        filename=img_path,
                        key=key,
                        bucket_name=bucket,
                        replace=True
                    )

                    processed_count += 1
                    yield {
                        'folder_id': folder_id,
                        'status': 'success',
                        's3_key': s3_key,
                        'count': processed_count
                    }

                except Exception as e:
                    errors.append(f"Error processing {img_path}: {str(e)}")
                    continue

        if errors:
            print("\nProcessing Errors:")
            for error in errors:
                print(error)

        print(f"\nTotal images processed: {processed_count}")
