import pytest
import torch
from training.config import Config
from training.models.build import build_model

@pytest.fixture
def config():
    return Config()

def test_model_build(config):
    model = build_model(config)
    assert model is not None, "Model build failed"

def test_model_forward_pass(config):
    model = build_model(config)
    dummy_input = torch.randn(1, 3, *config.INPUT_SIZE)
    output = model(dummy_input)
    assert output.shape == (1, config.NUM_CLASSES), "Incorrect output shape"
