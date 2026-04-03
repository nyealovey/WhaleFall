"""update-prod-flask Nginx sync contracts."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_update_prod_flask_preserves_existing_nginx_site_config_by_default() -> None:
    content = _read_text("scripts/deploy/update-prod-flask.sh")

    required_fragments = (
        "--sync-nginx-site-config",
        'FORCE_SYNC_NGINX_SITE_CONFIG="${FORCE_SYNC_NGINX_SITE_CONFIG:-0}"',
        "force_sync=${FORCE_SYNC_NGINX_SITE_CONFIG}",
        '\\"\\$force_sync\\" != \\"1\\"',
        "保留现有 Nginx 站点配置",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_hot_update_guide_documents_explicit_nginx_sync_override() -> None:
    content = _read_text("docs/Obsidian/operations/hot-update/hot-update-guide.md")

    required_fragments = (
        "默认保留容器内现有 Nginx 站点配置",
        "--sync-nginx-site-config",
    )

    for fragment in required_fragments:
        assert fragment in content
