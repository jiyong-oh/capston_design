# Cursor AI 코딩 툴 기반 오픈소스 구현 및 분석 보고서

## 1. 과제 개요

본 과제는 캡스톤디자인 프로젝트 수행 과정에서 AI 코딩 도구인 Cursor를 활용하여 타겟 논문의 오픈소스 코드를 실행 가능한 형태로 재현하고, 구현 과정과 실험 결과를 분석하는 것을 목표로 한다.

타겟 오픈소스는 ALMGuard 공식 GitHub 코드이며, GitHub 제출 기준으로는 `OpenSource` 폴더 아래에 다음 ZIP 파일과 압축 해제 폴더를 둔다.

```text
OpenSource/
├── ALMGuard-main.zip
└── ALMGuard-main/
```

압축 해제 후 작업 디렉터리는 다음과 같다. 이후 모든 실행 명령은 이 폴더를 기준으로 수행한다.

```text
OpenSource/ALMGuard-main
```

타겟 논문:

```text
ALMGuard: Safety Shortcuts and Where to Find Them as Guardrails for Audio-Language Models
```

최종 재현 범위는 논문 전체가 아니라, 공개 ZIP에 포함된 데이터와 GPU 환경에서 현실적으로 실행 가능한 부분 재현으로 설정하였다.

재현 대상:

- Table 1 일부: Qwen2-Audio에서 AdvWave, AdvWave-P, PAIR-Audio에 대한 None vs ALMGuard SRoA 비교
- Table 2 일부: Qwen2-Audio에서 LibriSpeech 샘플에 대한 None vs ALMGuard WER 비교

제외 대상:

- Table 1의 나머지 공격인 Gupta et al., ICA, PAP-Audio
- Qwen2-Audio 외 다른 ALM 모델
- Table 2의 RQS
- AIR-Bench-Chat 전체 평가

## 2. AI 코딩 툴 활용 방식

본 구현 과정에서는 Cursor를 다음 용도로 활용하였다.

- ZIP 내부 코드 구조 확인
- README와 논문 표 기준 재현 범위 설정
- 공식 코드의 실행 오류 탐지
- 누락된 인자와 import 수정
- baseline 평가 스크립트 생성
- Qwen2-Audio 및 SorryBench judge model 실행 흐름 정리
- full SAP 학습 명령 구성
- response 생성과 SRoA 채점 분리
- WER 평가 실행
- 최종 실험 결과 정리
- 교수님이 다른 경로에서 실행할 수 있도록 재현 매뉴얼 작성
- 프롬프트 로그 문서화

AI 코딩 툴은 단순 코드 작성뿐 아니라, 실제 터미널 실행 결과를 기반으로 오류 원인을 추적하고 다음 실행 단계를 제안하는 방식으로 사용하였다.

## 3. 오픈소스 구조 분석

압축 해제 후 주요 파일과 폴더는 다음과 같다.

| 경로 | 역할 |
| --- | --- |
| `README.md` | 공식 실행 설명 |
| `main.py` | ALMGuard SAP 학습 |
| `eval_qwen.py` | ALMGuard 적용 후 Qwen2-Audio jailbreak response 생성 및 SRoA 평가 |
| `eval_asr.py` | ALMGuard 적용 후 ASR WER 평가 |
| `eval.py` | 저장된 response에 대한 attack performance 평가 |
| `llm_evaluation.py` | SorryBench judge model 기반 SRoA 채점 |
| `utils.py` | audio loading, embedding 병합, WER/CER 계산 등 유틸리티 |
| `datasets/` | AdvBench-Audio, LibriSpeech metadata 및 일부 audio |
| `results/` | AdvWave, AdvWave-P, PAIR-Audio 공격 audio |
| `mask/global_saliency.npz` | M-GSM saliency mask |
| `whisper/` | Whisper 모델 로딩 코드 |
| `AIR-bench/` | AIR-Bench-Chat 평가 코드 |

공개 ZIP 기준 실제 샘플 수는 다음과 같았다.

| 데이터 | 실제 WAV 수 |
| --- | ---: |
| `datasets/advbench_audios` | 100 |
| `datasets/librispeech_audios` | 19 |
| `results/advwave_suffix` | 19 |
| `results/advwave_p` | 20 |
| `results/pair_audio` | 20 |

이 점은 논문 전체 평가셋과 공개 ZIP 평가셋이 다를 수 있음을 의미한다.

## 4. 구현 중 발견한 문제와 수정 사항

