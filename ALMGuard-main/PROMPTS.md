# PROMPTS.md

이 문서는 ALMGuard 오픈소스 구현 및 부분 재현 과정에서 Cursor AI 코딩 툴에 입력한 주요 프롬프트와 그에 따른 작업 내용을 정리한 프롬프트 로그이다. 실제 대화 내용을 제출용으로 정리한 것이며, Hugging Face token 등 민감 정보는 포함하지 않는다.

## Prompt 1. 오픈소스 재현 목표 설정

### 입력 프롬프트

```text
https://github.com/WeifeiJin/ALMGuard 이 링크에 있는 오픈소스를 그대로 재현해서, 바로 실행가능하도록 만드는게 목표야.
GitHub 제출 기준으로는 `OpenSource/ALMGuard-main.zip`에 원본 ZIP을 두고, `OpenSource/ALMGuard-main/`에서 압축 해제된 코드를 실행하는 형태로 정리할 거야.

이제부터는 “PPT에 넣을 최종 재현 범위” 기준으로 ALMGuard를 어떻게 실행할지 정리하면 돼.

목표 재현:
1. Table 1 / Table 3 일부 재현
   - Qwen2-Audio에서 AdvWave, AdvWave-P, PAIR-Audio에 대해 None vs ALMGuard SRoA 비교
2. Table 2 일부 재현
   - Qwen2-Audio에서 LibriSpeech 샘플에 대해 ALMGuard 적용 후 WER 측정
```

### AI 수행 내용

- ZIP 압축 해제
- repo 구조 확인
- `main.py`, `eval_qwen.py`, `eval_asr.py`, `eval.py`, `utils.py` 코드 분석
- 공식 README의 실행 절차와 실제 코드 차이 확인
- 데이터 및 공격 audio 폴더 존재 여부 확인
- 재현용 문서 초안 작성

### 산출물

```text
REPRODUCTION_KR.md
```

## Prompt 2. 데이터 확인 실행

### 입력 프롬프트

```text
이제 직접 실행해보고싶어.
REPRODUCTION_KR.md에 있는 내용대로 실행해보자.
```

### AI 수행 내용

- `datasets/advbench_audios`
- `datasets/librispeech_audios`
- `results/advwave_suffix`
- `results/advwave_p`
- `results/pair_audio`
- `mask/global_saliency.npz`

위 경로의 파일 수를 확인하였다.

### 확인 결과

```text
datasets/advbench_audios: 100 wav files
datasets/librispeech_audios: 19 wav files
results/advwave_suffix: 19 wav files
results/advwave_p: 20 wav files
results/pair_audio: 20 wav files
mask/global_saliency.npz: True
```

## Prompt 3. 환경 생성과 모델 로딩

### 입력 프롬프트

```text
이제 2번~4번 진행해보자.
```

### AI 수행 내용

- `conda create -n ALMGuard python=3.10`
- `pip install -r requirements.txt`
- GPU 확인
- `test_qwen_load.py` 생성
- Qwen2-Audio 로딩 확인
- Whisper-large-v3 checkpoint 다운로드

### 산출물

```text
test_qwen_load.py
models/large-v3.pt
```

### 확인 결과

```text
torch 2.2.2+cu121
cuda True
GPU: NVIDIA RTX A6000
Qwen2-Audio loaded successfully.
```

## Prompt 4. SAP 학습 및 병렬 실험 진행

### 입력 프롬프트

```text
이제 5번부터 쭉 진행해줘.
실험을 여러개해야하면, 병렬적으로 다른 가용 GPU 병렬적으로 나눠서 실험하면 될거같아.
```

### AI 수행 내용

- `main.py` 실행 전 오류 가능성 점검
- `argparse` import 누락 수정
- `--prefix` 인자 추가
- Qwen2-Audio 로딩을 `torch.float16`으로 변경
- smoke test용 `--max_iter`, `--max_train_samples` 인자 추가
- SAP smoke test 실행
- full SAP 학습 시작
- None baseline response 생성
- 중간 checkpoint 기준 ALMGuard response 및 WER 실험 수행

### 수정 파일

```text
main.py
eval_qwen.py
eval_qwen_baseline.py
eval_asr.py
eval_asr_baseline.py
```

### 주요 산출물

```text
results/prot_qwen_smoke/perturb_mel_epoch_0_iter_*.pth
results/prot_qwen_full/perturb_mel_epoch_0_iter_*.pth
```

## Prompt 5. SorryBench gated model 문제 해결

### 입력 프롬프트

```text
huggingface에 들어가서 gated 허용해줬고, 내 토큰은 준비했어.
이제 논문 방식대로 채점할 수 있겠지?
```

### AI 수행 내용

- SorryBench judge model 경로 확인
- `llm_evaluation.py`에서 로컬 model이 없으면 Hugging Face gated repo를 사용하도록 수정
- 기존 서버 환경의 invalid `HF_TOKEN`이 우선 적용되어 `401 Unauthorized`가 발생하는 문제 확인
- `env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN` 방식으로 저장된 login token을 사용하도록 해결
- `score_responses.py` 생성

