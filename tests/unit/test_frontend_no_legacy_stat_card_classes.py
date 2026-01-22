from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_no_legacy_metric_card_forks() -> None:
    """门禁：禁止继续保留/引入历史指标卡分叉与旧 stats_card 组件。"""
    repo_root = Path(__file__).resolve().parents[2]

    # Match exact class tokens, avoid substring hits (e.g. "change-log-stats-card").
    forbidden_patterns = [
        re.compile(r"(?<![\\w-])dashboard-stat-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])tags-stat-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])log-stats-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])session-stats-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])scheduler-stat-card(?![\\w-])"),
    ]

    scan_targets = [
        repo_root / "app/templates",
        repo_root / "app/static/css/pages",
    ]

    matches: list[str] = []
    for target in scan_targets:
        for path in target.rglob("*"):
            if path.is_dir():
                continue
            if path.suffix not in {".html", ".css"}:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                if pattern.search(content):
                    matches.append(f"{path.relative_to(repo_root)}: matches {pattern.pattern}")

    assert not matches, "发现指标卡私有体系残留:\n" + "\n".join(matches[:50])

    base_html = (repo_root / "app/templates/base.html").read_text(encoding="utf-8", errors="ignore")
    assert "css/components/stats-card.css" not in base_html, "base.html 不应再引入 stats-card.css"

    assert not (repo_root / "app/templates/components/ui/stats_card.html").exists(), "stats_card.html 应被移除"
    assert not (repo_root / "app/static/css/components/stats-card.css").exists(), "stats-card.css 应被移除"

    macros = (repo_root / "app/templates/components/ui/macros.html").read_text(encoding="utf-8", errors="ignore")
    assert "macro stats_card" not in macros, "macros.html 不应再定义 stats_card 宏"
