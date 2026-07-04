# Audio_to_Text

> 동영상/오디오 파일의 음성을 인식해 txt·md·srt 텍스트로 추출하는 한국어 중심 CLI 도구

## 개요
- 목적: mp4·mkv·mp3·wav 등 미디어 파일에서 음성을 글자로 변환(STT)한다.
- 주요 사용자: 본인(개발자)이 명령줄에서 직접 실행하는 도구.
- 최종 산출물: CLI 자동화 도구 (`python transcribe.py <입력> [옵션]`)
- STT 엔진: 로컬 Whisper(faster-whisper) — 무료·오프라인. NVIDIA GPU가 있으면 최고 품질 모델(large-v3) 사용.

## 실행 방법
> ⚠️ 아직 구현 전입니다. 코드가 완성되면 실제 동작하는 명령만 이 섹션에 채웁니다.
> (실제 구현된 기능만 기재하는 것이 규칙입니다 — `CLAUDE.md` 8절)

계획된 인터페이스(설계 기준, `PLAN.md` 참조):
```
python transcribe.py <파일_또는_폴더> [옵션]
  --format txt|md|srt   출력 형식(복수 지정 가능, 기본 md)
  --model NAME          Whisper 모델(기본 auto)
  --language ko|auto    음성 언어(기본 ko)
  --no-timestamps       타임스탬프 생략
  --diarize             화자 구분(추가 설치 + HuggingFace 토큰 필요)
```

## 프로젝트 구조
- `transcribe.py` — 진입점(구현 예정)
- `audio_to_text/` — 실행 코드 패키지(구현 예정, `src/` 역할)
- `tests/` — 테스트
- `tools/` — 개발·검증 보조 스크립트(예: 테스트 오디오 생성)
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
