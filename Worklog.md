# Worklog · Audio_to_Text

**모든 작업을 빠짐없이** 아래 형식으로 누적 기록한다. 규모가 작아도 생략하지 않는다. (규칙: CLAUDE.md 11절). 최신 항목을 위에 추가한다.

## 기록 형식
```
### W-00N · 작업 제목
**요청** / **수행 작업** / **변경 파일** / **검증** / **판단 근거** / **결과**
```

---

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
