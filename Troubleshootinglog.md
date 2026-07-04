# Troubleshootinglog · Audio_to_Text

실제 오류·실패·환경 문제·검증 실패·설계 충돌이 발생하면 기록한다. 같은 문제가 반복되면 새 T-ID를 만들기 전에 기존 T-ID를 먼저 확인한다. (규칙: CLAUDE.md 11절)

## 기록 형식
```
### T-00N · 문제 제목
**발생 상황** / **증상** / **확인된 원인** / **조치** / **재발 방지**
```

## 미리 예상되는 위험 (발생 시 여기에 T-ID로 기록)
- CUDA 12 + cuDNN 9 DLL 로드 실패(ctranslate2/faster-whisper, Windows). → CPU(int8) 자동 폴백 + 한국어 안내 예정.
- pyannote 게이트 모델 접근 실패(HuggingFace 토큰 미설정/약관 미동의). → 설치·설정 안내 메시지 예정.
- PyAV로 특정 동영상 컨테이너 디코딩 실패 가능성.

---

(아직 실제로 기록된 문제 없음)
