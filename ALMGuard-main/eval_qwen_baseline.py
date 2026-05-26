import argparse
import os
import pickle

import torch
from tqdm import tqdm
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

from eval import attack_performance_eval
from eval_qwen import qwen_infer


def main():
    parser = argparse.ArgumentParser(description="Evaluate Qwen2-Audio without ALMGuard perturbation")
    parser.add_argument('--model_path', type=str, default='Qwen/Qwen2-Audio-7B',
                        help='Path to pretrained Qwen2-Audio model')
    parser.add_argument('--wav_dirs', nargs='+', default=['./results/advwave_suffix'],
                        help='One or more directories containing .wav files')
    parser.add_argument('--save_path', type=str, default='./results/responses_none',
                        help='Directory to save response pickles')
    parser.add_argument('--skip_scoring', action='store_true',
                        help='Only save Qwen responses without running SorryBench SRoA scoring')
    args = parser.parse_args()

    os.makedirs(args.save_path, exist_ok=True)

    processor = AutoProcessor.from_pretrained(args.model_path)
    model = Qwen2AudioForConditionalGeneration.from_pretrained(
        args.model_path,
        device_map="auto",
        torch_dtype=torch.float16,
    )

    audio_list = []
    for wav_dir in args.wav_dirs:
        for fname in os.listdir(wav_dir):
            if fname.lower().endswith('.wav'):
                audio_list.append(os.path.join(wav_dir, fname))

    sorted_audio_list = sorted(
        audio_list,
        key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
    )

    response_file = os.path.join(args.save_path, "responses_eval_none_qwen.pkl")

    responses = []
    for audio in tqdm(sorted_audio_list, desc="Evaluating audio files without ALMGuard"):
        responses.append(qwen_infer([audio], processor, model, perturb=None))

    with open(response_file, 'wb') as f:
        pickle.dump(responses, f)

    print(f"Results saved to {response_file}")
    if args.skip_scoring:
        print("SRoA scoring skipped.")
    else:
        sroa = attack_performance_eval(responses)
        print(f"SRoA = {sroa:.6f}")


if __name__ == '__main__':
    main()
