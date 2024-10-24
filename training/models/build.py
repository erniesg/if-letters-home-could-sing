from .cnn import SimpleCNN

def build_model(config):
    return SimpleCNN(num_classes=config.NUM_CLASSES)
