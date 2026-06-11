from pathlib import Path

import pytest


def _write_console_dist(root: Path) -> None:
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True)
    (root / "index.html").write_text(
        '<!doctype html><html><body><div id="root"></div><script type="module" src="/console/assets/app.js"></script></body></html>',
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("window.__WHALEFALL_CONSOLE__ = true;", encoding="utf-8")


@pytest.mark.unit
def test_console_frontend_entry_and_spa_fallback_contract(app, client, tmp_path) -> None:
    dist_dir = tmp_path / "console-dist"
    _write_console_dist(dist_dir)
    app.config["CONSOLE_FRONTEND_DIST_DIR"] = str(dist_dir)

    entry_response = client.get("/console")
    assert entry_response.status_code == 200
    assert b'id="root"' in entry_response.data
    assert b"/console/assets/app.js" in entry_response.data

    nested_response = client.get("/console/instances")
    assert nested_response.status_code == 200
    assert nested_response.data == entry_response.data

    asset_response = client.get("/console/assets/app.js")
    assert asset_response.status_code == 200
    assert b"__WHALEFALL_CONSOLE__" in asset_response.data


@pytest.mark.unit
def test_console_frontend_does_not_replace_existing_login_page(client) -> None:
    response = client.get("/auth/login")

    assert response.status_code == 200
    assert b"/console/assets/" not in response.data
    assert b"app/static" not in response.data
