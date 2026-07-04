# 동영상/오디오 → 텍스트 추출 CLI 프로그램 설계

## Context

동영상 또는 오디오 파일을 입력하면 음성을 인식해 txt/md(및 srt) 파일로 텍스트를 추출하는 프로그램을 새로 만든다. 빈 디렉터리(`C:\Users\gorhk\Playground\1.programs\0.Audio_to_Text`)에서 시작하는 신규 프로젝트다.

**사용자 결정 사항:**
- STT 방식: **로컬 Whisper** (faster-whisper, 무료·오프라인)
- 인터페이스: **CLI 도구**
- 주요 언어: **한국어 위주** (자동 감지도 지원)
- 출력 요소: **타임스탬프 + 순수 텍스트 + SRT 자막 + 화자 구분** 모두 지원

**확인된 환경:**
- Python 3.10.8 / Windows 11
- NVIDIA RTX 4090 (24GB) → GPU로 최고 품질 모델(large-v3) 사용 가능
- FFmpeg 미설치 → faster-whisper의 내장 의존성 **PyAV**가 동영상/오디오 디코딩을 대신하므로 FFmpeg 설치 불필요

## 기술 스택

| 구성 요소 | 선택 | 이유 |
|---|---|---|
| STT 엔진 | faster-whisper | openai-whisper 대비 4배 이상 빠름, CUDA/CPU 모두 지원 |
| 미디어 디코딩 | PyAV (faster-whisper 의존성) | mp4/mkv 등 동영상에서 오디오 추출까지 처리, FFmpeg 설치 불필요 |
| 화자 구분 | pyannote.audio 3.1 + torch(CUDA) | 사실상 표준. **선택 기능**으로 분리(무거움 + HF 토큰 필요) |
| CLI | argparse (표준 라이브러리) | 의존성 최소화 |
| 진행률 | tqdm | 세그먼트 진행 상황 표시 |

## 프로젝트 구조

```
0.Audio_to_Text/
├── transcribe.py             # 진입점: python transcribe.py <입력> [옵션]
├── audio_to_text/
│   ├── __init__.py
│   ├── cli.py                # argparse 정의, 전체 파이프라인 오케스트레이션
│   ├── files.py              # 입력 수집(파일/폴더), 지원 확장자, 출력 경로 계산
│   ├── transcriber.py        # faster-whisper 래퍼 (모델 로드, GPU DLL 처리, 진행률)
│   ├── diarizer.py           # pyannote 래퍼 + 세그먼트-화자 매칭 (지연 import)
│   └── formatters.py         # txt / md / srt 생성
├── requirements.txt          # 기본 의존성 (faster-whisper, tqdm, GPU용 cuDNN/cuBLAS 휠)
├── requirements-diarize.txt  # 화자 구분용 추가 의존성 (torch CUDA, pyannote.audio)
├── .venv/                    # 가상환경
└── README.md                 # 설치·사용법 (한국어)
```

## CLI 설계

```
python transcribe.py <파일_또는_폴더> [추가입력 ...] [옵션]

옵션:
  --format txt|md|srt   출력 형식, 복수 지정 가능 (기본: md)
  --output-dir DIR      출력 폴더 (기본: 입력 파일과 같은 위치)
  --model NAME          Whisper 모델 (기본: auto → CUDA면 large-v3, CPU면 medium)
  --language LANG       음성 언어 (기본: ko, "auto"면 자동 감지)
  --no-timestamps       txt/md에서 [hh:mm:ss] 타임스탬프 생략 (순수 텍스트 모드)
  --diarize             화자 구분 활성화 (추가 설치 + HuggingFace 토큰 필요)
  --num-speakers N      화자 수 힌트 (선택)
  --device auto|cuda|cpu (기본: auto)
  --hf-token TOKEN      pyannote용 토큰 (기본: HF_TOKEN 환경변수)
  --overwrite           기존 출력 파일 덮어쓰기
```

지원 입력 확장자 — 오디오: mp3 wav m4a flac ogg opus aac wma / 동영상: mp4 mkv mov avi webm ts

## 처리 파이프라인

