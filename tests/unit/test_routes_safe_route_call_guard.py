from __future__ import annotations

from pathlib import Path

import pytest


def _scan_for_missing_safe_route_call(path: Path, *, display_path: Path) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    if ".route(" not in content and "add_url_rule(" not in content:
        return []

    if "safe_route_call(" in content:
        return []

    return [str(display_path)]


@pytest.mark.unit
def test_routes_modules_must_use_safe_route_call() -> None:
    """Routes 层强约束: 含 route 定义的模块必须使用 safe_route_call."""
    repo_root = Path(__file__).resolve().parents[2]
    routes_root = repo_root / "app" / "routes"

    missing: list[str] = []
    for path in routes_root.rglob("*.py"):
        missing.extend(_scan_for_missing_safe_route_call(path, display_path=path.relative_to(repo_root)))

    assert not missing, "发现未使用 safe_route_call 的 routes 模块:\n" + "\n".join(sorted(missing))
