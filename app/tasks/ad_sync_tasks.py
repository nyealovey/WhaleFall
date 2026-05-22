"""AD 域账户同步任务."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import structlog

from app import create_app, db
from app.core.constants.status_types import TaskRunStatus
from app.core.exceptions import ValidationError
from app.models.ad_domain_config import AdDomainConfig
from app.models.task_run import TaskRun
from app.repositories.ad_domain_config_repository import AdDomainConfigRepository
from app.services.ad_sync.ad_account_match_service import AdAccountMatchService, AdDomainMatchResult
from app.services.ad_sync.ldap_provider import AdPrincipalsFetchResult, LdapProvider
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

AD_SYNC_EXCEPTIONS: tuple[type[Exception], ...] = (
    ValidationError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)


@dataclass(frozen=True, slots=True)
class AdFetchTotals:
    """AD LDAP 拉取数量汇总."""

    users: int = 0
    groups: int = 0

    @property
    def principals(self) -> int:
        return self.users + self.groups


def _resolve_run_id(
    *,
    task_runs_service: TaskRunsWriteService,
    manual_run: bool,
    created_by: int | None,
    run_id: str | None,
) -> str:
    if run_id:
        existing_run = TaskRun.query.filter_by(run_id=run_id).first()
        if existing_run is None:
            raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": run_id})
        return run_id
    resolved_run_id = task_runs_service.start_run(
        task_key="sync_ad_accounts",
        task_name="AD 域账户同步",
        task_category="ad_sync",
        trigger_source="manual" if manual_run else "scheduled",
        created_by=created_by,
        result_url="/accounts/ledgers?ad_status=disabled",
    )
    db.session.commit()
    return resolved_run_id


def _init_items(*, task_runs_service: TaskRunsWriteService, run_id: str, domains: list[AdDomainConfig]) -> None:
    task_runs_service.init_items(
        run_id,
        items=[
            TaskRunItemInit(
                item_type="ad_domain",
                item_key=str(domain.id),
                item_name=domain.name,
            )
            for domain in domains
        ],
    )
    db.session.commit()


def _summary(
    *,
    domains_total: int,
    domains_successful: int,
    domains_failed: int,
    totals: AdDomainMatchResult,
    fetch_totals: AdFetchTotals,
) -> dict[str, object]:
    return {
        "version": 1,
        "task_key": "sync_ad_accounts",
        "status": "ok",
        "ext": {
            "type": "sync_ad_accounts",
            "domains_total": domains_total,
            "domains_successful": domains_successful,
            "domains_failed": domains_failed,
            "accounts_total": totals.total,
            "accounts_normal": totals.normal,
            "accounts_disabled": totals.disabled,
            "accounts_orphaned": totals.orphaned,
            "accounts_updated": totals.updated,
            "ad_users_total": fetch_totals.users,
            "ad_groups_total": fetch_totals.groups,
            "ad_principals_total": fetch_totals.principals,
        },
    }


def _add_results(left: AdDomainMatchResult, right: AdDomainMatchResult) -> AdDomainMatchResult:
    return AdDomainMatchResult(
        total=left.total + right.total,
        normal=left.normal + right.normal,
        disabled=left.disabled + right.disabled,
        orphaned=left.orphaned + right.orphaned,
        updated=left.updated + right.updated,
    )


def _add_fetch_totals(left: AdFetchTotals, right: AdPrincipalsFetchResult) -> AdFetchTotals:
    return AdFetchTotals(
        users=left.users + right.users_total,
        groups=left.groups + right.groups_total,
    )


def _metrics(result: AdDomainMatchResult, fetch_result: AdPrincipalsFetchResult) -> dict[str, object]:
    metrics: dict[str, object] = asdict(result)
    metrics.update(
        {
            "ad_users_total": fetch_result.users_total,
            "ad_groups_total": fetch_result.groups_total,
            "ad_principals_total": fetch_result.principals_total,
        }
    )
    return metrics


def _sync_domain(
    *,
    domain: AdDomainConfig,
    run_id: str,
    provider: LdapProvider,
    matcher: AdAccountMatchService,
    task_runs_service: TaskRunsWriteService,
) -> tuple[AdDomainMatchResult, AdPrincipalsFetchResult]:
    item_key = str(domain.id)
    task_runs_service.start_item(run_id, item_type="ad_domain", item_key=item_key)
    db.session.commit()

    fetch_result = provider.fetch_principals_with_stats(domain)
    result = matcher.match_and_update(domain_config=domain, principals=fetch_result.principals)
    domain.last_sync_at = time_utils.now()
    domain.last_sync_status = "success"
    domain.last_sync_run_id = run_id
    domain.last_error = None
    task_runs_service.complete_item(
        run_id,
        item_type="ad_domain",
        item_key=item_key,
        metrics_json=_metrics(result, fetch_result),
    )
    db.session.commit()
    return result, fetch_result


def _fail_domain(
    *,
    domain: AdDomainConfig,
    run_id: str,
    exc: Exception,
    task_runs_service: TaskRunsWriteService,
    sync_logger: structlog.BoundLogger,
) -> None:
    db.session.rollback()
    reloaded_domain = db.session.get(AdDomainConfig, domain.id)
    if reloaded_domain is not None:
        reloaded_domain.last_sync_at = time_utils.now()
        reloaded_domain.last_sync_status = "failed"
        reloaded_domain.last_sync_run_id = run_id
        reloaded_domain.last_error = str(exc)
    task_runs_service.fail_item(
        run_id,
        item_type="ad_domain",
        item_key=str(domain.id),
        error_message=str(exc),
    )
    sync_logger.exception(
        "ad_domain_sync_failed",
        module="ad_sync",
        operation="sync_ad_accounts",
        run_id=run_id,
        domain_id=domain.id,
        domain_name=domain.name,
    )
    db.session.commit()


def _finalize_run(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    domains_total: int,
    domains_successful: int,
    domains_failed: int,
    totals: AdDomainMatchResult,
    fetch_totals: AdFetchTotals,
) -> None:
    run = TaskRun.query.filter_by(run_id=run_id).first()
    if run is not None:
        run.summary_json = _summary(
            domains_total=domains_total,
            domains_successful=domains_successful,
            domains_failed=domains_failed,
            totals=totals,
            fetch_totals=fetch_totals,
        )
    task_runs_service.finalize_run(run_id)
    run = TaskRun.query.filter_by(run_id=run_id).first()
    if run is not None and domains_failed and domains_successful:
        run.status = TaskRunStatus.COMPLETED_WITH_ERRORS
    db.session.commit()


def sync_ad_accounts(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    **_: Any,
) -> None:
    """同步 AD 域账户状态并标记 SQL Server 域账户风险."""
    del session_id
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_runs_service = TaskRunsWriteService()
        resolved_run_id = _resolve_run_id(
            task_runs_service=task_runs_service,
            manual_run=manual_run,
            created_by=created_by,
            run_id=run_id,
        )
        domains = AdDomainConfigRepository.list_configs(enabled_only=True)
        _init_items(task_runs_service=task_runs_service, run_id=resolved_run_id, domains=domains)
        provider = LdapProvider()
        matcher = AdAccountMatchService()
        totals = AdDomainMatchResult(total=0, normal=0, disabled=0, orphaned=0, updated=0)
        fetch_totals = AdFetchTotals()
        successful = failed = 0
        for domain in domains:
            try:
                result, fetch_result = _sync_domain(
                    domain=domain,
                    run_id=resolved_run_id,
                    provider=provider,
                    matcher=matcher,
                    task_runs_service=task_runs_service,
                )
                totals = _add_results(totals, result)
                fetch_totals = _add_fetch_totals(fetch_totals, fetch_result)
                successful += 1
            except AD_SYNC_EXCEPTIONS as exc:
                failed += 1
                _fail_domain(
                    domain=domain,
                    run_id=resolved_run_id,
                    exc=exc,
                    task_runs_service=task_runs_service,
                    sync_logger=sync_logger,
                )
        _finalize_run(
            task_runs_service=task_runs_service,
            run_id=resolved_run_id,
            domains_total=len(domains),
            domains_successful=successful,
            domains_failed=failed,
            totals=totals,
            fetch_totals=fetch_totals,
        )
