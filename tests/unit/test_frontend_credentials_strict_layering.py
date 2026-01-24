from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_credential_modals_must_not_construct_service() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/credentials/modals/credential-modals.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new CredentialsService" not in content, (
        "credential-modals 不得自行 new CredentialsService（必须由 Page Entry 注入 store/actions）"
    )


@pytest.mark.unit
def test_credentials_list_page_must_not_have_migration_fallback() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/credentials/list.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "初始化 CredentialsService/CredentialsStore 失败" not in content, (
        "CredentialsListPage 不应保留迁移期 try/catch 兜底（应 fail fast）"
    )


@pytest.mark.unit
def test_credentials_list_page_must_inject_store_to_modals() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/credentials/list.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    pattern = re.compile(
        r"CredentialModals\.createController\(\{[\s\S]*?\bstore\s*:",
        re.MULTILINE,
    )
    assert pattern.search(content), "CredentialsListPage 必须向 credential-modals 注入 store"
