# Worklog · Audio_to_Text

**모든 작업을 빠짐없이** 아래 형식으로 누적 기록한다. 규모가 작아도 생략하지 않는다. (규칙: CLAUDE.md 11절). 최신 항목을 위에 추가한다.

## 기록 형식
```
### W-00N · 작업 제목
**요청** / **수행 작업** / **변경 파일** / **검증** / **판단 근거** / **결과**
```

---

### W-012 · 사용법 안내 (초급자용)
**요청**
- 도구 사용 방법 설명 요청.

**수행 작업**
- 초급자 기준 사용 안내 제공: PowerShell 실행 → 프로젝트 폴더 이동 → `.venv\Scripts\python transcribe.py <파일>` 3단계, 자주 쓰는 명령 레시피(형식·화자 구분·폴더 일괄·overwrite), 출력 형식별 용도(md 읽기용/txt 인용용/srt 자막), 알려진 한계 재안내.
- 편의용 `transcribe.bat`(드래그&드롭 실행) 제작을 제안(사용자 응답 대기).

**변경 파일**
- Worklog.md (기록만; 기능 변경 없음)

**검증**
- 해당 없음(설명 작업). 안내 내용은 README·검증 완료 기능과 일치함을 확인.

**판단 근거**
- 안내는 실제 구현·검증된 기능만 포함(CLAUDE.md 8절).

**결과**
- 완료. 남은 작업: S5(문서 최종 정리), (선택) 편의 bat 스크립트.

### W-011 · 실사용 인터뷰 영상 3건 변환 검증 (T-005·T-006 해결)
**요청**
- tests/ 하위의 실사용 mp4(1인 인터뷰 영상 3건, 각 5~8분·합계 20분)로 결과물 확인.

**수행 작업**
- 개인 콘텐츠 보호 선행: 출력 폴더 `tests/tests-output/`을 .gitignore에 등록(영상 원본은 기존 `*.mp4` 규칙으로 이미 제외). 커밋에는 결과물·영상 미포함.
- 1차 배치(GPU large-v3 + --diarize): 텍스트 3건 성공, 그러나 화자 라벨 전무 → **T-005**(pyannote 경로 전달 시 soundfile이 mp4를 못 엶) 발견·해결(파형 직접 전달 리팩터링).
- 2차 배치: 경고 0건, 3건 모두 라벨 적용.
- 원시 화자 진단 중 **T-006**(speechbrain k2 지연 모듈 간헐 크래시, Windows 가드 무력화) 발견·해결.
- 진단 확정: 세 영상 모두 pyannote 원시 출력이 사실상 단일 화자(제2 화자 합계 0초대) → "화자 1"만 표기는 **정답**(1인 인터뷰 편집 형식). 2인 분리 능력은 W-010에서 기검증.

**변경 파일**
- audio_to_text/transcriber.py(파형 반환), audio_to_text/diarizer.py(diarize_waveform·T-006 방어), audio_to_text/cli.py(파형 전달), tests/test_diarizer.py, .gitignore, Troubleshootinglog.md(T-005·T-006), docs/validation-plan.md, README.md, Worklog.md

**검증**
- 단위 테스트 27/27 유지. 실사용 3건 E2E: md(메타표+문단), srt(자막 규격), txt 모두 정상, 화자 라벨 포함.
- T-006은 실패가 재현되던 실행 문맥에서 3건 연속 통과로 해결 확인.
- 인식 품질: 육안 판독상 매우 정확. 고유명사 1건 오인식 확인(회사명 첫 등장 1회, 이후 등장은 정확) → 한계로 문서화.

**판단 근거**
- 원시 화자 통계까지 확인해 "라벨 1종 = 버그"가 아니라 "영상 특성"임을 데이터로 판정. 로그를 tail로 잘라 오판했던 실수도 재발 방지에 기록(T-005).

**결과**
- 실사용 검증 완료(도구가 실제 용도로 동작함을 확인). 남은 작업: S5(문서 최종 정리).

### W-010 · S4 화자 구분(--diarize) 실측 완료 (T-002~T-004 해결)
**요청**
- HF 토큰 설정 확인 요청 → 검증 후 S4 연속 진행(승인 흐름).