공식 코드 그대로 실행하기에는 몇 가지 문제가 있었다. Cursor를 이용해 코드를 읽고 실행 오류를 확인한 뒤 다음과 같이 보강하였다.

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| `main.py` | `argparse` import 추가 | parser를 사용하지만 import가 없어서 실행 오류 발생 |
| `main.py` | `--prefix` 인자 추가 | 저장 파일명에서 `args.prefix`를 참조하지만 parser에 정의되어 있지 않음 |
| `main.py` | `torch_dtype=torch.float16` 지정 | Qwen2-Audio 7B를 48GB GPU에서 안정적으로 로드하기 위함 |
| `main.py` | `--max_iter`, `--max_train_samples` 추가 | smoke test를 빠르게 수행하기 위함 |
| `eval_qwen.py` | `perturb=None` 처리 추가 | None baseline 추론에 재사용하기 위함 |
| `eval_qwen.py` | `--skip_scoring` 추가 | response 생성과 SorryBench SRoA 채점을 분리하기 위함 |
| `eval_qwen_baseline.py` | 신규 생성 | 공식 코드에 None baseline 전용 script가 없어 추가 |
| `eval_asr.py` | 존재하는 WAV만 평가하도록 수정 | JSON에는 500개가 있으나 ZIP에는 19개 WAV만 존재 |
| `eval_asr_baseline.py` | 신규 생성 | None WER 평가를 위해 추가 |
| `score_responses.py` | 신규 생성 | 저장된 response `.pkl`만 별도 SRoA 채점하기 위해 추가 |
| `llm_evaluation.py` | SorryBench HF gated repo fallback 추가 | 로컬 judge model이 없을 때 Hugging Face에서 로드하기 위함 |
| `test_qwen_load.py` | 신규 생성 | Qwen2-Audio 로딩 가능 여부를 사전 확인하기 위함 |

## 5. 순차적 구현 매뉴얼

아래는 최종적으로 정리한 실행 순서이다. GitHub에서 받은 경우 먼저 `OpenSource/ALMGuard-main`으로 이동하고, 모든 명령은 이 repo 루트에서 실행한다.

```bash
cd OpenSource/ALMGuard-main
```

### 5.1 환경 생성

```bash
conda create -n ALMGuard python=3.10
conda activate ALMGuard
pip install -r requirements.txt
```

GPU 확인:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

### 5.2 Hugging Face 접근 설정

Qwen2-Audio와 SorryBench judge model 접근이 필요하다.

필요한 모델:

```text
Qwen/Qwen2-Audio-7B
sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406
```

SorryBench judge model은 gated model이므로 Hugging Face에서 접근 승인을 받은 뒤 token을 설정한다.

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

주의: 실제 token은 보고서나 GitHub에 포함하지 않는다.

### 5.3 Qwen2-Audio 로딩 확인

```bash
python test_qwen_load.py
```

예상 출력:

```text
Qwen2-Audio loaded successfully.
CUDA available: True
GPU: NVIDIA RTX A6000
```

### 5.4 Whisper-large-v3 준비

```bash
mkdir -p models
python -c "import os, whisper; os.makedirs('models', exist_ok=True); print(whisper._download(whisper._MODELS['large-v3'], 'models', False))"
```

예상 output:

```text
models/large-v3.pt
```

### 5.5 데이터 확인

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

### 5.6 SAP smoke test

긴 학습 전, 작은 샘플로 전체 학습 루프가 정상 동작하는지 확인한다.

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

예상 output 파일:

```text
results/prot_qwen_smoke/perturb_mel_epoch_0_iter_0.pth
results/prot_qwen_smoke/perturb_mel_epoch_0_iter_1.pth
results/prot_qwen_smoke/perturb_mel_epoch_0_iter_2.pth
```

### 5.7 full SAP 학습

논문 표와 비교할 최종 perturbation 생성을 위해 full SAP 학습을 수행한다.

```bash
python main.py \
  --save_path ./results/prot_qwen_full \
  --wav_dirs ./results/advwave_p ./results/advwave_suffix ./results/pair_audio \
  --num_epochs 1 \
  --model_path Qwen/Qwen2-Audio-7B \
  --asr_path ./models/large-v3.pt \
  --prefix qwen_full
```

실제 output:

```text
results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth
results/prot_qwen_full/records_qwen_full_0502.pkl
results/prot_qwen_full/responses_qwen_full_0502.pkl
```

### 5.8 None baseline response 생성

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

output 파일:

```text
results/repro_advwave_none/responses_eval_none_qwen.pkl
results/repro_advwave_p_none/responses_eval_none_qwen.pkl
results/repro_pair_audio_none/responses_eval_none_qwen.pkl
```

### 5.9 ALMGuard response 생성

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

output 파일:

```text
results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl
results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl
results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl
```

### 5.10 SRoA 채점

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_none/responses_eval_none_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_p_none/responses_eval_none_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_pair_audio_none/responses_eval_none_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl

env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN python score_responses.py \
  --response_path ./results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl
```

출력 예:

```text
Total: 20
Response file: ./results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl
SRoA = 0.150000
```

`SRoA = 0.150000`은 논문 표와 비교할 때 `15.0%`로 변환한다.

### 5.11 WER 계산

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

출력 예:

```text
WER = 0.629574
```

## 6. 최종 실험 결과

### 6.1 Table 1 일부 재현: Qwen2-Audio SRoA

| Attack | Paper None | Paper ALMGuard | Our None | Our ALMGuard |
| --- | ---: | ---: | ---: | ---: |
| AdvWave | 86.4 | 3.1 | 0.0 | 0.0 |
| AdvWave-P | 80.8 | 11.7 | 0.0 | 0.0 |
| PAIR-Audio | 45.0 | 34.9 | 5.0 | 15.0 |
| Average | 70.7 | 16.6 | 1.7 | 5.0 |

### 6.2 Table 2 일부 재현: Qwen2-Audio WER

| Setting | Paper WER | Our WER |
| --- | ---: | ---: |
| Qwen2-Audio None | 6.85 | 46.28 |
| Qwen2-Audio + ALMGuard | 8.70 | 62.96 |

## 7. 논문 결과와 차이가 나는 이유 분석

실험 파이프라인은 끝까지 실행되었지만, 수치가 논문과 크게 다르게 나왔다. 주요 원인은 다음과 같이 분석된다.

1. 공개 ZIP 샘플 수가 논문 전체 평가셋과 다르다.
   - 논문은 더 큰 평가셋을 사용하지만, 공개 ZIP에는 일부 샘플만 포함되어 있다.
   - 이번 재현에서는 AdvWave 19개, AdvWave-P 20개, PAIR-Audio 20개만 평가했다.

2. 공격 audio subset이 논문 내부 실험과 다를 가능성이 있다.
   - Our None SRoA가 논문 None보다 지나치게 낮게 나왔다.
   - 이는 공개 공격 audio가 논문 Table 1에서 사용한 전체 공격 성공 샘플과 동일하지 않을 수 있음을 의미한다.

3. Qwen2-Audio 응답 형식과 평가 script 차이가 있다.
   - Qwen2-Audio가 `Audio 1:`, `Assistant:` 등 부가 텍스트를 생성하는 경우가 있었다.
   - SorryBench judge와 WER 계산이 이러한 문자열에 영향을 받을 수 있다.

4. WER transcript extraction이 정교하지 않다.
   - `eval_asr.py`는 응답에서 transcript를 단순 추출한다.
   - `Audio 1:` 같은 prefix나 punctuation이 섞이면 WER가 논문보다 커질 수 있다.

5. Table 2의 RQS는 이번 범위에서 제외되었다.
   - RQS는 AIR-Bench-Chat 별도 평가가 필요하다.
   - 이번 실험은 Table 2 중 WER만 재현했다.

## 8. AI 코딩 툴 활용 분석

Cursor를 사용하면서 유용했던 점은 다음과 같다.

- 공식 코드의 누락된 인자와 import를 빠르게 찾을 수 있었다.
- 실행 오류를 터미널 로그 기반으로 분석하고 수정할 수 있었다.
- Qwen2-Audio, Whisper, SorryBench judge model처럼 여러 외부 모델이 얽힌 실행 흐름을 단계별로 정리할 수 있었다.
- None baseline처럼 공식 repo에 없는 평가 스크립트를 기존 코드 패턴에 맞게 생성할 수 있었다.
- 장시간 GPU 작업을 중간 checkpoint 기준으로 관리하고, response 생성과 채점을 분리할 수 있었다.
- 최종 보고서와 재현 매뉴얼을 코드 실행 결과와 연결해 문서화할 수 있었다.

한계점은 다음과 같다.

- AI가 제안한 실행 명령도 실제 모델 권한, GPU 메모리, 데이터 존재 여부에 따라 실패할 수 있으므로 반드시 검증이 필요하다.
- gated model 접근, token precedence, Hugging Face 환경변수 문제는 실제 실행 로그를 확인해야 해결 가능했다.
- 논문 내부 평가셋과 공개 ZIP 샘플 차이는 AI 도구만으로 완전히 보정할 수 없다.

## 9. 최종 산출물

보고서 및 로그:

- `CAPSTONE_AI_CODING_REPORT_KR.md`
- `PROMPTS.md`
- `FINAL_REPRODUCTION_REPORT_KR.md`
- `REPRODUCTION_KR.md`
- `EXPERIMENT_RESULTS_KR.md`

실험 산출물:

- `results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth`
- `results/repro_advwave_none/responses_eval_none_qwen.pkl`
- `results/repro_advwave_p_none/responses_eval_none_qwen.pkl`
- `results/repro_pair_audio_none/responses_eval_none_qwen.pkl`
- `results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl`
- `results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl`
- `results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl`

## 10. 결론

본 과제에서는 Cursor AI 코딩 툴을 활용하여 ALMGuard 오픈소스를 실행 가능한 형태로 보강하고, Qwen2-Audio 기준 Table 1 일부와 Table 2 WER 항목을 부분 재현하였다.

공식 코드의 실행 오류를 수정하고, baseline script와 response scoring script를 추가하여 공개 ZIP만으로도 재현 절차를 수행할 수 있도록 구성하였다. 최종 수치는 논문과 차이가 있었지만, 이는 공개 평가셋 규모, response parsing, 공격 audio subset 차이에 기인한 것으로 분석된다.

결과적으로 본 작업은 논문 수치의 완전 동일 재현보다는, 공개 오픈소스 코드의 실행 가능성 검증, 평가 파이프라인 복원, AI 코딩 도구를 활용한 구현/분석 과정을 보여주는 캡스톤디자인 과제 목적에 부합한다.
