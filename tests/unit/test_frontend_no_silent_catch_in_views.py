from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_views_must_not_silently_swallow_errors() -> None:
    """禁止前端视图层出现 `.catch(() => {})` 这种静默吞异常写法。"""

    repo_root = Path(__file__).resolve().parents[2]
    views_root = repo_root / "app/static/js/modules/views"
    assert views_root.exists(), "views 目录不存在，检查测试路径是否正确"

    silent_catch = re.compile(r"\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)")
    offenders: list[str] = []

    for path in views_root.rglob("*.js"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        if silent_catch.search(content):
            offenders.append(str(path.relative_to(repo_root)))

    assert not offenders, (
        "views 禁止使用 `.catch(() => {})` 静默吞异常（必须显式提示/上报/日志）。\n"
        + "\n".join(offenders)
    )