**수행 작업**
- 토큰 검증(값 비출력): 유효 확인(계정 rlaqkr12123), 게이트 2종 접근 확인 — segmentation-3.0 미동의(403) 발견 → 사용자 동의 후 200 재확인.
- 의존성 설치에서 연쇄 이슈 3건 발견·해결:
  - **T-002**: 범위 지정 탓에 PyPI torch 2.12(비호환·CUDA 불명) 설치됨 → `torch==2.5.1+cu124`/`torchaudio==2.5.1+cu124` 정확 고정, CUDA(RTX 4090) 인식 확인.
  - **T-003**: pyannote 3.4 내부의 use_auth_token이 hub 1.x에서 제거되어 다운로드 실패 → `huggingface_hub>=0.30,<1` 고정. diarizer는 토큰을 환경변수로 전달(버전 독립).
  - **T-004**: pip 휠 cuDNN 9.24와 torch 번들 9.1 이중 로드로 네이티브 크래시 → transcriber를 "torch 우선" DLL 전략으로 수정.
- 픽스처: tools/make_test_dialogue.ps1 신규(2-보이스 이어붙임, 파라미터화). 한/영 혼합(Heami/Zira)과 영어 2인(David/Zira) 두 종 생성.
- diarizer에 GPU 이동(pipeline.to(cuda)) 추가. 단위 테스트 1건을 sys.modules 차단 방식으로 보정(설치 여부와 무관하게 미설치 경로 검증).

**변경 파일**
- audio_to_text/diarizer.py, audio_to_text/transcriber.py, requirements-diarize.txt, tests/test_diarizer.py, tools/make_test_dialogue.ps1(신규), Troubleshootinglog.md(T-002~T-004), README.md, docs/validation-plan.md, docs/implementation-plan.md, Worklog.md

**검증** (모두 실측)
- 영어 2인 대화: David 발화 1·3 → `화자 1`, Zira 발화 2 → `화자 2` — 라벨·첫 등장 순서(D-003)·시간 매칭 정확. txt/srt 표기 규격 일치.
- `--num-speakers 2` 힌트 동일 결과. 단위 테스트 27/27 유지.
- 같은 프로세스에서 GPU Whisper(large-v3, cuda/float16) + pyannote 공존 정상(T-004 해결 확인).
- 미준비 폴백(안내 후 텍스트 계속, D-003)이 T-003 진행 중 실전으로 확인됨.
- 한계 확인: 한/영 혼합 파일에서 영어 발화 누락 + 타임스탬프 부정확(Whisper 단일 언어 디코딩) → validation-plan "확인된 한계"와 README에 명시.

**판단 근거**
- implementation-plan S4. 의존성 이슈는 각 T-ID의 재발 방지 원칙(정확 고정, 공유 의존성 양쪽 호환, CUDA 라이브러리 단일화)으로 일반화.

**결과**
- S4 완료. 남은 작업: S5(문서 최종 정리)만 남음.

### W-009 · S3 옵션·폴더 일괄·경계 E2E 검증
**요청**
- "진행해줘" — 권장 순서(S3 우선)대로 착수.

**수행 작업**
- 도구 보강: tools/make_test_audio.ps1에 `-Text/-OutFile/-Culture` 파라미터 추가(임의 문장·언어·경로 지정), tools/make_test_video.py에 확장자별 코덱 선택(webm→Opus 48kHz, mp3→LAME, 그 외→AAC), tools/make_test_silence.py 신규(무음 WAV).
- 픽스처 생성(전부 out/, 비커밋): 배치용 2문장(하위 폴더 포함), 영어 문장(Zira), 무음 3초, 손상 mp3, 컨테이너 6종(mkv·mov·webm·ts·mp3·m4a).
- E2E 실행(small/cpu): T1 폴더 일괄+미러링, T2 --no-timestamps, T3 --language auto, T4 무음, T5 손상 혼합 배치, T6 컨테이너 일괄, 추가로 mp3·m4a 오디오 형식.

**변경 파일**
- tools/make_test_audio.ps1, tools/make_test_video.py, tools/make_test_silence.py(신규), docs/validation-plan.md, docs/implementation-plan.md, README.md, Worklog.md

