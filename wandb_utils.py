import wandb
import torch
import matplotlib.pyplot as plt

def init_wandb(project_name, config):
    """Initialize a new wandb run"""
    wandb.init(project=project_name, config=config)
    return wandb.config

def log_metrics(metrics, step=None):
    """Log metrics to wandb"""
    wandb.log(metrics, step=step)

def log_model(model_path, model_name, aliases=None):
    """Log a model checkpoint to wandb"""
    wandb.save(model_path)
    if aliases:
        wandb.log_artifact(model_path, name=model_name, type="model", aliases=aliases)
    else:
        wandb.log_artifact(model_path, name=model_name, type="model")

def log_image_table(images, predicted, labels, probs, class_names):
    """Log a wandb.Table with (img, pred, target, scores, correct)"""
    table = wandb.Table(columns=["image", "pred", "target", "correct"] + [f"score_{i}" for i in range(len(class_names))])
    for img, pred, targ, prob in zip(images, predicted, labels, probs):
        img_wandb = wandb.Image(img.permute(1, 2, 0).numpy())
        correct = "Yes" if pred == targ else "No"
        table.add_data(img_wandb, f"{pred.item()} ({class_names[pred]})",
                       f"{targ.item()} ({class_names[targ]})", correct, *prob.numpy())
    wandb.log({"predictions_table": table}, commit=False)

def log_confusion_matrix(y_true, y_pred, class_names):
    """Log a confusion matrix"""
    wandb.sklearn.plot_confusion_matrix(y_true, y_pred, class_names)

def finish_run():
    """Finish the current wandb run"""
    wandb.finish()
