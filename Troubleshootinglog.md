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
