from typing import Any, cast

import pytest

from app.core.exceptions import AppError
from app.services.account_classification.auto_classify_service import AutoClassifyService
from app.services.account_classification.cache import ClassificationCache
from app.services.account_classification.orchestrator import AccountClassificationService


@pytest.mark.unit
def test_orchestrator_get_permission_facts_missing_raises_explicit_error() -> None:
    class _StubAccount:
        permission_facts = None
        permission_snapshot = None

    with pytest.raises(AppError) as excinfo:
        AccountClassificationService._get_permission_facts(cast(Any, _StubAccount()))

    assert excinfo.value.message_key == "PERMISSION_FACTS_MISSING"


@pytest.mark.unit
def test_classification_cache_get_rules_accepts_only_wrapped_schema() -> None:
    rules_payload = [{"id": 1, "db_type": "mysql"}]

    class _StubManager:
        def __init__(self, payload: object) -> None:
            self._payload = payload

        def get_classification_rules_cache(self) -> object:
            return self._payload

    cache = ClassificationCache(manager=cast(Any, _StubManager({"rules": rules_payload})))
    assert cache.get_rules() == rules_payload

    legacy_cache = ClassificationCache(manager=cast(Any, _StubManager(rules_payload)))
    assert legacy_cache.get_rules() is None


@pytest.mark.unit
def test_auto_classify_service_does_not_wrap_app_error() -> None:
    class _StubOrchestrator:
        def auto_classify_accounts(self, *, instance_id: int | None, created_by: int | None) -> dict[str, object]:
            del instance_id, created_by
            raise AppError(message_key="PERMISSION_FACTS_MISSING")

    service = AutoClassifyService(classification_service=cast(Any, _StubOrchestrator()))
    with pytest.raises(AppError) as excinfo:
        service.auto_classify(instance_id=None, created_by=None)

    assert excinfo.value.message_key == "PERMISSION_FACTS_MISSING"
