import os
import json
import torch
from torchvision import transforms
from torch.utils.data import DataLoader, Dataset
from PIL import Image
import matplotlib.pyplot as plt

def pad_image(img, target_size):
    w, h = img.size
    ratio = min(target_size[0] / w, target_size[1] / h)
    new_w, new_h = int(w * ratio), int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    padded_img = Image.new('RGB', target_size, (255, 255, 255))
    padded_img.paste(img, ((target_size[0] - new_w) // 2, (target_size[1] - new_h) // 2))
    return padded_img

class ChineseCharDataset(Dataset):
    def __init__(self, root_dir, id_to_chinese_path, transform=None, target_size=(64, 64)):
        self.root_dir = os.path.join(root_dir, "Dataset")
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self.target_size = target_size

        with open(id_to_chinese_path, 'r') as f:
            self.id_to_chinese = json.load(f)

        self.classes = sorted([d for d in os.listdir(self.root_dir) if os.path.isdir(os.path.join(self.root_dir, d))])
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}
        self.samples = []
        for cls in self.classes:
            class_dir = os.path.join(self.root_dir, cls)
            for img_name in os.listdir(class_dir):
                img_path = os.path.join(class_dir, img_name)
                if os.path.isfile(img_path):
                    self.samples.append((img_path, cls))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = Image.open(img_path).convert('RGB')
        img = pad_image(img, self.target_size)
        if self.transform:
            img = self.transform(img)
        return img, self.class_to_idx[label]

    def get_class_chinese(self, label):
        class_id = self.classes[label]
        return self.id_to_chinese.get(class_id, "Unknown")

def get_dataloaders(dataset_path, id_to_chinese_path, batch_size=32, target_size=(64, 64)):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    full_dataset = ChineseCharDataset(dataset_path, id_to_chinese_path, transform, target_size)

    train_size = int(0.8 * len(full_dataset))
    val_size = int(0.1 * len(full_dataset))
    test_size = len(full_dataset) - train_size - val_size

    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size, test_size]
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    print(f"Dataset sizes: Train: {len(train_dataset)}, Validation: {len(val_dataset)}, Test: {len(test_dataset)}")

    return train_loader, val_loader, test_loader, full_dataset

def show_sample_images(dataset, num_images=5):
    fig, axes = plt.subplots(1, num_images, figsize=(15, 3))
    for i in range(num_images):
        img, label = dataset[i]
        axes[i].imshow(img.permute(1, 2, 0).clip(0, 1))
        axes[i].set_title(f"Class: {dataset.get_class_chinese(label)}")
        axes[i].axis('off')
    plt.tight_layout()
    plt.show()
