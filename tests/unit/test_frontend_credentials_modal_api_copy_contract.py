"""凭据模态 API 文案契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_credential_modal_template_exposes_api_copy_targets() -> None:
    content = _read_text("app/templates/credentials/modals/credential-modals.html")

    required_fragments = (
        'id="credentialSubjectMeta"',
        'id="credentialUsernameLabelText"',
        'id="credentialPasswordLabelText"',
        'id="credentialPasswordHintText"',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_credential_modal_js_defines_api_copy_variants() -> None:
    content = _read_text("app/static/js/modules/views/credentials/modals/credential-modals.js")

    required_fragments = (
        "Access Key ID",
        "Access Key Secret",
        "输入 Access Key ID 与 Access Key Secret",
        "Access Key Secret 仅用于接口认证，数据将加密存储",
        "留空表示保持原 Access Key Secret",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_credential_validation_rules_switch_to_api_copy_and_live_selector() -> None:
    content = _read_text("app/static/js/common/validation-rules.js")

    required_fragments = (
        "fields['#credentialType']",
        "Access Key ID不能为空",
        "Access Key Secret不能为空",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "#credential_type" not in content
