from __future__ import annotations

import re
from pathlib import Path

import pytest

ROLLBACK_PATTERN = re.compile(r"\bdb\.session\.rollback\(")


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
def test_repositories_do_not_call_db_session_rollback() -> None:
    """Write boundary: repositories 层不得回滚整个 session(应由边界入口处理)."""
    repo_root = Path(__file__).resolve().parents[2]
    repositories_root = repo_root / "app" / "repositories"

    matches: list[str] = []
    for path in repositories_root.rglob("*.py"):
        matches.extend(_scan_file(path, display_path=path.relative_to(repo_root)))

    assert not matches, "Repositories 层发现 db.session.rollback 漂移:\n" + "\n".join(matches[:50])

