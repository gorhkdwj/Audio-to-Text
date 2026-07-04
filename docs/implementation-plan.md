# 구현 계획 · Audio_to_Text

> 처음부터 전체를 달리지 않는다. 가장 작은 성공 단위부터. 각 단계는 완료 조건과 검증 방법을 명시한다. (상세 설계: `PLAN.md`)

## 진행 상태 (2026-07-04 기준)
- ✅ **S0 완료** (W-005) · ✅ **S1 완료** (W-006) · ✅ **S2 완료** (W-007, T-001 해결)
- ⬜ S3(옵션·폴더 E2E) · ⬜ S4(화자 구분 실측) · ⬜ S5(문서 최종 정리)
- S4는 HuggingFace 토큰 발급(**사용자 작업**)이 선행되어야 한다. 잔여 미검증 항목은 `docs/validation-plan.md`의 "미검증 범위" 참조.

## 단계 개요
| 단계 | 목표 | 완료 조건 | 검증 방법 | 의존/연결 |
|------|------|-----------|-----------|-----------|
| S0 | 환경·의존성 준비 | `.venv` + requirements.txt 설치 성공 | `import faster_whisper` 성공 | - |
| S1 | 기본 변환(txt·md·srt + 타임스탬프) | 오디오 1개 → 3형식 출력 생성 | TTS 테스트 오디오로 내용/포맷 확인 | S0 |
| S2 | GPU 동작 및 DLL 폴백 | large-v3 GPU 추론 또는 CPU 자동 폴백 | 콘솔 로그로 device/precision 확인, --device cpu 확인 | S1 |
| S3 | 폴더 일괄·옵션 | 폴더 입력, --no-timestamps, --overwrite 동작 | 각 옵션 실제 실행 확인 | S1 |
| S4 | 화자 구분(--diarize) | 2-보이스 파일에서 화자 라벨 분리 | HF 토큰 준비 시 실측, 없으면 안내 메시지 확인 | S1 |
| S5 | README·문서 정리 | 구현된 기능만 문서화, 문서-코드 일치 | README 명령을 그대로 실행해 재현 | S1~S4 |

## 단계 상세

### S0 · 환경·의존성 준비
- 왜 필요한가: faster-whisper/PyAV/GPU 휠이 있어야 시작 가능.
- 완료 조건: `.venv`에서 `faster-whisper`, `tqdm`, `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` 설치 및 import 성공.
- 검증 방법: 파이썬에서 `from faster_whisper import WhisperModel` 오류 없음.
- 실패 시 중단점: 휠 설치 실패 시 원인 기록(T-ID) 후 중단.

### S1 · 기본 변환
- 왜 필요한가: 프로젝트 핵심 가치(음성→텍스트).
- 이전 연결: S0 환경. 다음 전달: 세그먼트 리스트를 S2/S4가 재사용.
- 구현: files.py(입력 수집) → transcriber.py(faster-whisper 래퍼) → formatters.py(txt/md/srt) → cli.py/transcribe.py.
- 완료 조건: `python transcribe.py test.wav --format txt md srt`로 3파일 생성.
- 검증 방법: `tools/`의 TTS 생성 스크립트로 만든 "알고 있는 문장" 오디오로 결과 대조.
- 실패 시 중단점: 디코딩/추론 오류 시 원인 기록 후 중단.

### S2 · GPU 동작 및 DLL 폴백
- 왜 필요한가: 품질(large-v3)과 속도. Windows CUDA DLL 리스크 대응.
- 완료 조건: GPU 추론 성공 또는 DLL 실패 시 CPU(int8) 자동 폴백 + 한국어 안내.
- 검증 방법: 콘솔 로그로 cuda/float16 확인, `--device cpu`로 폴백 확인.
- 실패 시 중단점: 폴백조차 실패하면 중단·기록.

### S3 · 폴더 일괄·옵션
- 완료 조건: 폴더 재귀 수집, `--no-timestamps`, `--overwrite`, `--output-dir` 동작.
- 검증 방법: 폴더 입력 실행, 각 옵션 on/off 결과 비교.

### S4 · 화자 구분(--diarize)
- 왜 필요한가: 대화/회의 텍스트 가독성.
- 구현: requirements-diarize.txt(torch cu124, pyannote.audio) + diarizer.py(지연 import) + 세그먼트-화자 매칭.
- 완료 조건: 2-보이스 테스트 파일에서 화자 라벨 분리. 토큰 없으면 안내.
- 검증 방법: HF 토큰 준비 시 실측(토큰 발급은 사용자 작업), 없으면 안내 메시지 확인.
- 실패 시 중단점: 게이트 모델 접근 실패는 안내로 처리(전체 중단 아님).

### S5 · README·문서 정리
- 완료 조건: README에 실제 구현된 기능만 기재, 문서-코드 정합.
- 검증 방법: README의 명령을 그대로 실행해 재현되는지 확인.
