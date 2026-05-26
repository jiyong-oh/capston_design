# ALMGuard 부분 재현 실행 가이드

이 문서는 교수님이 ZIP으로 받은 공식 ALMGuard 코드를 기준으로, PPT에 넣을 최종 재현 범위를 실행하기 위한 절차를 정리한 것입니다.

재현 목표는 다음 두 가지입니다.

- Table 1 / Table 3 일부 재현: Qwen2-Audio에서 AdvWave, AdvWave-P, PAIR-Audio에 대한 None vs ALMGuard SRoA 비교
- Table 2 일부 재현: Qwen2-Audio에서 LibriSpeech 샘플에 ALMGuard 적용 후 WER 측정

논문 기준값은 다음과 같이 정리합니다.

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

## 1. 압축 해제 후 폴더 확인

```bash
cd /path/to/your/workdir
unzip ALMGuard-main.zip
cd ALMGuard-main
```

이후 모든 명령은 `ALMGuard-main` repo 루트에서 실행합니다. 교수님 환경에서는 `/home/gpuadmin/Daeun/OpenSource`가 아니라 ZIP을 푼 실제 경로로 이동하면 됩니다.

현재 ZIP 기준으로 확인된 입력 파일은 다음과 같습니다.

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

주의: 현재 ZIP에는 `datasets/librispeech_audios`가 19개, `results/advwave_suffix`가 19개 들어 있습니다. 스크립트는 실제 존재하는 WAV만 평가하도록 수정되어 있습니다.

## 2. Conda 환경 생성

```bash
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

만약 `KeyError: qwen2-audio` 계열 오류가 나면 `transformers` 버전을 최신 GitHub 버전으로 교체합니다.

```bash
pip uninstall -y transformers
pip install git+https://github.com/huggingface/transformers
```

## 3. Hugging Face 접근 설정

Qwen2-Audio와 SorryBench judge model을 내려받으려면 Hugging Face 접근 권한이 필요할 수 있습니다. 특히 SRoA 채점은 논문 방식 그대로 하려면 아래 gated model 접근이 필요합니다.

- Qwen2-Audio: `Qwen/Qwen2-Audio-7B`
- SorryBench judge: `sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406`

먼저 Hugging Face 웹사이트에서 `sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406` 모델 페이지에 들어가 접근 허용을 요청/승인합니다.

그 다음 Hugging Face token을 준비합니다.

1. Hugging Face 로그인
2. Settings > Access Tokens
3. Read 권한 token 생성
4. gated repo 읽기 권한이 포함되어 있는지 확인

터미널에서는 다음처럼 설정합니다. 실제 토큰 값은 `hf_xxx` 자리에 넣습니다.

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

만약 서버에 기존의 잘못된 `HF_TOKEN` 또는 `HUGGING_FACE_HUB_TOKEN`이 설정되어 있으면, `huggingface-cli login`으로 저장한 token보다 환경변수가 우선 적용되어 `401 Unauthorized`가 날 수 있습니다. 이 경우 아래처럼 현재 셸의 token을 명시적으로 덮어씁니다.

```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
unset HUGGING_FACE_HUB_TOKEN
```

또는 저장된 login token을 쓰고 싶으면 명령 앞에 다음을 붙입니다.

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl
```

주의: token은 비밀번호처럼 취급합니다. 보고서, PPT, GitHub, ZIP 문서 안에 실제 token 값을 적지 않습니다.

## 4. Whisper-large-v3 준비

SAP 학습에는 Whisper-large-v3 checkpoint가 필요합니다. 기본 경로는 다음과 같습니다.

```bash
mkdir -p models
# models/large-v3.pt 위치에 Whisper checkpoint를 둡니다.
```

다른 경로에 있다면 `main.py` 실행 시 `--asr_path`로 넘기면 됩니다.

공식 Whisper checkpoint를 직접 받을 수 있는 환경이면 다음 명령으로 `models/large-v3.pt`를 준비할 수 있습니다.

```bash
python -c "import os, whisper; os.makedirs('models', exist_ok=True); print(whisper._download(whisper._MODELS['large-v3'], 'models', False))"
```

## 5. SAP 학습

논문 표와 비교할 최종 결과는 full SAP 학습 perturbation을 사용하는 것이 가장 적절합니다. 먼저 실행 가능 여부를 빠르게 확인하려면 작은 smoke test를 실행할 수 있습니다.

