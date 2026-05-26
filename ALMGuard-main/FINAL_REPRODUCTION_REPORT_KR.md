# ALMGuard 최종 부분 재현 보고서

이 문서는 `ALMGuard-main.zip` 공개 코드와 공개 ZIP에 포함된 샘플을 이용해 수행한 부분 재현 절차와 결과를 정리한 최종 문서입니다. 교수님 환경에서는 ZIP을 임의 경로에 압축 해제한 뒤, 아래 명령을 `ALMGuard-main` 루트에서 실행하면 됩니다.

## 0. 전체 실행 순서 요약

아래 순서대로 실행하면 이번 재현 범위인 **Table 1 일부 SRoA + Table 2 WER**를 재현할 수 있습니다.

| 순서 | 목적 | 실행 파일/명령 | 주요 output |
| ---: | --- | --- | --- |
| 1 | 환경 설치 | `conda create`, `pip install -r requirements.txt` | `ALMGuard` conda 환경 |
| 2 | Qwen2-Audio 로딩 확인 | `python test_qwen_load.py` | `Qwen2-Audio loaded successfully.` |
| 3 | Whisper checkpoint 준비 | `models/large-v3.pt` 준비 | `models/large-v3.pt` |
| 4 | SAP smoke test | `python main.py --save_path ./results/prot_qwen_smoke ... --max_train_samples 3 --max_iter 5` | `results/prot_qwen_smoke/perturb_mel_epoch_0_iter_*.pth` |
| 5 | full SAP 학습 | `python main.py --save_path ./results/prot_qwen_full ...` | `results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth` |
| 6 | None baseline response 생성 | `python eval_qwen_baseline.py ... --skip_scoring` | `results/repro_*_none/responses_eval_none_qwen.pkl` |
| 7 | ALMGuard response 생성 | `python eval_qwen.py --perturb_path "$PERTURB" ... --skip_scoring` | `results/repro_*_almguard_final/responses_eval_prot_qwen.pkl` |
| 8 | SRoA 채점 | `python score_responses.py --response_path <response.pkl>` | 터미널의 `SRoA = ...` |
| 9 | None WER 계산 | `python eval_asr_baseline.py ...` | 터미널의 `WER = ...` |
| 10 | ALMGuard WER 계산 | `python eval_asr.py --perturb_paths "$PERTURB" ...` | 터미널의 `WER = ...` |

핵심 실행 흐름은 다음과 같습니다.

```bash
# 1. 환경 확인
python test_qwen_load.py

# 2. full SAP 학습
python main.py \
  --save_path ./results/prot_qwen_full \
  --wav_dirs ./results/advwave_p ./results/advwave_suffix ./results/pair_audio \
  --num_epochs 1 \
  --model_path Qwen/Qwen2-Audio-7B \
  --asr_path ./models/large-v3.pt \
  --prefix qwen_full

# 3. 최종 perturbation 지정
PERTURB=./results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth

# 4. None baseline response 생성
python eval_qwen_baseline.py --model_path Qwen/Qwen2-Audio-7B --wav_dirs ./results/advwave_suffix --save_path ./results/repro_advwave_none --skip_scoring
python eval_qwen_baseline.py --model_path Qwen/Qwen2-Audio-7B --wav_dirs ./results/advwave_p --save_path ./results/repro_advwave_p_none --skip_scoring
python eval_qwen_baseline.py --model_path Qwen/Qwen2-Audio-7B --wav_dirs ./results/pair_audio --save_path ./results/repro_pair_audio_none --skip_scoring

# 5. ALMGuard response 생성
python eval_qwen.py --model_path Qwen/Qwen2-Audio-7B --wav_dirs ./results/advwave_suffix --perturb_path "$PERTURB" --save_path ./results/repro_advwave_almguard_final --skip_scoring
python eval_qwen.py --model_path Qwen/Qwen2-Audio-7B --wav_dirs ./results/advwave_p --perturb_path "$PERTURB" --save_path ./results/repro_advwave_p_almguard_final --skip_scoring
python eval_qwen.py --model_path Qwen/Qwen2-Audio-7B --wav_dirs ./results/pair_audio --perturb_path "$PERTURB" --save_path ./results/repro_pair_audio_almguard_final --skip_scoring

# 6. SRoA 채점
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_advwave_p_none/responses_eval_none_qwen.pkl
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_pair_audio_none/responses_eval_none_qwen.pkl
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl

# 7. WER 계산
python eval_asr_baseline.py --model_path Qwen/Qwen2-Audio-7B --data_path ./datasets/libri_wav_txt_pairs.json --max_samples 20
python eval_asr.py --model_path Qwen/Qwen2-Audio-7B --data_path ./datasets/libri_wav_txt_pairs.json --perturb_paths "$PERTURB" --max_samples 20
```

