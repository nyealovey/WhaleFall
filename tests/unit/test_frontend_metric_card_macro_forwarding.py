from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.mark.unit
def test_frontend_metric_card_macro_forwards_call_block_content() -> None:
    """metric_card wrapper 需要支持 `{% call metric_card(...) %}...{% endcall %}` 语法."""

    repo_root = Path(__file__).resolve().parents[2]
    templates_root = repo_root / "app/templates"

    env = Environment(loader=FileSystemLoader(str(templates_root)))

    template = env.from_string(
        """
        {% from 'components/ui/macros.html' import metric_card %}
        {% call metric_card('Label', value='42', icon_class='fas fa-x') %}
            <span class="test-meta">Hello</span>
        {% endcall %}
        """
    )

    rendered = template.render()

    assert "wf-metric-card__meta" in rendered
    assert "Hello" in rendered

