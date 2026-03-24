from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_jumpserver_source_page_route_removed(auth_client) -> None:
    response = auth_client.get("/integrations/jumpserver/source")

    assert response.status_code == 404