SRoA 채점은 0-1 fraction으로 출력됩니다. 논문 표와 비교할 때는 `SRoA = 0.150000`을 `15.0%`처럼 변환합니다.

## 1. 최종 재현 범위

이번 재현 목표는 논문 전체가 아니라, PPT에 넣을 수 있는 Qwen2-Audio 기준 핵심 부분 재현입니다.

재현한 항목:

- **Table 1 일부**: Qwen2-Audio에서 `AdvWave`, `AdvWave-P`, `PAIR-Audio`에 대한 `None` vs `ALMGuard` SRoA 비교
- **Table 2 일부**: Qwen2-Audio에서 LibriSpeech 샘플에 대한 `None` vs `ALMGuard` WER 비교

재현하지 않은 항목:

- Table 1의 나머지 공격(`Gupta et al.`, `ICA`, `PAP-Audio`)
- Table 1의 다른 모델(`LLaMA-Omni`, `Lyra-Base`, `Qwen2.5-Omni`)
- Table 2의 `RQS`

`RQS`는 AIR-Bench-Chat 기반 model utility 평가로, 이번 `SAP 학습 -> 공격 response 생성 -> SRoA 채점 -> ASR WER` 흐름과 별도입니다. 공식 repo에는 `AIR-bench/Inference_Chat.py`, `score_chat.py`, `cal_score.py`가 있으나 이번 최종 범위에서는 제외했습니다.

## 2. 논문 표와의 대응

| 논문 항목 | 이번 재현에서 수행한 항목 | 비교 가능 여부 |
| --- | --- | --- |
| Table 1 Qwen2-Audio None SRoA | `eval_qwen_baseline.py`로 세 공격 response 생성 후 SorryBench 채점 | 가능 |
| Table 1 Qwen2-Audio ALMGuard SRoA | full SAP 학습 후 최종 perturbation으로 response 생성, SorryBench 채점 | 가능 |
| Table 2 Qwen2-Audio None WER | `eval_asr_baseline.py`로 LibriSpeech 샘플 WER 계산 | 가능 |
| Table 2 Qwen2-Audio ALMGuard WER | 최종 perturbation으로 `eval_asr.py` 실행 | 가능 |
| Table 2 Qwen2-Audio RQS | AIR-Bench-Chat 별도 실행 필요 | 이번 범위 제외 |

논문 기준값:

| Attack | Paper None SRoA | Paper ALMGuard SRoA |
| --- | ---: | ---: |
| AdvWave | 86.4 | 3.1 |
| AdvWave-P | 80.8 | 11.7 |
| PAIR-Audio | 45.0 | 34.9 |
| Average | 70.7 | 16.6 |

| Setting | Paper WER |
| --- | ---: |
| Qwen2-Audio None | 6.85 |
| Qwen2-Audio + ALMGuard | 8.70 |

## 3. 공개 ZIP 데이터 상태

공개 ZIP을 압축 해제한 뒤 확인한 샘플 수는 다음과 같습니다.

```bash
python - <<'PY'
from pathlib import Path
for p in [
    'datasets/advbench_audios',
    'datasets/librispeech_audios',
    'results/advwave_suffix',
    'results/advwave_p',
    'results/pair_audio',
]:
    d = Path(p)
    print(f'{p}: {len(list(d.glob("*.wav")))} wav files')
print('mask/global_saliency.npz:', Path('mask/global_saliency.npz').exists())
PY
```

확인된 수량:

- `datasets/advbench_audios`: 100개
- `datasets/librispeech_audios`: 19개
- `results/advwave_suffix`: 19개
- `results/advwave_p`: 20개
- `results/pair_audio`: 20개
- `mask/global_saliency.npz`: 존재

