import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm
import matplotlib.pyplot as plt
from preproc_train import get_dataloaders
from model import SimpleCNN
from wandb_utils import init_wandb, log_metrics, log_model, log_image_table, log_confusion_matrix, finish_run
import os
import matplotlib.font_manager as fm
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import wandb

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")

def train(model, train_loader, criterion, optimizer, device, epoch):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1} Training")
    for batch_idx, (inputs, labels) in enumerate(progress_bar):
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs, _ = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
        progress_bar.set_postfix({'loss': running_loss / (batch_idx + 1), 'acc': correct / total})

        # Log metrics to wandb
        log_metrics({
            "train/loss": loss.item(),
            "train/accuracy": correct / total,
            "train/epoch": epoch + batch_idx / len(train_loader)
        })

    return running_loss / len(train_loader), correct / total

def evaluate(model, val_loader, criterion, device, dataset, epoch, num_samples=5):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_inputs = []
    all_labels = []
    all_predictions = []
    all_probs = []
    all_attentions = []

    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs, attention = model(inputs)
            loss = criterion(outputs, labels)
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

            all_inputs.append(inputs.cpu())
            all_labels.append(labels.cpu())
            all_predictions.append(predicted.cpu())
            all_probs.append(outputs.softmax(dim=1).cpu())
            all_attentions.append(attention.cpu())

    all_inputs = torch.cat(all_inputs)
    all_labels = torch.cat(all_labels)
    all_predictions = torch.cat(all_predictions)
    all_probs = torch.cat(all_probs)
    all_attentions = torch.cat(all_attentions)

    # Visualize samples
    if epoch % 5 == 0:  # Visualize every 5 epochs
        font_path = '/Users/erniesg/Library/Fonts/BabelStoneHan.ttf'
        prop = fm.FontProperties(fname=font_path)

        output_dir = os.path.join('data', 'output', f'epoch_{epoch}')
        os.makedirs(output_dir, exist_ok=True)

        for i in range(num_samples):
            idx = torch.randint(0, len(all_inputs), (1,)).item()
            input_img = all_inputs[idx].permute(1, 2, 0).numpy()

            # Denormalize the image
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])
            input_img = std * input_img + mean
            input_img = np.clip(input_img, 0, 1)

            attention_map = all_attentions[idx].squeeze().numpy()
            label = all_labels[idx].item()
            prediction = all_predictions[idx].item()

            # Create a more compact figure with 2 subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

            # Input Image
            ax1.imshow(input_img)
            ax1.set_title("Input Image")
            ax1.axis('off')

            # Overlay attention on input image
            ax2.imshow(input_img)
            attention_overlay = ax2.imshow(1 - attention_map, cmap='Greys', alpha=0.7, interpolation='nearest')
            ax2.set_title("Attention Overlay")
            ax2.axis('off')
            fig.colorbar(attention_overlay, ax=ax2, fraction=0.046, pad=0.04)

            true_char = dataset.get_class_chinese(label)
            pred_char = dataset.get_class_chinese(prediction)

            plt.suptitle(f"True: {label} ({true_char}) | Predicted: {prediction} ({pred_char})",
                         fontproperties=prop, fontsize=12)

            plt.tight_layout()
            fig.savefig(os.path.join(output_dir, f'sample_{i}.png'), bbox_inches='tight')
            plt.close(fig)

        # Log samples to wandb
        wandb.log({"sample_predictions": [wandb.Image(os.path.join(output_dir, f'sample_{i}.png')) for i in range(num_samples)]})

    # Log predictions table with correct/incorrect information
    log_image_table(all_inputs[:num_samples], all_predictions[:num_samples],
                    all_labels[:num_samples], all_probs[:num_samples], dataset.classes)

    # Log confusion matrix
    log_confusion_matrix(all_labels.numpy(), all_predictions.numpy(), dataset.classes)

    # Log metrics
    val_loss = running_loss / len(val_loader)
    val_acc = correct / total
    log_metrics({
        "val/loss": val_loss,
        "val/accuracy": val_acc,
        "val/epoch": epoch
    })

    return val_loss, val_acc

def main(args):
    device = get_device()
    print(f"Using device: {device}")

    # Initialize wandb
    config = {
        "learning_rate": args.learning_rate,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "image_size": args.image_size,
        "patience": args.patience
    }
    config = init_wandb("chinese-char-recognition", config)

    try:
        train_loader, val_loader, test_loader, full_dataset = get_dataloaders(
            args.dataset_path, args.id_to_chinese_path, config.batch_size, (config.image_size, config.image_size)
        )
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    print(f"Number of classes: {len(full_dataset.class_to_idx)}")

    model = SimpleCNN(num_classes=len(full_dataset.class_to_idx)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)

    best_val_acc = 0
    patience = config.patience
    counter = 0

    for epoch in range(config.epochs):
        train_loss, train_acc = train(model, train_loader, criterion, optimizer, device, epoch)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device, full_dataset, epoch)

        print(f"Epoch {epoch+1}/{config.epochs}:")
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), 'best_model.pth')
            log_model('best_model.pth', 'chinese_char_model', aliases=[f"epoch-{epoch+1}"])
            counter = 0
        else:
            counter += 1
            if counter >= patience:
                print(f"Early stopping after {epoch+1} epochs")
                break

    print("Training completed. Evaluating on test set...")
    model.load_state_dict(torch.load('best_model.pth'))
    test_loss, test_acc = evaluate(model, test_loader, criterion, device, full_dataset, epoch=config.epochs)
    print(f"Test Loss: {test_loss:.4f}, Test Acc: {test_acc:.4f}")

    # Log final test metrics
    log_metrics({
        "test/loss": test_loss,
        "test/accuracy": test_acc
    })

    # Finish the wandb run
    finish_run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Chinese character recognition model")
    parser.add_argument('--dataset_path', type=str, required=True, help="Path to the dataset")
    parser.add_argument('--id_to_chinese_path', type=str, required=True, help="Path to ID_to_Chinese.json")
    parser.add_argument('--batch_size', type=int, default=32, help="Batch size")
    parser.add_argument('--image_size', type=int, default=64, help="Image size (width and height)")
    parser.add_argument('--learning_rate', type=float, default=0.001, help="Learning rate")
    parser.add_argument('--epochs', type=int, default=50, help="Number of epochs")
    parser.add_argument('--patience', type=int, default=5, help="Patience for early stopping")
    args = parser.parse_args()
    main(args)
