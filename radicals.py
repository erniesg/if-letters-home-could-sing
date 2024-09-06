import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributed as dist
from sam2.sam2_image_predictor import SAM2ImagePredictor
from torchvision.models import resnet50
import numpy as np

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")

class RadicalSegmentor:
    def __init__(self):
        self.device = get_device()
        print(f"Using device: {self.device}")
        self.predictor = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-large").to(self.device)

    def segment_image(self, image):
        if isinstance(image, np.ndarray):
            image = torch.tensor(image).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.inference_mode(), torch.autocast(device_type=self.device.type, dtype=torch.bfloat16):
            self.predictor.set_image(image)
            masks, _, _ = self.predictor.predict([])
        return masks

class MoCo(nn.Module):
    def __init__(self, base_encoder, feature_dim=128, queue_size=65536, momentum=0.999, temperature=0.07):
        super(MoCo, self).__init__()

        self.encoder_q = base_encoder(num_classes=feature_dim)
        self.encoder_k = base_encoder(num_classes=feature_dim)

        for param_q, param_k in zip(self.encoder_q.parameters(), self.encoder_k.parameters()):
            param_k.data.copy_(param_q.data)
            param_k.requires_grad = False

        self.register_buffer("queue", torch.randn(feature_dim, queue_size))
        self.queue = nn.functional.normalize(self.queue, dim=0)
        self.register_buffer("queue_ptr", torch.zeros(1, dtype=torch.long))

        self.momentum = momentum
        self.temperature = temperature
        self.queue_size = queue_size

    @torch.no_grad()
    def _momentum_update_key_encoder(self):
        for param_q, param_k in zip(self.encoder_q.parameters(), self.encoder_k.parameters()):
            param_k.data = param_k.data * self.momentum + param_q.data * (1. - self.momentum)

    @torch.no_grad()
    def _dequeue_and_enqueue(self, keys):
        if dist.is_initialized():
            keys = concat_all_gather(keys)
        batch_size = keys.shape[0]
        ptr = int(self.queue_ptr)
        assert self.queue_size % batch_size == 0
        self.queue[:, ptr:ptr + batch_size] = keys.T
        ptr = (ptr + batch_size) % self.queue_size
        self.queue_ptr[0] = ptr

    def forward(self, im_q, im_k):
        q = self.encoder_q(im_q)
        q = nn.functional.normalize(q, dim=1)

        with torch.no_grad():
            self._momentum_update_key_encoder()
            k = self.encoder_k(im_k)
            k = nn.functional.normalize(k, dim=1)

        l_pos = torch.einsum('nc,nc->n', [q, k]).unsqueeze(-1)
        l_neg = torch.einsum('nc,ck->nk', [q, self.queue.clone().detach()])

        logits = torch.cat([l_pos, l_neg], dim=1)
        logits /= self.temperature

        labels = torch.zeros(logits.shape[0], dtype=torch.long).to(logits.device)

        self._dequeue_and_enqueue(k)

        return logits, labels

class MoCoAnnotator:
    def __init__(self, model_path=None, base_encoder=resnet50, feature_dim=128, queue_size=65536, momentum=0.999, temperature=0.07):
        self.device = get_device()
        self.moco_model = MoCo(base_encoder, feature_dim, queue_size, momentum, temperature).to(self.device)
        if model_path and os.path.exists(model_path):
            self.moco_model.load_state_dict(torch.load(model_path, map_location=self.device))

    def annotate(self, segmented_masks):
        annotations = []
        for mask in segmented_masks:
            mask = mask.to(self.device)
            with torch.no_grad():
                logits, _ = self.moco_model(mask, mask)
            annotation = torch.argmax(logits, dim=1)
            annotations.append(annotation.cpu().numpy())
        return annotations

    def save_model(self, path):
        torch.save(self.moco_model.state_dict(), path)

def run_segmentation_and_annotation(image, segmentor, annotator):
    masks = segmentor.segment_image(image)
    annotations = annotator.annotate(masks)
    return annotations, masks