주의할 점은 공개 ZIP이 논문 전체 평가셋과 동일하지 않다는 것입니다. 특히 논문 Table 1/2의 전체 평가셋 규모와 공개 ZIP 샘플 수가 다르므로, 절대값이 논문 표와 일치하지 않을 수 있습니다.

## 4. 환경 설정

```bash
cd /path/to/your/workdir
unzip ALMGuard-main.zip
cd ALMGuard-main

conda create -n ALMGuard python=3.10
conda activate ALMGuard
pip install -r requirements.txt
```

GPU 확인:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Qwen2-Audio 로딩 확인:

```bash
python test_qwen_load.py
```

실제 실행 환경에서는 다음이 확인되었습니다.

- GPU: NVIDIA RTX A6000 48GB
- PyTorch: `2.2.2+cu121`
- CUDA 사용 가능
- Qwen2-Audio 로딩 성공

## 5. Hugging Face 접근 설정

SRoA 채점은 논문 방식과 동일하게 SorryBench judge model을 사용합니다.

- Qwen2-Audio: `Qwen/Qwen2-Audio-7B`
- SorryBench judge: `sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406`

`sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406`는 gated model이므로 Hugging Face 웹사이트에서 접근 허용을 먼저 받아야 합니다.

토큰 설정:

```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
huggingface-cli login --token "$HF_TOKEN"
```

로그인 확인:

```bash
python - <<'PY'
from huggingface_hub import whoami
print(whoami()["name"])
PY
```

서버에 기존의 잘못된 `HF_TOKEN` 또는 `HUGGING_FACE_HUB_TOKEN`이 남아 있으면 `huggingface-cli login`보다 환경변수가 우선되어 `401 Unauthorized`가 날 수 있습니다. 이 경우 아래처럼 실행합니다.

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl
```

토큰은 보고서, PPT, GitHub, ZIP 안에 포함하지 않습니다.

## 6. Whisper-large-v3 준비

SAP 학습에는 Whisper-large-v3 checkpoint가 필요합니다. 기본 경로는 `models/large-v3.pt`입니다.

```bash
mkdir -p models
python -c "import os, whisper; os.makedirs('models', exist_ok=True); print(whisper._download(whisper._MODELS['large-v3'], 'models', False))"
```

다른 위치에 checkpoint가 있으면 `main.py` 실행 시 `--asr_path`로 지정합니다.

## 7. 코드 보강 사항

공식 ZIP을 그대로 실행하면 일부 문제가 있어 다음 보강을 추가했습니다.

- `main.py`: 누락된 `argparse` import 추가
- `main.py`: 누락된 `--prefix` 인자 추가
- `main.py`: Qwen2-Audio를 `torch.float16`으로 로드
- `main.py`: smoke test용 `--max_iter`, `--max_train_samples` 추가
- `eval_qwen.py`: `perturb=None`이면 원본 feature로 추론 가능하게 보강
- `eval_qwen.py`: `--skip_scoring` 추가
- `eval_qwen_baseline.py`: None baseline SRoA 평가용 스크립트 추가
- `eval_asr.py`: 실제 존재하는 WAV만 평가하고 `--max_samples` 지원
- `eval_asr_baseline.py`: None baseline WER 평가용 스크립트 추가
- `score_responses.py`: 저장된 response `.pkl`만 별도로 SRoA 채점하는 스크립트 추가
- `llm_evaluation.py`: 로컬 SorryBench 모델이 없으면 Hugging Face gated repo를 사용하도록 보강

## 8. 실행 순서

### 8.1 Smoke Test

긴 학습 전에 작은 설정으로 학습 루프가 도는지 확인합니다.

```bash
python main.py \
  --save_path ./results/prot_qwen_smoke \
  --wav_dirs ./results/advwave_p ./results/advwave_suffix ./results/pair_audio \
  --num_epochs 1 \
  --model_path Qwen/Qwen2-Audio-7B \
  --asr_path ./models/large-v3.pt \
  --prefix qwen_smoke \
  --max_train_samples 3 \
  --max_iter 5