**검증** (전 항목 통과)
- T1: 폴더 재귀 수집 2건 성공, `out/batch_out/sub/b.*`로 하위 구조 미러링 확인, 인식 내용 정답 일치.
- T2: 타임스탬프 0건, 문단 병합 텍스트 확인.
- T3: 영어 파일 `--language auto` → md 메타 `언어 en`, 내용 정답 일치.
- T4: 무음 → txt/md/srt 생성, `(인식된 음성 없음)` 명시, 성공 집계, exit 0.
- T5: 손상 mp3 + 정상 wav 배치 → 성공 1/실패 1, **exit 1** (첫 실측).
- T6+: mkv·mov·webm(Opus)·ts·mp3·m4a 모두 디코딩·인식 성공.
- README의 컨테이너 검증 주장에서 미실측(flac·ogg·opus·aac·wma·avi)을 분리해 정직하게 기재.

**판단 근거**
- implementation-plan S3. stderr/stdout 리다이렉트 순서 문제는 버퍼링 특성으로 코드 결함 아님(validation-plan 메모).

**결과**
- S3 완료. 남은 작업: S4(HF 토큰 대기), S5(최종 문서 정리).

### W-008 · 남은 작업 정리
**요청**
- 남은 작업 정리.

**수행 작업**
- 구현 계획·검증 계획을 대조해 잔여 작업을 3단계로 정리해 보고: S3(옵션·폴더 E2E — 검증만 남음), S4(화자 구분 실측 — HF 토큰 발급이 사용자 선행 작업), S5(문서 최종 정리).
- 미검증 잔여 항목(무음 E2E, 종료 코드 1, mp4 외 컨테이너)을 S3에 편입해 정리.
- docs/implementation-plan.md에 "진행 상태" 섹션 추가(S0~S2 완료 표시, S4 선행 조건 명시).

**변경 파일**
- docs/implementation-plan.md, Worklog.md

**검증**
- 문서 정리 작업(실행 검증 대상 아님). 계획·검증 문서와 정합 확인.

**판단 근거**
- 진행 상태가 채팅에만 있으면 휘발되므로 계획 문서에 고정(문서-실제 상태 정합 유지, CLAUDE.md 8절).

**결과**
- 완료. 다음 착수 후보: S3(즉시 가능) → S4(토큰 준비 후) → S5.

### W-007 · S2 GPU 검증 + T-001 해결 + 동영상 입력 검증
**요청**
- S1에 이어 계속 진행(같은 승인 흐름).

**수행 작업**
- GPU 첫 실행: 모델 로드(cuda, float16)는 성공했으나 첫 추론에서 `cublas64_12.dll` 로드 실패 → **설계한 CPU 자동 폴백이 실전에서 정상 작동**(변환 성공, exit 0) → T-001 기록.
- 원인 수정: DLL 폴더를 `os.add_dll_directory()` 외에 `PATH`에도 등록(transcriber.py) → large-v3(cuda, float16) 추론 성공.
- STT 통과 판정(교차 검증): 문장 2 통과(핵심 단어 전부 보존, "세 가지"→"3가지"는 허용 범위). 문장 1의 "화창"→"확장"은 3개 모델 동일 오인식 → TTS 픽스처 발음 한계로 판정.
- tools/make_test_video.py(PyAV) 작성 → wav를 mp4로 변환해 **동영상 입력 E2E 통과**.
- 종료 코드 2 확인(앞선 exit=0은 셸 파이프 측정 오류였음을 확인 후 정정).

**변경 파일**
- audio_to_text/transcriber.py(PATH 등록), tools/make_test_video.py(신규), Troubleshootinglog.md(T-001), docs/validation-plan.md(미검증 범위 갱신), README.md(검증 상태)

**검증**
- large-v3(cuda/float16) 추론 성공(폴백 메시지 없음), mp4 인식 결과 정답 일치, exit=2 확인.

**판단 근거**
- implementation-plan S2. "모델 로드 성공 ≠ 추론 성공" 교훈을 재발 방지에 반영.

**결과**
- S2 완료(GPU·CPU 모두 검증). 남은 작업: S3(폴더 일괄·옵션 E2E), S4(화자 구분 실측), S5(README 최종 정리).

### W-006 · S1 기본 변환 구현 + 단위·E2E 검증
**요청**
- "시작해줘" — S1 착수.