Smoke test:

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

논문 비교용 full SAP 학습:

```bash
python main.py \
  --save_path ./results/prot_qwen \
  --wav_dirs ./results/advwave_p ./results/advwave_suffix ./results/pair_audio \
  --num_epochs 1 \
  --model_path Qwen/Qwen2-Audio-7B \
  --asr_path ./models/large-v3.pt \
  --prefix qwen
```

현재 공개 ZIP 기준으로 `advwave_p` 20개, `advwave_suffix` 19개, `pair_audio` 20개가 있어 interleave 후 약 57개 adversarial audio를 학습합니다. RTX A6000 48GB 단일 GPU 기준 수 시간 이상 걸릴 수 있습니다. 중간 checkpoint는 `perturb_mel_epoch_0_iter_*.pth` 형태로 계속 저장되지만, PPT에서 논문 표와 비교할 최종값은 가능하면 가장 마지막 checkpoint를 사용합니다.

산출물 확인:

```bash
ls results/prot_qwen/*.pth
```

예상 산출물은 `perturb_mel_epoch_0_iter_*.pth`, `responses_qwen_*.pkl`, `records_qwen_*.pkl`입니다.

## 6. ALMGuard SRoA 평가

아래 명령에서 `PERTURB` 값은 실제 생성된 `.pth` 파일로 바꿉니다.

```bash
PERTURB=./results/prot_qwen/perturb_mel_epoch_0_iter_56.pth
```

AdvWave:

```bash
python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_almguard
```

AdvWave-P:

```bash
python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_p \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_p_almguard
```

PAIR-Audio:

```bash
python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/pair_audio \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_pair_audio_almguard
```

각 실행의 마지막 `SRoA = ...` 값을 PPT 표의 `Our ALMGuard`에 넣습니다.

SRoA 채점이 오래 걸리거나 SorryBench 권한 문제가 있으면, 먼저 Qwen 응답만 저장할 수 있습니다.

```bash
python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_almguard \
  --skip_scoring
```

이후 저장된 response 파일을 별도로 채점합니다.

```bash
python score_responses.py \
  --response_path ./results/repro_advwave_almguard/responses_eval_prot_qwen.pkl
```

## 7. None Baseline SRoA 평가

공식 repo에는 None baseline 전용 스크립트가 없어 `eval_qwen_baseline.py`를 추가했습니다. 이 스크립트는 perturbation을 더하지 않고 같은 평가 함수를 사용합니다.

```bash
python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --save_path ./results/repro_advwave_none

python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_p \
  --save_path ./results/repro_advwave_p_none

python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/pair_audio \
  --save_path ./results/repro_pair_audio_none
```

각 실행의 `SRoA = ...` 값을 PPT 표의 `Our None`에 넣습니다.

마찬가지로 응답 생성과 SRoA 채점을 분리할 수 있습니다.

```bash
python eval_qwen_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --save_path ./results/repro_advwave_none \
  --skip_scoring

python score_responses.py \
  --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl
```

## 8. ASR WER 평가

ALMGuard 적용 WER:

```bash
python eval_asr.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --data_path ./datasets/libri_wav_txt_pairs.json \
  --perturb_paths "$PERTURB" \
  --max_samples 20
```

None WER:

```bash
python eval_asr_baseline.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --data_path ./datasets/libri_wav_txt_pairs.json \
  --max_samples 20
```

현재 ZIP에 실제 존재하는 LibriSpeech WAV가 19개이므로, 위 명령은 19개 샘플 기준으로 WER를 계산합니다.

## 9. 병렬 실행 예시

GPU가 여러 장 있으면 Qwen 응답 생성과 WER 평가는 공격별로 나누어 병렬 실행할 수 있습니다.

```bash
CUDA_VISIBLE_DEVICES=0 python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_suffix \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_almguard \
  --skip_scoring

CUDA_VISIBLE_DEVICES=1 python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/advwave_p \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_advwave_p_almguard \
  --skip_scoring

CUDA_VISIBLE_DEVICES=2 python eval_qwen.py \
  --model_path Qwen/Qwen2-Audio-7B \
  --wav_dirs ./results/pair_audio \
  --perturb_path "$PERTURB" \
  --save_path ./results/repro_pair_audio_almguard \
  --skip_scoring
```

