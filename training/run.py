import torch
from training.config import Config
from training.data.load import ChineseCharDataset, get_dataloader
from training.data.transform import get_train_transforms, get_val_transforms
from training.models.build import build_model
from training.train.engine import Trainer
from training.train.logger import init_wandb, log_metrics, finish_wandb
from training.utils.check import check_memory_usage
from training.data.sample import sample_gb2312, get_sample_stats
import logging
logging.getLogger('PIL').setLevel(logging.WARNING)
def main():
    config = Config()
    print(config)

    # Set up data
    train_transform = get_train_transforms(config)
    val_transform = get_val_transforms(config)

    train_dataset = ChineseCharDataset(config, transform=train_transform)
    val_dataset = ChineseCharDataset(config, transform=val_transform)

    # Print full dataset statistics
    print("Full dataset statistics:")
    print(train_dataset.get_stats())

    # Sample GB2312 characters for dry run
    sample_size = 1000  # Adjust as needed
    sampled_dataset = sample_gb2312(train_dataset, sample_size)

    # Print sampled dataset statistics
    print("Sampled dataset statistics:")
    print(get_sample_stats(sampled_dataset))

    train_loader = get_dataloader(config, train_dataset)
    val_loader = get_dataloader(config, val_dataset)
    sampled_loader = get_dataloader(config, sampled_dataset)

    # Update number of classes
    config.update_num_classes(len(set(char_id for _, char_id, _ in sampled_dataset)))

    # Build model
    model = build_model(config)

    # Initialize trainer
    trainer = Trainer(model, config)

    # Check memory usage
    check_memory_usage()

    # Perform dry run
    print("Starting dry run...")
    trainer.dry_run(sampled_loader, num_batches=5)

    try:
        init_wandb(config)
    except Exception as e:
        print(f"Failed to initialize wandb: {str(e)}")
        print("Continuing without wandb logging...")

    # Full training run
    print("Starting full training...")
    for epoch in range(config.NUM_EPOCHS):
        train_loss, train_acc = trainer.train_epoch(train_loader)
        val_loss, val_acc = trainer.validate(val_loader)

        # Log metrics
        log_metrics({
            'epoch': epoch,
            'train_loss': train_loss,
            'train_acc': train_acc,
            'val_loss': val_loss,
            'val_acc': val_acc
        })

        print(f"Epoch {epoch+1}/{config.NUM_EPOCHS}")
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")

    # Finish W&B run
    finish_wandb()

if __name__ == "__main__":
    main()