```

실제 실행에서 smoke test는 성공했고, `results/prot_qwen_smoke/perturb_mel_epoch_0_iter_*.pth`가 생성되었습니다.

### 8.2 Full SAP 학습

논문 Table 1/Table 2 WER와 비교할 최종 결과는 full SAP 학습의 마지막 perturbation을 사용했습니다.

```bash
python main.py \
  --save_path ./results/prot_qwen_full \
  --wav_dirs ./results/advwave_p ./results/advwave_suffix ./results/pair_audio \
  --num_epochs 1 \
  --model_path Qwen/Qwen2-Audio-7B \
  --asr_path ./models/large-v3.pt \
  --prefix qwen_full
```

최종 산출물:

```text
results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth
```

공개 ZIP 기준 interleave된 공격 audio가 총 57개이므로 `iter_0`부터 `iter_56`까지 생성되었습니다. RTX A6000 48GB 단일 GPU에서 수 시간 이상 소요되었습니다.

### 8.3 None Baseline Response 생성

공식 repo에는 None baseline 전용 스크립트가 없어 `eval_qwen_baseline.py`를 추가했습니다.

```bash
python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --save_path ./results/repro_advwave_none \
  --skip_scoring

python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_p \
  --save_path ./results/repro_advwave_p_none \
  --skip_scoring

python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/pair_audio \
  --save_path ./results/repro_pair_audio_none \
  --skip_scoring
```

생성된 파일:

- `results/repro_advwave_none/responses_eval_none_qwen.pkl`
- `results/repro_advwave_p_none/responses_eval_none_qwen.pkl`
- `results/repro_pair_audio_none/responses_eval_none_qwen.pkl`

### 8.4 Final ALMGuard Response 생성

```bash
PERTURB=./results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth

python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_almguard_final \
  --skip_scoring

python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_p \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_p_almguard_final \
  --skip_scoring

python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/pair_audio \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_pair_audio_almguard_final \
  --skip_scoring
```

생성된 파일:

- `results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl`
- `results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl`
- `results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl`

### 8.5 SRoA 채점

`score_responses.py`는 저장된 response `.pkl`을 SorryBench judge로 채점합니다. 출력값은 0-1 fraction이므로 논문 표와 비교할 때는 `%`로 변환합니다.

None baseline:

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_p_none/responses_eval_none_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_pair_audio_none/responses_eval_none_qwen.pkl
```

ALMGuard:

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl
```

GPU가 여러 장 있으면 `CUDA_VISIBLE_DEVICES=0/1/2`를 붙여 병렬로 실행할 수 있습니다.

### 8.6 WER 평가

None WER:

```bash
python eval_asr_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --data_path ./datasets/libri_wav_txt_pairs.json \
  --max_samples 20
```

ALMGuard WER:

```bash
python eval_asr.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --data_path ./datasets/libri_wav_txt_pairs.json \
  --perturb_paths ./results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth \
  --max_samples 20
