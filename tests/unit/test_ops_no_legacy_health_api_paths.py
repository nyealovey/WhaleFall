from __future__ import annotations

from pathlib import Path

import pytest

LEGACY_HEALTH_API_PREFIX = "/health/api/"


def _scan_file(path: Path, *, display_path: Path) -> list[str]:
    matches: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return matches

    for lineno, line in enumerate(content.splitlines(), start=1):
        if LEGACY_HEALTH_API_PREFIX in line:
            matches.append(f"{display_path}:{lineno}: {line.strip()}")
    return matches


@pytest.mark.unit
def test_ops_sources_do_not_use_legacy_health_api_paths() -> None:
    """避免部署/运维脚本仍访问旧 `/health/api/*` (将导致 410)."""
    repo_root = Path(__file__).resolve().parents[2]
    targets: list[Path] = [
        repo_root / "Dockerfile.prod",
        repo_root / "docker-compose.prod.yml",
        repo_root / "docker-compose.flask-only.yml",
        repo_root / "Makefile.prod",
        repo_root / "Makefile.flask",
        repo_root / "nginx",
        repo_root / "scripts",
        repo_root / "docs" / "operations",
    ]

    matches: list[str] = []
    for target in targets:
        if target.is_file():
            matches.extend(_scan_file(target, display_path=target.relative_to(repo_root)))
            continue
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if path.is_dir():
                continue
            matches.extend(_scan_file(path, display_path=path.relative_to(repo_root)))

    assert not matches, "发现旧健康检查 API 路径引用(将导致 410):\n" + "\n".join(matches[:50])
