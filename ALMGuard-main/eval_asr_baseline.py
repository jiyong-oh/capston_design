import argparse
import os

import torch
from tqdm import tqdm
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

from eval_qwen import qwen_infer
from utils import calc_asr_metrics, extract_single_quoted_text, get_json_pairs


def main():
    parser = argparse.ArgumentParser(description="Evaluate ASR performance without ALMGuard perturbation")
    parser.add_argument('--model_path', type=str, default='Qwen/Qwen2-Audio-7B',
                        help='Path to pretrained Qwen2-Audio model')
    parser.add_argument('--data_path', type=str, default='./datasets/libri_wav_txt_pairs.json',
                        help='Path to JSON file with wav-txt pairs')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='Maximum number of existing wav-text pairs to evaluate')
    args = parser.parse_args()

    processor = AutoProcessor.from_pretrained(args.model_path)
    model = Qwen2AudioForConditionalGeneration.from_pretrained(
        args.model_path,
        device_map='auto',
        torch_dtype=torch.float16,
    )

    data_list = [
        pair for pair in get_json_pairs(args.data_path, 'wav', 'txt')
        if os.path.exists(pair[0])
    ]
    if args.max_samples is not None:
        data_list = data_list[:args.max_samples]
    print(f"Loaded {len(data_list)} existing wav-text pairs from {args.data_path}")
    question = "Transcribe the audio into text word-for-word, preserving all words accurately."

    results = []
    for wav_path, org_txt in tqdm(data_list, desc="Evaluating ASR without ALMGuard"):
        response = qwen_infer([wav_path], processor, model, perturb=None, question=question)
        transcript = extract_single_quoted_text(response)
        print(f"Orig: {org_txt} -> Transcribed: {transcript}")
        results.append((org_txt, transcript))

    _, _, _, avg_cer, avg_wer = calc_asr_metrics(results)
    print("Perturbation: None")
    print(f"CER = {avg_cer:.6f}")
    print(f"WER = {avg_wer:.6f}")


if __name__ == '__main__':
    main()
