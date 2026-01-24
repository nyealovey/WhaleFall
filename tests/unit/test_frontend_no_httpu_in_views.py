from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_change_password_modals_must_not_use_httpu() -> None:
    """change password 全局模态属于 views 层，禁止直接访问 window.httpU。"""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/auth/modals/change-password-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "httpU" not in content, "change-password-modals.js 不得直接访问 window.httpU"

