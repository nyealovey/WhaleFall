import pytest
from flask import Flask
from werkzeug.datastructures import MultiDict

from app.utils.request_payload import parse_payload


@pytest.mark.unit
def test_parse_payload_multidict_trims_strings_by_default() -> None:
    payload: MultiDict[str, str] = MultiDict([("username", "  alice  ")])
    sanitized = parse_payload(payload)
    assert sanitized["username"] == "alice"


@pytest.mark.unit
def test_parse_payload_multidict_preserves_password_raw_value() -> None:
    payload: MultiDict[str, str] = MultiDict([("password", "  Pass 1A  ")])
    sanitized = parse_payload(payload, preserve_raw_fields=["password"])
    assert sanitized["password"] == "  Pass 1A  "


@pytest.mark.unit
def test_parse_payload_multidict_list_fields_are_always_list() -> None:
    payload: MultiDict[str, str] = MultiDict([("tag_names", "  foo  ")])
    sanitized = parse_payload(payload, list_fields=["tag_names"])
    assert sanitized["tag_names"] == ["foo"]


@pytest.mark.unit
def test_parse_payload_multidict_non_list_fields_take_last_value() -> None:
    payload: MultiDict[str, str] = MultiDict([("username", "alice"), ("username", "bob")])
    sanitized = parse_payload(payload)
    assert sanitized["username"] == "bob"


@pytest.mark.unit
def test_parse_payload_mapping_list_field_accepts_scalar_and_list() -> None:
    sanitized = parse_payload({"tag_names": "  foo  "}, list_fields=["tag_names"])
    assert sanitized["tag_names"] == ["foo"]

    sanitized = parse_payload({"tag_names": ["  foo  ", "bar"]}, list_fields=["tag_names"])
    assert sanitized["tag_names"] == ["foo", "bar"]


@pytest.mark.unit
def test_parse_payload_sets_missing_boolean_fields_to_false_for_multidict() -> None:
    payload: MultiDict[str, str] = MultiDict([("username", "alice")])
    sanitized = parse_payload(payload, boolean_fields_default_false=["is_active"])
    assert sanitized["is_active"] is False


@pytest.mark.unit
def test_parse_payload_guard_allows_single_call_per_request() -> None:
    app = Flask(__name__)
    with app.test_request_context("/"):
        sanitized = parse_payload({"username": "alice"})
        assert sanitized["username"] == "alice"

    with app.test_request_context("/"):
        sanitized = parse_payload({"username": "bob"})
        assert sanitized["username"] == "bob"


@pytest.mark.unit
def test_parse_payload_guard_raises_when_called_twice_in_request() -> None:
    app = Flask(__name__)
    with app.test_request_context("/"):
        parse_payload({"username": "alice"})
        with pytest.raises(RuntimeError, match="parse_payload"):
            parse_payload({"username": "bob"})