**수행 작업**
- `audio_to_text` 패키지 구현: files.py(입력 수집·경로 미러링·이름 충돌 회피), transcriber.py(모델 로드·auto 해석·진행률·폴백), formatters.py(txt/md/srt·문단 병합·빈 결과 문구), diarizer.py(첫 등장 순 화자 라벨·겹침 최대 매칭·미준비 안내), cli.py(argparse·오케스트레이션·종료 코드), transcribe.py 진입점.
- requirements-diarize.txt 작성(안내 메시지의 실효성 확보, S4 검증 예정).
- 단위 테스트 27건 작성(tests/test_formatters·test_files·test_diarizer).
- tools/make_test_audio.ps1(TTS 정답 문장 WAV 생성, UTF-8 BOM 처리).
- 개선: 모델 지연 로드(전부 건너뜀이면 모델을 아예 로드하지 않음).
- 계약 보완 2건: 출력 이름 충돌 회피 규칙, 파일 인코딩(txt/md UTF-8, srt UTF-8 BOM).

**변경 파일**
- audio_to_text/(6개 파일), transcribe.py, requirements-diarize.txt, tests/(3개), tools/make_test_audio.ps1, docs/requirements-contract.md

**검증**
- 단위 테스트 27/27 통과.
- E2E(wav, cpu/small): txt·md·srt 3형식 생성, 타임스탬프·메타표·SRT 블록 규격 일치.
- 계약 동작 확인: 건너뜀+exit 0, 지연 로드, `--diarize` 미준비 시 한국어 안내 후 계속(D-003).
- 문장 1 "화창"→"확장" 오인식은 W-007에서 픽스처 한계로 판정.

**판단 근거**
- implementation-plan S1, requirements-contract 규격(D-003 포함) 그대로 구현.

**결과**
- S1 완료. 남은 작업: S2(→W-007).

### W-005 · S0 환경·의존성 준비
**요청**
- "시작해줘" — S0 착수 승인.

**수행 작업**
- Python 3.10.8 확인 → `.venv` 생성, pip 26.1.2로 업그레이드.
- `requirements.txt` 작성(faster-whisper, tqdm, nvidia-cublas-cu12, nvidia-cudnn-cu12>=9,<10) 및 설치.
- 설치 결과: faster-whisper 1.2.1, ctranslate2 4.8.1, av(PyAV) 17.1.0, cuDNN 9.24, cuBLAS 12.9.

**변경 파일**
- requirements.txt (신규)

**검증**
- `from faster_whisper import WhisperModel` import 성공.
- `resolve_device('auto')` → `('cuda', 'float16', None)` — pip 휠 DLL 등록으로 RTX 4090 정상 감지.

**판단 근거**
- implementation-plan S0. FFmpeg 없이 PyAV로 디코딩하는 PLAN.md 전략 유지.

**결과**
- 완료: S0 완료 조건 충족.
- 남은 작업: S1 구현.

### W-004 · docs 문서 검토 및 계약 확정
**요청**
- `PLAN.md`를 더 구체화해 docs 내 각 md의 고도화 필요 여부 검토.

**수행 작업**
- docs 4종을 `PLAN.md`와 대조 검토. 결론: 전면 고도화 불필요, PLAN.md 내용의 중복 복사는 모순 위험이 커서 지양.
- 발견 1 — 문서 간 모순: project-plan 마일스톤(S1~S4)과 implementation-plan(S0~S5) 번호 불일치 → project-plan을 S0~S5로 정렬.
- 발견 2 — 계약 공백: `확인 필요` 2건을 사용자 확인으로 확정(D-003: diarize 실패 시 안내 후 계속 / 무음 파일도 빈 출력 생성 / 폴더 출력 미러링). 관례 항목(SRT v1 세그먼트 그대로, 화자 번호 첫 등장 순, 종료 코드 0·1·2, 문서 우선순위)도 계약에 명시.
- 발견 3 — 검증 공백: validation-plan에 STT 통과 판정 기준(핵심 단어 보존, 조사·띄어쓰기 차이 허용)과 테스트 오디오 비커밋 원칙, 종료 코드 검증 항목 추가.

**변경 파일**
- docs/project-plan.md, docs/requirements-contract.md, docs/validation-plan.md, Decisionlog.md, Worklog.md

**검증**
- 문서 수정만 수행(코드 없음). 3개 문서의 단계 번호·규칙 상호 참조를 육안 대조.

**판단 근거**
- CLAUDE.md 8절(문서 간 무모순)과 5절(구현 전 계약 확정)에 따라 S1 착수 전 규격을 고정.

