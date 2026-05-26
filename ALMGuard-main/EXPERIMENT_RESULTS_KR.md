# ALMGuard 재현 실행 결과

실행 기준:

- 최종 SAP checkpoint: `results/prot_qwen_full/perturb_mel_epoch_0_iter_56.pth`
- SRoA judge: `sorry-bench/ft-mistral-7b-instruct-v0.2-sorry-bench-202406`
- Qwen2-Audio: `Qwen/Qwen2-Audio-7B`
- 공개 ZIP 내 샘플 수: AdvWave 19개, AdvWave-P 20개, PAIR-Audio 20개, LibriSpeech 19개

## Table 1 일부 재현: Qwen2-Audio SRoA

`score_responses.py`는 0-1 fraction으로 출력하므로, 아래 표에는 논문과 맞추기 위해 `%`로 변환했습니다.

| Attack | Paper None | Paper ALMGuard | Our None | Our ALMGuard |
| --- | ---: | ---: | ---: | ---: |
| AdvWave | 86.4 | 3.1 | 0.0 | 0.0 |
| AdvWave-P | 80.8 | 11.7 | 0.0 | 0.0 |
| PAIR-Audio | 45.0 | 34.9 | 5.0 | 15.0 |
| Average | 70.7 | 16.6 | 1.7 | 5.0 |

Response / score inputs:

- None AdvWave: `results/repro_advwave_none/responses_eval_none_qwen.pkl`
- None AdvWave-P: `results/repro_advwave_p_none/responses_eval_none_qwen.pkl`
- None PAIR-Audio: `results/repro_pair_audio_none/responses_eval_none_qwen.pkl`
- ALMGuard AdvWave: `results/repro_advwave_almguard_final/responses_eval_prot_qwen.pkl`
- ALMGuard AdvWave-P: `results/repro_advwave_p_almguard_final/responses_eval_prot_qwen.pkl`
- ALMGuard PAIR-Audio: `results/repro_pair_audio_almguard_final/responses_eval_prot_qwen.pkl`

## Table 2 일부 재현: Qwen2-Audio WER

| Setting | Paper WER | Our WER |
| --- | ---: | ---: |
| Qwen2-Audio None | 6.85 | 46.28 |
| Qwen2-Audio + ALMGuard | 8.70 | 62.96 |

WER 실행 로그 기준:

- None WER: `0.462786`
- Final ALMGuard WER: `0.629574`

## 해석 시 주의점

- 공개 ZIP에는 논문 전체 평가셋이 아니라 일부 샘플만 들어 있어 표의 절대값과 직접 일치하기 어렵습니다.
- Our None SRoA가 논문 None보다 지나치게 낮게 나왔습니다. 이는 공개 공격 audio subset, Qwen2-Audio 응답 생성 방식, 공식 eval script의 prompt/audio 매칭 조건 차이 때문일 수 있어 response case를 함께 확인해야 합니다.
- WER도 논문보다 크게 높습니다. 현재 `eval_asr.py`는 Qwen2-Audio 응답에서 transcript를 단순 추출하므로 `Audio 1:` 같은 prefix가 섞이면 WER가 커질 수 있습니다.
- PPT에는 “공식 공개 ZIP 기반 부분 재현”과 “샘플 수 및 평가 스크립트 차이로 절대값 차이 존재”를 명시하는 것이 안전합니다.
