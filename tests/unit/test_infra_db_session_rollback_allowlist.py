from __future__ import annotations

import re
from pathlib import Path

import pytest

ROLLBACK_PATTERN = re.compile(r"\bdb\.session\.rollback\(")

ALLOWED_INFRA_ROLLBACK_FILES = {
    Path("app/infra/route_safety.py"),
    Path("app/infra/logging/queue_worker.py"),
}


def _scan_file(path: Path, *, display_path: Path) -> list[str]:
    matches: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return matches

    for lineno, line in enumerate(content.splitlines(), start=1):
        if ROLLBACK_PATTERN.search(line):
            matches.append(f"{display_path}:{lineno}: {line.strip()}")
    return matches


@pytest.mark.unit
def test_infra_db_session_rollback_is_limited_to_entrypoints() -> None:
    """Write boundary: infra 中仅允许提交点入口执行 rollback."""
    repo_root = Path(__file__).resolve().parents[2]
    infra_root = repo_root / "app" / "infra"

    matches: list[str] = []
    for path in infra_root.rglob("*.py"):
        rel = path.relative_to(repo_root)
        if rel in ALLOWED_INFRA_ROLLBACK_FILES:
            continue
        matches.extend(_scan_file(path, display_path=rel))

    assert not matches, "Infra 层发现 db.session.rollback 漂移:\n" + "\n".join(matches[:50])
