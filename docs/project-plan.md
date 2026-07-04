# 프로젝트 기획 · Audio_to_Text

> 상세 기술 설계는 루트 `PLAN.md`에 있다. 이 문서는 그 위의 기획 요약이다.

## 문제 정의
- 동영상/오디오 파일의 음성 내용을 사람이 직접 받아쓰지 않고, 자동으로 텍스트(txt·md·srt)로 추출하고 싶다.
- 온라인 업로드 없이(프라이버시), 무료로, 한국어를 잘 인식해야 한다.

## 목표와 성공 기준
- `python transcribe.py <파일>` 한 번으로 정확한 한국어 텍스트 파일이 생성된다.
- GPU(RTX 4090)에서 large-v3 모델로 동작하고, 문제가 있으면 CPU로 자동 폴백한다.
- txt(타임스탬프), md(메타데이터+문단), srt(자막) 3형식을 지원한다.
- (선택) 화자 구분으로 "화자 1/2"를 나눌 수 있다.

## 범위
- 포함: 로컬 STT(faster-whisper), CLI, 한국어 위주(auto 감지), txt·md·srt 출력, 폴더 일괄 처리, 타임스탬프 on/off, 화자 구분(선택 기능), GPU/CPU 자동 선택.
- 제외(추후 확장 후보): GUI/드래그앤드롭, 실시간 마이크 입력, 번역 기능, 클라우드 API 모드.

## 주요 사용자와 사용 시나리오
- 사용자: 본인(개발자). 강의·회의·인터뷰 녹음이나 동영상을 텍스트로 정리할 때 명령줄에서 실행.
- 시나리오: `python transcribe.py 회의.mp4 --format md srt` → 회의.md, 회의.srt 생성.

## 산출물
- CLI 자동화 도구(파이썬). 진입점 `transcribe.py` + `audio_to_text/` 패키지.
- 사용 설명 README(한국어), requirements.txt / requirements-diarize.txt.

## 일정·마일스톤
- 마감: 없음(개인 프로젝트).
- 주요 단계(상세는 `docs/implementation-plan.md`):
  - S1: 기본 변환(txt·md·srt + 타임스탬프)
  - S2: GPU 동작 확인 및 DLL 폴백
  - S3: 화자 구분(--diarize)
  - S4: README·문서 정리

## 리스크와 대응
- CUDA/cuDNN DLL 로드 실패 → nvidia pip 휠 + `os.add_dll_directory` + CPU 자동 폴백.
- pyannote 게이트 모델(HF 토큰 필요) → 미설정 시 친절한 한국어 안내.
- PyAV 디코딩 호환성 → 다양한 컨테이너로 테스트.