**결과**
- 완료: 계약 문서 확정(`확인 필요` 0건). 구현 착수 준비됨.
- 남은 작업: S0(환경 준비) 착수.

### W-003 · Worklog 기록 범위 확대 (모든 작업 기록)
**요청**
- Worklog를 "주요 요청"이 아니라 **모든 작업**에 대해 기록하도록 변경하고, CLAUDE.md도 그 방향으로 수정.

**수행 작업**
- CLAUDE.md 11절 Worklog 규칙을 "주요 요청마다" → "모든 작업마다"로 개정(소급 기록·분할 기록 지침 추가).
- Worklog 상단 안내문도 동일 방향으로 수정.
- 누락돼 있던 git 셋업을 W-002로 소급 기록.

**변경 파일**
- CLAUDE.md, Worklog.md

**검증**
- 문서 수정만 수행. 실행 검증 대상 아님(문서 정합성 육안 확인).

**판단 근거**
- 사용자가 상세한 개발 기록을 원함. 기록 누락(git 셋업)이 실제로 발생해 규칙을 강화.

**결과**
- 완료: 규칙 개정 및 소급 기록. 이후 모든 작업을 Worklog에 남긴다.
- 남은 작업: 변경분 커밋·푸시.

### W-002 · Git 저장소 초기화 및 원격 푸시
**요청**
- GitHub 레포(https://github.com/gorhkdwj/Audio-to-Text.git)로 git 관리 및 푸시.

**수행 작업**
- `git init` → 브랜치 `main` → 원격 `origin` 연결 → 전체 스테이징 → 커밋 → `git push -u origin main`.
- 첫 커밋 메시지에 잘못된 셸 heredoc 표기로 `@` 문자가 혼입 → `git commit --amend`로 정리 후 `--force-with-lease`로 재푸시.

**변경 파일**
- (신규 추적) .gitignore, CLAUDE.md, README.md, Worklog/Decisionlog/Troubleshootinglog, docs/*, tests/.gitkeep, tools/.gitkeep, docs/references/.gitkeep — 커밋 `68f7f0c`

**검증**
- `git ls-remote`로 원격이 비어 있음 확인(충돌 없음). 푸시 후 `main...origin/main` 동기화 확인. `out/`·`.venv/`·비밀정보 미추적 확인.

**판단 근거**
- 초기 운영 체계를 버전 관리에 올려 이후 변경 이력을 추적하기 위함.

**결과**
- 완료: 원격 `main` 생성 및 동기화.
- 남은 작업: 없음(후속 변경은 별도 커밋).

### W-001 · 프로젝트 운영 체계 셋업
**요청**
- 프로젝트 초기 운영 구조 셋업 (`/project-setup`)

**수행 작업**
- 현재 폴더/git 상태 확인. 기존 `PLAN.md`(상세 설계) 확인 후 보존(덮어쓰지 않음).
- CLAUDE.md(작업 헌법), README.md, Worklog/Decisionlog/Troubleshootinglog, docs 4종(project-plan, requirements-contract, implementation-plan, validation-plan), .gitignore 생성.
- 빈 폴더 tests/ tools/ out/ docs/references/ 생성(.gitkeep). data/ 는 데이터셋 없어 생략.
- PLAN.md의 확정 사항(로컬 Whisper/faster-whisper, CLI, 한국어 위주, txt·md·srt·화자구분, RTX 4090, FFmpeg 미설치→PyAV)을 각 문서에 반영.

**변경 파일**
- CLAUDE.md, README.md, Worklog.md, Decisionlog.md, Troubleshootinglog.md, .gitignore
- docs/project-plan.md, docs/requirements-contract.md, docs/implementation-plan.md, docs/validation-plan.md
- tests/.gitkeep, tools/.gitkeep, out/.gitkeep, docs/references/.gitkeep

**검증**
- 파일 생성 및 폴더 구조 확인. **구현 미착수**(코드 없음).

**판단 근거**
- 문서화·검증을 중시하는 진행 방식에 맞춰, 구현 전에 판단·구조 일관성을 잡는 운영 체계를 우선 적용.

**결과**
- 완료: 운영 파일 생성, PLAN.md 설계 반영
- 남은 작업: 기준 계약 문서 확정 → S1(기본 변환) 구현
