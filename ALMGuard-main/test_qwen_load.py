import torch
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration


def main():
    model_path = "Qwen/Qwen2-Audio-7B"

    AutoProcessor.from_pretrained(model_path)
    Qwen2AudioForConditionalGeneration.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch.float16,
    )

    print("Qwen2-Audio loaded successfully.")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")


if __name__ == "__main__":
    main()
