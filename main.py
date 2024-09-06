from helpers.config import load_config
from operators.download import DownloadOperator
from operators.unzip import UnzipOperator
from operators.preproc import PreprocessOperator

def main():
    config = load_config()
    s3_config = config['s3']
    datasets = config['datasets']
    processing_config = config['processing']

    # Rest of the main function remains the same
    ...

if __name__ == "__main__":
    main()
