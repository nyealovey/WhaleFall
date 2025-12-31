from __future__ import annotations

import re
from pathlib import Path

import pytest

LEGACY_API_PATTERN = re.compile(r"/api(?!/v1)(?:/|$)")


def _scan_file(path: Path, *, display_path: Path) -> list[str]:
    matches: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return matches

    for lineno, line in enumerate(content.splitlines(), start=1):
        if LEGACY_API_PATTERN.search(line):
            matches.append(f"{display_path}:{lineno}: {line.strip()}")
    return matches


@pytest.mark.unit
def test_frontend_sources_do_not_use_legacy_api_paths() -> None:
    """强下线策略下,前端/模板不得再访问旧 `*/api/*` 端点."""
    repo_root = Path(__file__).resolve().parents[2]
    targets = [
        repo_root / "app/static/js",
        repo_root / "app/templates",
    ]

    matches: list[str] = []
    for target in targets:
        for path in target.rglob("*"):
            if path.is_dir():
                continue
            if path.suffix not in {".js", ".html"}:
                continue
            matches.extend(_scan_file(path, display_path=path.relative_to(repo_root)))

    assert not matches, "发现旧版 API 路径引用(将导致 410):\n" + "\n".join(matches[:50])
