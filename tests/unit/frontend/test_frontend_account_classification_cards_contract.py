"""账户分类左栏资料卡契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_account_classification_cards_use_dossier_structure() -> None:
    content = _read_text("app/static/js/modules/views/accounts/account-classification/index.js")

    required_fragments = (
        "function renderClassificationCard(classification)",
        "classification-card__masthead",
        "classification-card__identity",
        "classification-card__signals",
        "classification-card__code",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "classification-card__note" not in content
    assert "classification-card__meta" not in content
    assert "renderLedgerChip(`优先级 ${priority}`, 'muted')" not in content
    assert "renderLedgerChip(`规则 ${rulesCount}`, 'muted')" not in content
    assert "classification?.description" not in content


def test_account_classification_cards_preserve_edit_and_delete_actions() -> None:
    content = _read_text("app/static/js/modules/views/accounts/account-classification/index.js")

    required_fragments = (
        'data-action="edit-classification"',
        'data-action="delete-classification"',
        'aria-label="编辑分类"',
        'aria-label="删除分类"',
        "renderSystemClassificationPill",
        "renderRiskLevelPill",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_account_classification_css_defines_dossier_card_language() -> None:
    content = _read_text("app/static/css/pages/accounts/account-classification.css")

    required_fragments = (
        ".classification-card__masthead {",
        ".classification-card__identity {",
        ".classification-card__signals {",
        ".classification-card__code {",
        ".classification-card__actions .btn-icon {",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert ".classification-card__note {" not in content
    assert ".classification-card__meta {" not in content
