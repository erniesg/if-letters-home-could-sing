import pytest
from training.config import Config
from training.data.load import ChineseCharDataset, get_dataloader

@pytest.fixture
def config():
    return Config()

def test_dataset_loading(config):
    dataset = ChineseCharDataset(config)
    assert len(dataset) > 0, "Dataset is empty"

def test_dataloader(config):
    dataloader = get_dataloader(config)
    batch = next(iter(dataloader))
    assert len(batch) == 2, "Batch should contain inputs and labels"
    inputs, labels = batch
    assert inputs.shape == (config.BATCH_SIZE, 3, *config.INPUT_SIZE), "Incorrect input shape"
    assert labels.shape == (config.BATCH_SIZE,), "Incorrect label shape"
