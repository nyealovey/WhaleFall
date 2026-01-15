import pathlib
import re

import pytest


_GET_OR_GET_PATTERN = re.compile(
    r"""\.get\(\s*['"][^'"]+['"]\s*(?:,[^)]*)?\)\s*or\s*[^#\n]*\.get\(\s*['"][^'"]""",
)


@pytest.mark.unit
def test_no_internal_payload_alias_fallback_chains_in_business_layers() -> None:
    roots = [
        pathlib.Path("app/services"),
        pathlib.Path("app/repositories"),
    ]

    bad: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if _GET_OR_GET_PATTERN.search(line):
                    bad.append(f"{path}:{lineno} {line.strip()}")

    assert not bad, "Found internal payload alias fallback chains:\n" + "\n".join(bad)

