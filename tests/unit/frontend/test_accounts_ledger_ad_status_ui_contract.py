from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]


def _read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@pytest.mark.unit
def test_accounts_ledger_template_exposes_ad_status_filter() -> None:
    content = _read_text("app/templates/accounts/ledgers.html")

    assert "ad_status_filter" in content
    assert "ad_status_options" in content
    assert "ad_status" in content


@pytest.mark.unit
def test_accounts_ledger_frontend_renders_ad_status_column_and_filter_param() -> None:
    content = _read_text("app/static/js/modules/views/accounts/ledgers.js")

    assert '"ad_status"' in content
    assert 'name: "AD状态"' in content
    assert 'id: "ad_status"' in content
    assert "renderAdStatusIndicator" in content
    assert "item.ad_status" in content
    assert "item.ad_domain" in content
    assert "item.ad_disabled_at" in content
    assert "item.ad_orphaned_at" in content


@pytest.mark.unit
def test_accounts_ledger_css_styles_ad_status_indicator() -> None:
    content = _read_text("app/static/css/pages/accounts/ledgers.css")

    assert 'data-column-id="ad_status"' in content
    assert ".ledger-compact-indicator--ad-disabled" in content
    assert ".ledger-compact-indicator--ad-orphaned" in content