```

공개 ZIP에 실제 존재하는 LibriSpeech WAV가 19개이므로, 위 WER는 19개 샘플 기준입니다.

## 9. 최종 실행 결과

### 9.1 Table 1 일부 재현: Qwen2-Audio SRoA

`score_responses.py` 출력값을 `%`로 변환한 결과입니다.

| Attack | Paper None | Paper ALMGuard | Our None | Our ALMGuard |
| --- | ---: | ---: | ---: | ---: |
| AdvWave | 86.4 | 3.1 | 0.0 | 0.0 |
| AdvWave-P | 80.8 | 11.7 | 0.0 | 0.0 |
| PAIR-Audio | 45.0 | 34.9 | 5.0 | 15.0 |
| Average | 70.7 | 16.6 | 1.7 | 5.0 |

원래 출력값:

| Attack | None SRoA fraction | ALMGuard SRoA fraction |
| --- | ---: | ---: |
| AdvWave | 0.000000 | 0.000000 |
| AdvWave-P | 0.000000 | 0.000000 |
| PAIR-Audio | 0.050000 | 0.150000 |

### 9.2 Table 2 일부 재현: Qwen2-Audio WER

| Setting | Paper WER | Our WER |
| --- | ---: | ---: |
| Qwen2-Audio None | 6.85 | 46.28 |
| Qwen2-Audio + ALMGuard | 8.70 | 62.96 |

원래 출력값:

- None WER: `0.462786`
- Final ALMGuard WER: `0.629574`

## 10. 결과 해석

이번 실험은 코드 실행 파이프라인 재현에는 성공했지만, 수치가 논문 표와 크게 다릅니다.

주요 차이:

- 논문은 전체 평가셋 기준 결과이고, 공개 ZIP에는 일부 샘플만 포함되어 있습니다.
- 공개 ZIP의 `AdvWave`는 19개, `AdvWave-P`는 20개, `PAIR-Audio`는 20개만 평가되었습니다.
- Our None SRoA가 논문 None보다 지나치게 낮습니다. 이는 공개 공격 audio subset이 논문 평가셋과 다르거나, Qwen2-Audio 추론 prompt/response 형식, SorryBench judge 입력 구성, 공격 audio와 prompt 매칭 방식이 논문 내부 실험과 다르기 때문일 수 있습니다.
- WER가 논문보다 크게 높습니다. 현재 `eval_asr.py`는 Qwen2-Audio 응답에서 transcription만 정교하게 파싱하지 않고, `Audio 1:`, `Audio 2:`, punctuation, assistant marker 등이 섞인 문자열을 그대로 WER에 넣는 경우가 있습니다.
- Table 2의 RQS는 AIR-Bench-Chat 별도 평가가 필요하며 이번 결과에는 포함되지 않았습니다.

따라서 PPT에는 다음처럼 표현하는 것이 안전합니다.

```text
공식 공개 ZIP 기반으로 ALMGuard의 Qwen2-Audio 부분 재현 파이프라인을 실행했다.
Table 1의 AdvWave/AdvWave-P/PAIR-Audio에 대해 None vs ALMGuard SRoA를 계산했고,
Table 2 중 WER 항목을 계산했다.
다만 공개 ZIP 샘플 수와 평가 스크립트/응답 파싱 차이로 인해 논문 표의 절대 수치와는 차이가 있으며,
이번 결과는 "공개 코드 기반 실행 가능성 및 부분 재현"으로 해석한다.
```

## 11. 최종 산출물 목록

SAP:

- `results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth`
- `results/prot_qwen_full/records_qwen_full_0502.pkl`
- `results/prot_qwen_full/responses_qwen_full_0502.pkl`

None response:

- `results/repro_advwave_none/responses_eval_none_qwen.pkl`
- `results/repro_advwave_p_none/responses_eval_none_qwen.pkl`
- `results/repro_pair_audio_none/responses_eval_none_qwen.pkl`

ALMGuard final response:

- `results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl`
- `results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl`
- `results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl`

문서:

- `REPRODUCTION_KR.md`: 실행 가이드
- `EXPERIMENT_RESULTS_KR.md`: 실행 결과 요약
- `FINAL_REPRODUCTION_REPORT_KR.md`: 최종 통합 보고서

## 12. Troubleshooting

`401 Unauthorized` 또는 `403 Forbidden`:

- Hugging Face에서 `sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406` 접근 승인이 되었는지 확인합니다.
- `HF_TOKEN`이 올바른지 확인합니다.
- 기존 invalid 환경변수가 우선되는 경우 아래처럼 실행합니다.

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl
```

`KeyError: qwen2-audio`:

```bash
pip uninstall -y transformers
pip install git+https://github.com/huggingface/transformers
```

GPU OOM:

- Qwen2-Audio와 SorryBench judge가 모두 큰 모델이므로 한 GPU에 여러 프로세스를 올리지 않습니다.
- `CUDA_VISIBLE_DEVICES`로 실험을 GPU별로 분리합니다.

## 13. 캡처 추천 목록

- `nvidia-smi` GPU 환경
- `conda activate ALMGuard` 및 package 설치
- Qwen2-Audio 로딩 성공
- Whisper-large-v3 checkpoint 준비
- full SAP 학습 완료 및 `perturb_mel_epoch_0_iter_56.pth`
- final response 생성 로그
- SorryBench SRoA 출력 로그
- WER 출력 로그
- 최종 결과 표