1. **입력 수집** (files.py): 폴더 입력 시 지원 확장자 파일만 재귀 수집, 출력 경로 충돌 검사
2. **디코딩**: `faster_whisper.decode_audio()` → 16kHz mono float32 파형 (동영상도 같은 경로로 처리)
3. **음성 인식** (transcriber.py): `WhisperModel.transcribe(language="ko", vad_filter=True, word_timestamps=srt·화자구분 시)` — 세그먼트 제너레이터를 순회하며 tqdm 진행률 표시 (`segment.end / 전체길이`)
4. **화자 구분** (diarizer.py, `--diarize` 시): 같은 파형을 torch tensor로 pyannote 파이프라인에 전달 → 화자 turn 목록 → 각 Whisper 세그먼트에 시간 겹침이 최대인 화자를 할당 (v1은 세그먼트 단위 매칭)
5. **출력** (formatters.py):
   - **txt**: `[00:01:23] 텍스트` (타임스탬프 모드) 또는 문단 단위 순수 텍스트. 화자 구분 시 `[00:01:23] 화자 1: 텍스트`
   - **md**: 제목(파일명) + 메타데이터 표(원본, 길이, 모델, 언어, 생성일) + 본문. 문단은 발화 간격(≥2초) 기준으로 병합, 화자는 `**화자 1:**` 굵게 표기
   - **srt**: 표준 자막 형식, 화자 구분 시 자막 텍스트 앞에 `화자 1:` 접두

## GPU(CUDA) 관련 처리 — 핵심 리스크

ctranslate2(faster-whisper 백엔드)는 Windows에서 CUDA 12 + cuDNN 9 DLL을 요구한다. 대응 전략:

1. requirements.txt에 `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` pip 휠 포함
2. transcriber.py에서 CUDA 사용 전 `os.add_dll_directory()`로 해당 패키지의 bin 폴더 등록 (torch가 설치돼 있으면 `import torch` 선행으로도 해결)
3. DLL 로드 실패 시 명확한 한국어 안내와 함께 **CPU(int8) 자동 폴백**

## 화자 구분 제약 (사용자 안내 필요)

- `pyannote/speaker-diarization-3.1`은 **게이트 모델**: HuggingFace 계정으로 모델 페이지에서 이용 약관 동의 + 액세스 토큰 필요 (`pyannote/segmentation-3.0`도 동일)
- 토큰은 `HF_TOKEN` 환경변수 또는 `--hf-token`으로 전달
- 미설치/토큰 없음 상태에서 `--diarize` 사용 시 설치·설정 방법을 안내하는 한국어 에러 메시지 출력

## 구현 단계

1. `.venv` 생성 → requirements.txt 작성·설치 (faster-whisper, tqdm, nvidia-cublas-cu12, nvidia-cudnn-cu12)
2. files.py, transcriber.py, formatters.py, cli.py, transcribe.py 구현 — 기본 변환(txt/md/srt + 타임스탬프) 완성
3. GPU 동작 확인 (large-v3, float16). DLL 문제 시 위 폴백 전략 적용
4. requirements-diarize.txt (torch cu124 인덱스, pyannote.audio) + diarizer.py + `--diarize` 연동
5. README.md 작성 (설치, 사용 예시, 화자 구분 설정법, 모델별 속도/품질 안내)

## 검증 방법

1. **테스트 오디오 생성**: PowerShell `System.Speech`(TTS)로 한국어(ko-KR 보이스 있으면) 또는 영어 WAV 생성. 화자 구분 테스트용으로는 서로 다른 두 보이스를 이어 붙인 WAV 생성
2. **테스트 동영상 생성**: PyAV로 WAV를 m4a/mp4 컨테이너로 변환해 동영상 입력 경로 검증
3. `python transcribe.py test.wav --format txt md srt` 실행 → 3개 출력 파일의 타임스탬프·내용 확인
4. 콘솔 로그로 GPU(cuda/float16) 사용 여부 확인, `--device cpu`로 CPU 폴백도 확인
5. 폴더 입력 일괄 처리, `--no-timestamps`, `--overwrite` 동작 확인
6. `--diarize`: HF 토큰이 준비되면 2-보이스 테스트 파일로 화자 라벨 확인. 토큰이 없으면 안내 메시지 출력까지 확인 (토큰 발급은 사용자 작업)

## 범위 제외 (추후 확장 후보)

- GUI(드래그 앤 드롭), 실시간 마이크 입력, 번역 기능, 클라우드 API 모드
