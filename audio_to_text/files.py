"""입력 수집과 출력 경로 계산.

- 지원 확장자 정의 (오디오/동영상)
- 파일/폴더 입력을 받아 변환 대상 목록을 만든다 (폴더는 재귀 수집)
- 출력 경로 계산: 기본은 입력 파일 옆, --output-dir 지정 시 폴더 구조 미러링
- 출력 이름 충돌(같은 이름의 다른 확장자) 감지 및 회피

규칙 출처: docs/requirements-contract.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


class InputError(Exception):
    """입력 자체가 잘못된 경우(존재하지 않는 경로 등) — 종료 코드 2 대상."""


@dataclass
class InputItem:
    """변환 대상 파일 하나.

    base_dir: 폴더 입력으로 수집된 경우 그 폴더. --output-dir 지정 시
              이 폴더 기준 상대 경로를 출력 폴더에 미러링한다.
    """

    path: Path
    base_dir: Path | None = None


def collect_inputs(raw_paths: list[str]) -> tuple[list[InputItem], list[str]]:
    """파일/폴더 경로 목록에서 변환 대상을 수집한다.

    반환: (변환 대상 목록, 경고 메시지 목록)
    - 존재하지 않는 경로 → InputError
    - 직접 지정한 파일이 지원하지 않는 확장자 → 경고 후 건너뜀
    - 폴더 → 지원 확장자 파일만 재귀 수집(경로순 정렬)
    - 같은 파일이 두 번 지정되면 한 번만 변환한다.
    """
    items: list[InputItem] = []
    warnings: list[str] = []
    seen: set[Path] = set()

    for raw in raw_paths:
        path = Path(raw)
        if not path.exists():
            raise InputError(f"경로를 찾을 수 없습니다: {raw}")
        if path.is_file():
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                warnings.append(f"지원하지 않는 확장자라 건너뜁니다: {path}")
                continue
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                items.append(InputItem(path=path))
        else:  # 폴더: 지원 확장자 파일만 재귀 수집
            found = sorted(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            if not found:
                warnings.append(f"폴더에 지원하는 미디어 파일이 없습니다: {path}")
            for p in found:
                resolved = p.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    items.append(InputItem(path=p, base_dir=path))
    return items, warnings


def plan_output_paths(
    items: list[InputItem],
    formats: list[str],
    output_dir: str | None,
) -> tuple[dict[tuple[Path, str], Path], list[str]]:
    """모든 (입력 파일, 형식) 조합의 출력 경로를 미리 계산한다.

    반환: ({(입력 경로, 형식): 출력 경로}, 경고 메시지 목록)
    - 기본: 입력 파일과 같은 폴더에 같은 이름(stem) + 형식 확장자
    - --output-dir + 폴더 입력: 입력 폴더 기준 상대 경로를 미러링
    - 서로 다른 입력이 같은 출력 이름으로 이어지면(예: a.mp3와 a.wav)
      충돌한 입력만 원본 확장자를 포함한 이름(a.mp3.md)으로 저장하고 경고
    """
    out_base = Path(output_dir) if output_dir else None

    # 1) 형식과 무관한 "출력 폴더/파일 줄기(stem)"를 먼저 정한다.
    stems: dict[Path, Path] = {}
    for item in items:
        if out_base is not None:
            if item.base_dir is not None:
                rel = item.path.relative_to(item.base_dir)
                target_dir = out_base / rel.parent  # 하위 구조 미러링
            else:
                target_dir = out_base
        else:
            target_dir = item.path.parent
        stems[item.path] = target_dir / item.path.stem

    # 2) 같은 줄기를 쓰는 입력이 여럿이면 원본 확장자를 붙여 회피한다.
    warnings: list[str] = []
    by_stem: dict[Path, list[Path]] = {}
    for input_path, stem in stems.items():
        by_stem.setdefault(stem, []).append(input_path)
    for stem, sources in by_stem.items():
        if len(sources) > 1:
            for src in sources:
                stems[src] = stem.with_name(src.name)  # 예: a.mp3 → a.mp3.md
            names = ", ".join(str(s) for s in sources)
            warnings.append(f"출력 이름이 겹쳐 원본 확장자를 포함해 저장합니다: {names}")

    # 3) 형식별 최종 경로.
    plan: dict[tuple[Path, str], Path] = {}
    for item in items:
        base = stems[item.path]
        for fmt in formats:
            plan[(item.path, fmt)] = base.parent / f"{base.name}.{fmt}"
    return plan, warnings
