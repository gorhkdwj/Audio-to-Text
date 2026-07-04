# Decisionlog · Audio_to_Text

방향을 바꾸거나 이후 작업에 영향을 주는 **중요한 결정만** 기록한다. 사소한 수정은 Worklog에만 남긴다. (규칙: CLAUDE.md 11절)

## 기록 형식
```
### D-00N · 결정 제목
**상황** / **검토한 선택지** / **결정** / **근거** / **영향** / **재검토 조건**
```

---

### D-001 · STT 엔진·인터페이스·범위 확정
**상황**
- 동영상/오디오를 텍스트로 추출하는 신규 프로젝트. 셋업 전 `PLAN.md`에서 사용자와 방향을 확정함.

**검토한 선택지**
- STT: 클라우드 API(유료·온라인) vs 로컬 Whisper(무료·오프라인)
- 인터페이스: CLI vs GUI
- 미디어 디코딩: FFmpeg 설치 vs faster-whisper 내장 PyAV

**결정**
- STT = 로컬 faster-whisper, 인터페이스 = CLI, 언어 = 한국어 위주(auto 지원), 출력 = txt·md·srt + 화자 구분(선택), 디코딩 = PyAV(FFmpeg 미설치).

**근거**
- 무료·오프라인·프라이버시. RTX 4090으로 large-v3 GPU 추론 가능. PyAV로 FFmpeg 설치 부담 제거.

**영향**
- ctranslate2의 CUDA 12 + cuDNN 9 DLL 의존성 관리 필요(리스크). 화자 구분은 pyannote 게이트 모델 → HuggingFace 토큰 필요.

**재검토 조건**
- GPU DLL 문제로 GPU 사용이 반복 실패하거나, 화자 구분 품질/설치 부담이 과도할 경우 범위 재조정.

### D-002 · 코드 배치 구조 결정 (src/ 대신 패키지)
**상황**
- 표준 셋업 구조는 `src/`를 두지만, PLAN.md는 루트 `audio_to_text/` 패키지 + `transcribe.py` 진입점을 사용.

**검토한 선택지**
- (a) `src/audio_to_text/` 로 이동 vs (b) PLAN.md대로 루트 패키지 유지

**결정**
- (b) 루트 `audio_to_text/` 패키지 + `transcribe.py` 유지. `src/` 폴더는 만들지 않음.

**근거**
- 파이썬 CLI에서 관용적이고 `python transcribe.py`로 바로 실행하기 쉬움. 이미 설계·합의된 구조.

**영향**
- CLAUDE.md 3절에 "`src/` 역할은 `audio_to_text/` 패키지가 대신함"을 명시.

**재검토 조건**
- 배포(pip 패키징)를 정식화할 때 `src/` 레이아웃 재검토.
