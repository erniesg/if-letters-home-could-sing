import torch

def check_memory_usage():
    if torch.cuda.is_available():
        print(f"GPU Memory Usage:")
        print(f"Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        print(f"Cached: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
    elif torch.backends.mps.is_available():
        print("Running on Apple MPS. Memory usage information not available.")
    else:
        print("Running on CPU. Memory usage information not available.")

def dry_run_check(trainer, dataloader, num_batches=5):
    initial_state = trainer.model.state_dict()
    trainer.dry_run(dataloader, num_batches)
    final_state = trainer.model.state_dict()

    for (k1, v1), (k2, v2) in zip(initial_state.items(), final_state.items()):
        if not torch.equal(v1, v2):
            print(f"Model parameters changed after dry run. Training is working.")
            return
    print("Warning: Model parameters did not change after dry run. Check your training loop.")
