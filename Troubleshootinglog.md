# Troubleshootinglog · Audio_to_Text

실제 오류·실패·환경 문제·검증 실패·설계 충돌이 발생하면 기록한다. 같은 문제가 반복되면 새 T-ID를 만들기 전에 기존 T-ID를 먼저 확인한다. (규칙: CLAUDE.md 11절)

## 기록 형식
```
### T-00N · 문제 제목
**발생 상황** / **증상** / **확인된 원인** / **조치** / **재발 방지**
```

## 미리 예상되는 위험 (발생 시 여기에 T-ID로 기록)
- ~~CUDA 12 + cuDNN 9 DLL 로드 실패~~ → **T-001로 실제 발생·해결됨** (2026-07-04).
- pyannote 게이트 모델 접근 실패(HuggingFace 토큰 미설정/약관 미동의). → 설치·설정 안내 메시지 구현됨(S4에서 실측 예정).
- PyAV로 특정 동영상 컨테이너 디코딩 실패 가능성. (mp4는 검증 완료)

---

### T-006 · speechbrain 지연 모듈(k2)로 인한 간헐적 파이프라인 로드 실패
**발생 상황**
- 실사용 mp4 검증 중 원시 화자 진단(2026-07-04). 처음에는 `python -c` 문맥에서만 재현됐으나, 이후 CLI 코드 경로에서도 발생 확인 → 실행 문맥 의존 간헐 크래시로 판정.

**증상**
- `ImportError: Lazy import of LazyModule(package=None, target=speechbrain.integrations.k2_fsa, loaded=False) failed` (근저: `No module named 'k2'`)
- CLI에서는 D-003 폴백으로 텍스트 변환은 계속되나 화자 구분이 조용히 빠짐.

