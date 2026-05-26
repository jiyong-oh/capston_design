import argparse
import json
import pickle

from eval import attack_performance_eval


def load_responses(path):
    if path.endswith(".pkl"):
        with open(path, "rb") as f:
            return pickle.load(f)
    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise ValueError(f"Unsupported response file: {path}")


def main():
    parser = argparse.ArgumentParser(description="Score saved ALMGuard response files")
    parser.add_argument("--response_path", required=True,
                        help="Path to saved .pkl or .json response file")
    args = parser.parse_args()

    responses = load_responses(args.response_path)
    sroa = attack_performance_eval(responses)
    print(f"Response file: {args.response_path}")
    print(f"SRoA = {sroa:.6f}")


if __name__ == "__main__":
    main()