### 수정 및 생성 파일

```text
llm_evaluation.py
score_responses.py
```

### 검증 결과

```text
Response file: ./results/repro_advwave_none/responses_eval_none_qwen.pkl
SRoA = 0.000000
```

## Prompt 6. 최종 재현 범위 결정

### 입력 프롬프트

```text
그러면 Table1+WER까지 비교하는걸로 할게.
```

### AI 수행 내용

- 최종 재현 범위를 Table 1 일부 + Table 2 WER로 확정
- RQS는 AIR-Bench-Chat 별도 평가가 필요하므로 제외
- full SAP 학습 완료 후 final perturbation을 사용하는 방식으로 실험 계획 정리

### 최종 범위

```text
Table 1:
- AdvWave None vs ALMGuard SRoA
- AdvWave-P None vs ALMGuard SRoA
- PAIR-Audio None vs ALMGuard SRoA

Table 2:
- Qwen2-Audio None WER
- Qwen2-Audio + ALMGuard WER
```

## Prompt 7. full SAP 학습 완료 후 최종 실험

### 입력 프롬프트

```text
이제 full SAP 학습이 완료된것 같아. 다음 단계로 넘어가자.
```

### AI 수행 내용

- full SAP 학습 종료 확인
- 최종 checkpoint 확인
- 최종 perturbation으로 세 공격의 ALMGuard response 생성
- final ALMGuard WER 계산
- None baseline과 ALMGuard response를 SorryBench judge로 SRoA 채점

### 최종 perturbation

```text
results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth
```

### 최종 response 파일

```text
results/repro_advwave_none/responses_eval_none_qwen.pkl
results/repro_advwave_p_none/responses_eval_none_qwen.pkl
results/repro_pair_audio_none/responses_eval_none_qwen.pkl

results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl
results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl
results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl
```

## Prompt 8. 최종 결과 문서화

### 입력 프롬프트

```text
현재 진행한 실험에 대한 설명 + 해당 실험에 대한 결과 + 논문의 어느 table 항목과 비교가능한지,
어떤 점에 차이가 있는 지 등을 전부 포함해줘.
```

### AI 수행 내용

- 실행 가이드와 실험 결과를 통합
- 논문 Table 1 / Table 2와의 대응 관계 작성
- 실행 순서 요약 추가
- output 파일 경로 정리
- 결과 해석 및 한계점 분석

### 산출물

```text
FINAL_REPRODUCTION_REPORT_KR.md
EXPERIMENT_RESULTS_KR.md
```

## Prompt 9. 제출용 보고서와 프롬프트 로그 생성

### 입력 프롬프트

```text
Cursor, AI코딩 tool을 이용하여 캡스톤디자인 프로젝트 진행에 도움이 될 수 있는 보고서 제출과제를 진행해보고자 합니다.
타겟논문의 오픈소스 코드 구현 및 분석 과제를 AI 코딩 툴을 이용하여 구현해보고자 합니다.

타겟 오픈소스: OpenSource 폴더 구현 과정에 대한 내용.
다음을 정리해서 이 오픈소스를 구현하기 위한 과정에 대한 내용을 생성해주세요.
- 보고서(순차적 구현 매뉴얼, 프롬프트 입력 내용 등 분석 내용 포함)
- 프롬프트 로그(PROMPTS.md 파일)
```

### AI 수행 내용

- 기존 재현 문서와 실험 결과 문서를 종합
- 캡스톤 제출용 보고서 생성
- AI 코딩 툴 활용 과정 분석
- 주요 프롬프트 입력 내용과 AI 수행 결과를 로그 형식으로 정리

### 산출물

```text
CAPSTONE_AI_CODING_REPORT_KR.md
PROMPTS.md
```

## 최종 결과 요약

### Table 1 일부 재현

| Attack | Paper None | Paper ALMGuard | Our None | Our ALMGuard |
| --- | ---: | ---: | ---: | ---: |
| AdvWave | 86.4 | 3.1 | 0.0 | 0.0 |
| AdvWave-P | 80.8 | 11.7 | 0.0 | 0.0 |
| PAIR-Audio | 45.0 | 34.9 | 5.0 | 15.0 |
| Average | 70.7 | 16.6 | 1.7 | 5.0 |

### Table 2 WER 일부 재현

| Setting | Paper WER | Our WER |
| --- | ---: | ---: |
| Qwen2-Audio None | 6.85 | 46.28 |
| Qwen2-Audio + ALMGuard | 8.70 | 62.96 |

## 프롬프트 사용 분석

이번 구현에서 프롬프트는 다음 역할을 수행했다.

- 재현 목표 정의
- 공식 코드 구조 분석 요청
- 실행 단계별 진행 요청
- 오류 해결 요청
- 실험 범위 조정
- 결과 해석 요청
- 최종 보고서 생성 요청

Cursor의 응답은 단순 코드 생성이 아니라, 실제 명령 실행과 파일 수정, 로그 분석, 결과 문서화까지 포함하는 반복적 구현 보조 역할을 수행했다.
