from __future__ import annotations

import re
from pathlib import Path

import pytest

ENV_READ_PATTERN = re.compile(r"\bos\.(?:environ\.get|getenv)\(")


def _scan_file(path: Path, *, display_path: Path) -> list[str]:
    matches: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return matches

    for lineno, line in enumerate(content.splitlines(), start=1):
        if ENV_READ_PATTERN.search(line):
            matches.append(f"{display_path}:{lineno}: {line.strip()}")
    return matches


@pytest.mark.unit
def test_no_os_environ_reads_outside_settings_module() -> None:
    """配置读取强约束: 禁止在非 settings/入口脚本中读取环境变量."""
    repo_root = Path(__file__).resolve().parents[2]

    allowlist = {
        Path("app/settings.py"),
        Path("app.py"),
        Path("wsgi.py"),
    }

    matches: list[str] = []
    for path in (repo_root / "app").rglob("*.py"):
        rel = path.relative_to(repo_root)
        if rel in allowlist:
            continue
        matches.extend(_scan_file(path, display_path=rel))

    assert not matches, "发现 settings 之外的环境变量读取:\n" + "\n".join(matches[:50])