SRoA 채점도 response 파일이 이미 있으면 GPU별로 나눌 수 있습니다. 단, SorryBench judge model도 7B급이라 각 프로세스가 별도 GPU 메모리를 사용합니다.

```bash
CUDA_VISIBLE_DEVICES=0 python score_responses.py --response_path ./results/repro_advwave_almguard/responses_eval_prot_qwen.pkl
CUDA_VISIBLE_DEVICES=1 python score_responses.py --response_path ./results/repro_advwave_p_almguard/responses_eval_prot_qwen.pkl
CUDA_VISIBLE_DEVICES=2 python score_responses.py --response_path ./results/repro_pair_audio_almguard/responses_eval_prot_qwen.pkl
```

## 10. PPT 결과 표

| Attack | Paper None | Paper ALMGuard | Our None | Our ALMGuard |
| --- | ---: | ---: | ---: | ---: |
| AdvWave | 86.4 | 3.1 | 실행값 | 실행값 |
| AdvWave-P | 80.8 | 11.7 | 실행값 | 실행값 |
| PAIR-Audio | 45.0 | 34.9 | 실행값 | 실행값 |
| Average | 70.7 | 16.6 | 평균 | 평균 |

| Setting | Paper WER | Our WER |
| --- | ---: | ---: |
| Qwen2-Audio None | 6.85 | 실행값 |
| Qwen2-Audio + ALMGuard | 8.70 | 실행값 |

## 11. 캡처 체크리스트

- `nvidia-smi` GPU 환경
- conda 환경 생성 및 `pip install -r requirements.txt`
- 데이터/공격 폴더 WAV 개수 확인
- `python test_qwen_load.py` 성공
- Hugging Face gated model 접근 확인
- `main.py` SAP 학습 로그
- `results/prot_qwen/*.pth` 생성 결과
- 세 공격의 ALMGuard `SRoA = ...`
- 세 공격의 None baseline `SRoA = ...`
- ASR None / ALMGuard `WER = ...`
- 방어 전후 response case 2-3개

## 12. Troubleshooting

`401 Unauthorized` 또는 `403 Forbidden`:

- `sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406` 접근 승인이 완료되었는지 확인합니다.
- `HF_TOKEN`이 올바른 token인지 확인합니다.
- 서버에 예전 invalid token이 환경변수로 남아 있으면 `export HF_TOKEN="새 토큰"`으로 덮어쓰거나 `unset HUGGING_FACE_HUB_TOKEN`을 실행합니다.
- `python -c "from huggingface_hub import whoami; print(whoami())"`로 현재 token이 인식되는지 확인합니다.

`KeyError: qwen2-audio`:

- `transformers` 버전 문제일 수 있으므로 최신 GitHub 버전으로 교체합니다.

```bash
pip uninstall -y transformers
pip install git+https://github.com/huggingface/transformers
```

GPU OOM:

- Qwen2-Audio와 SorryBench judge는 각각 큰 모델입니다.
- 한 GPU에 여러 평가를 동시에 올리지 말고 `CUDA_VISIBLE_DEVICES`로 GPU를 나누어 실행합니다.
- `main.py`, `eval_qwen.py`, `eval_qwen_baseline.py`, `eval_asr.py`, `eval_asr_baseline.py`는 Qwen2-Audio를 `torch.float16`으로 로드하도록 보강했습니다.

## 13. 수정한 파일

- `main.py`: 누락된 `argparse` import와 `--prefix` 인자 추가
- `eval_qwen.py`: `perturb=None`이면 원본 audio feature로 추론하도록 보강
- `eval_qwen_baseline.py`: None baseline SRoA 평가 스크립트 추가
- `eval_asr.py`: 실제 존재하는 WAV만 평가하고 `--max_samples`를 지원하도록 보강
- `eval_asr_baseline.py`: None baseline WER 평가 스크립트 추가
- `test_qwen_load.py`: Qwen2-Audio 로딩 확인 스크립트 추가
- `score_responses.py`: 저장된 Qwen response `.pkl`을 나중에 SRoA 채점할 수 있도록 추가
- `llm_evaluation.py`: 로컬 SorryBench 모델이 없으면 Hugging Face gated repo를 사용하도록 보강