**확인된 원인**
- speechbrain은 선택 백엔드(k2 등)를 지연 모듈(LazyModule의 서브클래스 `DeprecatedModuleRedirect` 포함)로 sys.modules에 등록한다.
- 모델 로딩 중 lightning/pyannote가 `inspect`로 스택을 조사할 때 sys.modules를 순회하며 이 모듈들의 속성을 건드리고, 지연 import(k2 — 미설치)가 발동해 ImportError가 난다.
- speechbrain에 이를 막는 자체 가드가 있으나 `filename.endswith("/inspect.py")`로 비교해 **Windows 경로 구분자(`\`)에서 무력화**되는 것이 근본 원인.

**조치**
- diarizer에서 파이프라인 로드 전, "등록만 되고 실제 로드되지 않은" speechbrain 지연 모듈을 sys.modules에서 제거(isinstance로 서브클래스 포함 판별, `__dict__` 접근으로 지연 import 트리거 회피).
- 1차 시도(클래스명 문자열 비교)는 서브클래스를 놓쳐 실패 → speechbrain 소스를 직접 읽고 수정.
- 최종 해결 확인: 실패가 재현되던 문맥에서 3건 연속 경고 없이 화자 구분 완료.

**재발 방지**
- 외부 라이브러리의 간헐 오류는 추측 대신 **해당 소스 코드를 직접 읽고** 근본 원인을 확정한 뒤 고친다.
- 화자 구분 실패는 항상 D-003 폴백으로 변환 자체를 막지 않게 유지한다.

### T-005 · mp4 입력에서 화자 구분 실패 (pyannote가 동영상 컨테이너를 못 엶)
**발생 상황**
- 실사용 인터뷰 mp4 3건 배치(2026-07-04). 텍스트 변환은 3건 성공했으나 세 파일 모두 화자 라벨이 없었음.

**증상**
- `[경고] 화자 구분에 실패해 …: Error opening '…mp4': Format not recognised.`
- 부수 교훈: 배경 실행 로그를 `tail`로 잘라 저장한 탓에 경고가 1건만 보였음(실제는 3건 전부 실패). 로그는 자르지 않고 원본을 남긴다.

**확인된 원인**
- diarizer가 pyannote에 **파일 경로**를 넘기면 pyannote는 torchaudio/soundfile 백엔드로 여는데, soundfile은 mp4 등 동영상 컨테이너를 디코딩하지 못한다(wav라서 S4 픽스처는 통과했던 것).

**조치**
- PLAN.md의 원설계대로 **파형 직접 전달** 구조로 수정: transcriber가 PyAV(`decode_audio`)로 16kHz mono float32 파형을 디코딩·반환하고, Whisper와 pyannote(`{"waveform": tensor, "sample_rate": 16000}`)가 같은 파형을 공유. 이중 디코딩도 제거됨.
- `diarize_file(경로)` → `diarize_waveform(파형)` 개명, cli·단위 테스트 갱신.
- 최종 해결 확인: mp4 3건 전부 경고 0건 + 화자 라벨 적용.

**재발 방지**
- 미디어 디코딩은 PyAV 단일 경로로 통일한다(외부 라이브러리에 경로를 직접 넘기지 않는다).
- 배경 작업 로그는 원본 그대로 보존한다(요약·tail 가공 금지).

### T-004 · cuDNN 이중 로드 크래시 (pip 휠 9.24 vs torch 번들 9.1)
**발생 상황**
- S4, T-003의 hub 고정 후 `--diarize` 재실행(2026-07-04). Whisper(GPU) 변환은 진행됐으나 pyannote 단계에서 프로세스가 비정상 종료(exit 127), 요약 줄 미출력. 출력 파일은 이전 실행 잔재였음.

**증상**
- `Could not load symbol cudnnGetLibConfig. Error code 127` (네이티브 오류, 파이썬 트레이스백 없음)

**확인된 원인**
- T-001 조치로 PATH 앞에 등록한 nvidia pip 휠(cuDNN **9.24**)과 torch 2.5.1+cu124가 번들한 cuDNN **9.1**이 한 프로세스에 섞여 로드됨.
- cuDNN 9는 셔틀 DLL(cudnn64_9)이 하위 구성요소(ops/graph 등)를 동적 로드하는 모듈 구조라, 서로 다른 버전이 섞이면 심볼 불일치로 즉사한다.

**조치**
- `transcriber._register_cuda_dll_dirs()`를 **"torch 우선" 전략**으로 변경: torch가 설치돼 있으면 `import torch`만 수행(torch\lib이 PATH에 등록돼 ctranslate2도 같은 DLL 사용 → 버전 단일화), 없으면 기존 pip 휠 등록(T-001 경로 유지).
- 최종 해결 확인: 같은 프로세스에서 GPU Whisper(large-v3) + pyannote 화자 구분 동시 성공.

**재발 방지**
- 한 프로세스에는 **한 벌의 CUDA 라이브러리만** 로드되게 한다. GPU 스택 의존성을 추가할 때 DLL 출처(pip 휠 vs 프레임워크 번들)가 섞이지 않는지 확인한다.

### T-003 · pyannote 모델 다운로드 실패 — huggingface_hub 1.x의 use_auth_token 제거
**발생 상황**
- S4 첫 실측(2026-07-04). `--diarize` 실행 시 `[경고]`와 함께 화자 구분만 실패하고 텍스트 변환은 계속됨(설계된 D-003 동작 확인).

**증상**
- `hf_hub_download() got an unexpected keyword argument 'use_auth_token'`

**확인된 원인**
- 1차: 우리 diarizer가 `Pipeline.from_pretrained(..., use_auth_token=...)`을 사용 → 인자를 없애고 환경변수(HF_TOKEN) 방식으로 수정했으나 **동일 오류 재발**.
- 2차(근본): pyannote.audio 3.4.0 **내부 코드**가 use_auth_token을 hub에 전달한다. faster-whisper가 설치한 huggingface_hub 1.22.0은 이 인자를 제거했다(pyannote 의존성 메타데이터에 상한이 없어 pip이 비호환 조합을 허용한 것).

**조치**
- requirements-diarize.txt에 `huggingface_hub>=0.30,<1` 고정(0.36.2 설치 — 인자 허용, 경고만).
- diarizer의 환경변수 전달 방식은 유지(hub 버전 독립적).
- faster-whisper 1.2.1이 hub 0.x와 호환됨을 import·실행으로 확인.

**재발 방지**
- 서로 다른 생태계(faster-whisper ↔ pyannote)가 **공유하는 의존성**(huggingface_hub)은 양쪽 호환 범위로 명시 고정한다.
- 미준비/실패 시에도 텍스트 변환은 계속된다는 D-003 폴백이 실전에서 유효함을 확인.

### T-002 · pyannote.audio import 실패 (torchaudio 비호환) + torch 버전 미고정 문제
**발생 상황**
- S4 준비(2026-07-04). `requirements-diarize.txt`(당시 `torch>=2.4` + `--extra-index-url cu124`) 설치 후 `import pyannote.audio` 실패.

**증상**
- `AttributeError: module 'torchaudio' has no attribute 'AudioMetaData'` (pyannote/audio/core/io.py)

**확인된 원인**
- `--extra-index-url`은 PyPI와 PyTorch 인덱스를 **모두** 후보로 두고 최신 버전을 고르므로, PyPI의 torch/torchaudio **2.12.1**이 선택됨.
- torchaudio 2.9+에서 `AudioMetaData` API가 제거되어 pyannote.audio 3.x와 비호환.
- (부가 위험) PyPI 기본 torch 휠은 Windows에서 CUDA 미지원 빌드일 수 있음 — cuda 사용 여부는 미확인 상태였으나 고정으로 원천 차단.

**조치**
- requirements-diarize.txt에서 `torch==2.5.1+cu124`, `torchaudio==2.5.1+cu124`로 **정확히 고정**(+cu124 로컬 버전은 PyTorch 인덱스에만 존재 → CUDA 빌드 강제). pyannote.audio는 `>=3.1,<4` 유지.
- 고정 버전으로 재설치 후 import·CUDA 가용성·화자 구분 실측으로 최종 확인. → 결과는 W-010에 기록.

**재발 방지**
- 외부 인덱스를 쓰는 의존성은 범위 지정 대신 **정확한 버전+로컬 태그로 고정**한다.
- 새 의존성 설치 후에는 "설치 성공"이 아니라 **import 성공까지** 확인한다.

### T-001 · GPU 추론 시 cublas64_12.dll 로드 실패
**발생 상황**
- S2 GPU 검증(2026-07-04). `--device auto`로 large-v3 모델 로드는 성공(cuda, float16)했으나 첫 추론에서 오류 발생.

**증상**
- `Library cublas64_12.dll is not found or cannot be loaded`
- 설계해 둔 CPU(int8) 자동 폴백이 작동해 변환 자체는 성공(exit 0). 결과 md의 모델이 large-v3가 아닌 medium(폴백)으로 기록되어 발견.

**확인된 원인**
- DLL 자체는 `.venv/Lib/site-packages/nvidia/cublas/bin/`에 존재했다.
- `os.add_dll_directory()` 등록은 파이썬 확장 모듈 로드에는 적용되지만, ctranslate2가 **추론 시점**에 호출하는 일반 `LoadLibrary("cublas64_12.dll")`의 검색 경로(실행 파일 폴더·시스템 폴더·PATH)에는 반영되지 않는다.
- 모델 로드까지는 cuBLAS가 필요 없어서 성공했고, 첫 행렬 연산에서 실패한 것.

**조치**
- `transcriber._register_cuda_dll_dirs()`에서 `os.add_dll_directory()`와 함께 NVIDIA 휠 DLL 폴더들을 **`PATH` 환경변수 앞쪽에도 추가**하도록 수정.
- 최종 해결 확인: large-v3(cuda, float16)로 추론 성공, 폴백 메시지 없음.

**재발 방지**
- 코드 주석에 T-001 참조를 남김.
- GPU 관련 변경 시 "모델 로드 성공"만으로 판정하지 말고 **실제 추론까지** 확인한다(로드와 추론의 DLL 요구가 다름).
