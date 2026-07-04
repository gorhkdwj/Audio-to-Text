# Audio_to_Text

> 동영상/오디오 파일의 음성을 인식해 txt·md·srt 텍스트로 추출하는 한국어 중심 CLI 도구

## 개요
- 목적: mp4·mkv·mp3·wav 등 미디어 파일에서 음성을 글자로 변환(STT)한다.
- 주요 사용자: 본인(개발자)이 명령줄에서 직접 실행하는 도구.
- STT 엔진: 로컬 Whisper(faster-whisper) — 무료·오프라인. FFmpeg 설치 불필요(내장 PyAV가 디코딩).
- GPU: NVIDIA GPU가 있으면 최고 품질 모델(large-v3)을 자동 사용, 불가하면 CPU로 자동 폴백.

## 설치
```
# Python 3.10 이상 필요
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## 사용법
```
.venv\Scripts\python transcribe.py <파일_또는_폴더> [추가입력 ...] [옵션]
```

예시:
```
# 기본: md 파일 생성 (입력 파일과 같은 위치)
.venv\Scripts\python transcribe.py 강의.mp4

# 세 형식 모두 + 출력 폴더 지정
.venv\Scripts\python transcribe.py 회의.wav --format txt md srt --output-dir out

# 폴더 일괄 처리 (하위 폴더 구조를 출력 폴더에 그대로 재현)
.venv\Scripts\python transcribe.py 녹음폴더 --format srt --output-dir out
```

옵션:
| 옵션 | 설명 |
|---|---|
| `--format txt md srt` | 출력 형식, 복수 지정 가능 (기본: md) |
| `--output-dir DIR` | 출력 폴더 (기본: 입력 파일과 같은 위치) |
| `--model NAME` | Whisper 모델 (기본: auto → GPU면 large-v3, CPU면 medium) |
| `--language LANG` | 음성 언어 (기본: ko, `auto`면 자동 감지) |
| `--no-timestamps` | txt/md에서 `[HH:MM:SS]` 타임스탬프 생략 |
| `--device auto\|cuda\|cpu` | 추론 장치 (기본: auto) |
| `--overwrite` | 기존 출력 파일 덮어쓰기 (없으면 건너뜀) |
| `--diarize` | 화자 구분 — 선택 기능, 추가 설치 + HuggingFace 토큰 필요 |
| `--num-speakers N` | 화자 수 힌트 (`--diarize`와 함께) |
| `--hf-token TOKEN` | pyannote용 토큰 (기본: `HF_TOKEN` 환경변수) |

종료 코드: `0` 전체 성공(건너뜀 포함) / `1` 일부 파일 실패 / `2` 인자·입력 오류

## 화자 구분(--diarize) 사용법
2인 이상 대화에서 발화자별로 `화자 1:`, `화자 2:` 라벨을 붙인다. 최초 1회 준비:
1. 추가 패키지 설치: `.venv\Scripts\python -m pip install -r requirements-diarize.txt` (torch CUDA 포함, 수 GB)
2. HuggingFace 계정으로 두 게이트 모델 약관 동의: [speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1), [segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
3. [액세스 토큰](https://huggingface.co/settings/tokens)(Read 권한) 발급 후 `HF_TOKEN` 환경변수로 등록

```
.venv\Scripts\python transcribe.py 회의.wav --format txt srt --diarize [--num-speakers 2]
```
화자 번호는 먼저 말한 순서대로 붙는다. 준비가 안 된 상태에서 `--diarize`를 쓰면 안내 후 화자 구분 없이 텍스트 변환만 계속한다.

> ⚠️ 한 파일에 여러 언어가 섞이면 Whisper가 한 언어로만 디코딩해 다른 언어 발화가 누락될 수 있다. 화자 구분은 같은 언어로 진행된 대화에 사용을 권장한다.
> ⚠️ 회사명·제품명·인명 같은 고유명사는 오인식될 수 있다. 중요한 문서는 고유명사를 검토하기를 권장한다.

## 검증 상태 (정직하게)
- ✅ 기본 변환(txt/md/srt), GPU(RTX 4090, large-v3, float16), CPU 폴백, 건너뜀·덮어쓰기 — 실측 검증 완료
- ✅ 폴더 일괄 + 하위 구조 미러링, `--no-timestamps`, `--language auto`, 무음 파일 처리, 종료 코드 0·1·2 — 실측 검증 완료
- ✅ 컨테이너 실측: 오디오 wav·mp3·m4a / 동영상 mp4·mkv·mov·webm·ts (flac·ogg·opus·aac·wma·avi는 PyAV 지원 범위이나 미실측)
- ✅ 화자 구분(`--diarize`, `--num-speakers`): 2인 영어 대화 파일에서 라벨 분리·첫 등장 순서 번호 실측 검증 완료 (3인 이상·장시간 파일은 미실측)

## 지원 입력 확장자
- 오디오: mp3 wav m4a flac ogg opus aac wma
- 동영상: mp4 mkv mov avi webm ts

## 프로젝트 구조
- `transcribe.py` — 진입점
- `audio_to_text/` — 실행 코드 패키지 (cli / files / transcriber / formatters / diarizer)
- `tests/` — 단위 테스트 (`.venv\Scripts\python -m unittest discover -s tests`)
- `tools/` — 테스트 오디오(TTS)·동영상 생성 스크립트
- `docs/` — 기획·기준 계약·구현·검증 문서
- `out/` — 실행 결과·변환 산출물 (Git 제외)

## 문서
- 초기 설계: `PLAN.md`
- 작업 규칙: `CLAUDE.md`
- 프로젝트 기획: `docs/project-plan.md`
- 기준 계약: `docs/requirements-contract.md`
- 구현 계획: `docs/implementation-plan.md`
- 검증 계획: `docs/validation-plan.md`
- 작업 이력: `Worklog.md`
- 주요 결정: `Decisionlog.md`
- 문제 해결: `Troubleshootinglog.md`
