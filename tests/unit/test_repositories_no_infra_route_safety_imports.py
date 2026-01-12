from __future__ import annotations

import re
from pathlib import Path

import pytest

ROUTE_SAFETY_IMPORT_PATTERN = re.compile(r"\bapp\.infra\.route_safety\b")


def _scan_file(path: Path, *, display_path: Path) -> list[str]:
    matches: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return matches

    for lineno, line in enumerate(content.splitlines(), start=1):
        if ROUTE_SAFETY_IMPORT_PATTERN.search(line):
            matches.append(f"{display_path}:{lineno}: {line.strip()}")
    return matches


@pytest.mark.unit
def test_repositories_do_not_import_infra_route_safety() -> None:
    """Repository 层避免依赖 request/actor 语义的 route_safety 适配器."""
    repo_root = Path(__file__).resolve().parents[2]
    repositories_root = repo_root / "app" / "repositories"

    matches: list[str] = []
    for path in repositories_root.rglob("*.py"):
        matches.extend(_scan_file(path, display_path=path.relative_to(repo_root)))

    assert not matches, "Repository 层发现对 app.infra.route_safety 的依赖:\n" + "\n".join(matches[:50])

