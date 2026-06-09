"""邮件告警事件服务."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from sqlalchemy.exc import IntegrityError

from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.repositories.instances_repository import InstancesRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.alerts.alert_event_candidates import DatabaseCapacityGrowthCandidate
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.services.cluster_status_sync.issue_contract import ClusterStatusDetectionResult
from app.services.veeam.instance_backup_read_service import resolve_backup_status
from app.utils.time_utils import time_utils

LOOKBACK_DAYS = 3


def _has_enabled_delivery_channel(settings: object) -> bool:
    return bool(getattr(settings, "global_enabled", False)) or bool(getattr(settings, "feishu_enabled", False))


class EmailAlertEventService:
    """邮件告警事件服务."""

    def __init__(
        self,
        repository: EmailAlertsRepository | Any | None = None,
        settings_service: EmailAlertSettingsService | Any | None = None,
        instances_repository: InstancesRepository | Any | None = None,
        veeam_repository: VeeamRepository | Any | None = None,
    ) -> None:
        self._repository = repository or EmailAlertsRepository()
        self._settings_service = settings_service or EmailAlertSettingsService()
        self._instances_repository = instances_repository or InstancesRepository()
        self._veeam_repository = veeam_repository or VeeamRepository()

    def record_database_capacity_events(
        self,
        *,
        current_rows: list[dict[str, object]],
        occurred_at: datetime | None = None,
    ) -> int:
        settings = self._settings_service.get_or_create_settings()
        if not _has_enabled_delivery_channel(settings) or not bool(settings.database_capacity_enabled):
            return 0

        resolved_occurred_at = occurred_at or time_utils.now()
        bucket_date = self._resolve_bucket_date(resolved_occurred_at)
        created = 0

        for row in current_rows:
            raw_database_name = row.get("database_name")
            current_collected_date = row.get("collected_date")
            raw_instance_id = row.get("instance_id")
            raw_size_mb = row.get("size_mb")
            if not isinstance(raw_database_name, str) or not raw_database_name.strip():
                continue
            if current_collected_date is None or raw_instance_id is None or raw_size_mb is None:
                continue
            instance_id = int(cast("int | str", raw_instance_id))
            database_name = raw_database_name.strip()
            current_date = cast(date, current_collected_date)
            baseline = self._repository.find_recent_database_baseline(
                instance_id=instance_id,
                database_name=database_name,
                current_collected_date=current_date,
                lookback_days=LOOKBACK_DAYS,
            )
            candidate = DatabaseCapacityGrowthCandidate.from_row(
                row=row,
                baseline=baseline,
                percent_threshold=int(settings.database_capacity_percent_threshold),
                absolute_gb_threshold=int(settings.database_capacity_absolute_gb_threshold),
                lookback_days=LOOKBACK_DAYS,
            )
            if candidate is None:
                continue

            if self._create_event(
                alert_type="database_capacity_growth",
                occurred_at=resolved_occurred_at,
                bucket_date=bucket_date,
                dedupe_key=candidate.dedupe_key,
                instance_id=candidate.instance_id,
                database_name=candidate.database_name,
                payload_json=candidate.payload_json(),
            ):
                created += 1

        return created

    def record_sync_failure_event(
        self,
        *,
        alert_type: str,
        instance_id: int,
        instance_name: str,
        run_id: str | None,
        session_id: str | None,
        error_message: str,
        occurred_at: datetime | None = None,
    ) -> bool:
        settings = self._settings_service.get_or_create_settings()
        if not _has_enabled_delivery_channel(settings):
            return False
        if alert_type == "account_sync_failure" and not bool(settings.account_sync_failure_enabled):
            return False
        if alert_type == "database_sync_failure" and not bool(settings.database_sync_failure_enabled):
            return False

        resolved_occurred_at = occurred_at or time_utils.now()
        return self._create_event(
            alert_type=alert_type,
            occurred_at=resolved_occurred_at,
            bucket_date=self._resolve_bucket_date(resolved_occurred_at),
            dedupe_key=f"{alert_type}:{run_id or 'no-run'}:{instance_id}",
            instance_id=instance_id,
            run_id=run_id,
            session_id=session_id,
            payload_json={
                "instance_id": instance_id,
                "instance_name": instance_name,
                "error_message": error_message,
            },
        )

    def record_privileged_account_event(
        self,
        *,
        instance_id: int,
        instance_name: str,
        username: str,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> bool:
        settings = self._settings_service.get_or_create_settings()
        if not _has_enabled_delivery_channel(settings) or not bool(settings.privileged_account_enabled):
            return False

        resolved_occurred_at = occurred_at or time_utils.now()
        return self._create_event(
            alert_type="privileged_account_discovery",
            occurred_at=resolved_occurred_at,
            bucket_date=self._resolve_bucket_date(resolved_occurred_at),
            dedupe_key=f"{instance_id}:{username}",
            instance_id=instance_id,
            username=username,
            payload_json={
                "instance_id": instance_id,
                "instance_name": instance_name,
                "username": username,
                "reason": reason,
            },
        )

    def sync_backup_issue_events_for_active_instances(
        self,
        *,
        occurred_at: datetime | None = None,
    ) -> int:
        instances = self._instances_repository.list_active_instances()
        backup_summary_map = self._veeam_repository.fetch_backup_summary_map(instances)
        backup_rows: list[dict[str, object]] = []
        for instance in instances:
            backup_summary = backup_summary_map.get(int(instance.id), {})
            latest_backup_at = backup_summary.get("latest_backup_at") if isinstance(backup_summary, dict) else None
            backup_last_time = latest_backup_at if isinstance(latest_backup_at, str) else None
            backup_rows.append(
                {
                    "instance_id": int(instance.id),
                    "instance_name": instance.name,
                    "backup_status": resolve_backup_status(latest_backup_at=backup_last_time),
                    "backup_last_time": backup_last_time,
                },
            )
        return self.record_backup_issue_events(backup_rows=backup_rows, occurred_at=occurred_at)

    def record_backup_issue_events(
        self,
        *,
        backup_rows: list[dict[str, object]],
        occurred_at: datetime | None = None,
    ) -> int:
        settings = self._settings_service.get_or_create_settings()
        if not _has_enabled_delivery_channel(settings) or not bool(getattr(settings, "backup_issue_enabled", False)):
            return 0

        resolved_occurred_at = occurred_at or time_utils.now()
        bucket_date = self._resolve_bucket_date(resolved_occurred_at)
        active_dedupe_keys: set[str] = set()
        created = 0

        for row in backup_rows:
            raw_instance_id = row.get("instance_id")
            if raw_instance_id is None:
                continue
            backup_status = str(row.get("backup_status") or "").strip()
            reason_text = self._resolve_backup_issue_reason_text(backup_status)
            if reason_text is None:
                continue

            instance_id = int(cast("int | str", raw_instance_id))
            dedupe_key = str(instance_id)
            active_dedupe_keys.add(dedupe_key)
            payload_json = {
                "instance_id": instance_id,
                "instance_name": row.get("instance_name"),
                "backup_status": backup_status,
                "backup_last_time": row.get("backup_last_time"),
                "reason_text": reason_text,
            }
            created_flag = self._repository.upsert_backup_issue_event(
                alert_type="backup_status_issue",
                occurred_at=resolved_occurred_at,
                bucket_date=bucket_date,
                dedupe_key=dedupe_key,
                instance_id=instance_id,
                payload_json=payload_json,
            )
            if created_flag:
                created += 1

        self._repository.delete_pending_backup_issue_events_not_in(
            bucket_date=bucket_date,
            dedupe_keys=active_dedupe_keys,
        )
        return created

    def record_cluster_status_event(
        self,
        *,
        cluster_type: str,
        cluster_id: int,
        cluster_name: str,
        run_id: str,
        result: dict[str, Any],
        occurred_at: datetime | None = None,
    ) -> bool:
        settings = self._settings_service.get_or_create_settings()
        if not _has_enabled_delivery_channel(settings) or not bool(getattr(settings, "cluster_status_enabled", False)):
            return False

        resolved_occurred_at = occurred_at or time_utils.now()
        bucket_date = self._resolve_bucket_date(resolved_occurred_at)
        detection = ClusterStatusDetectionResult.from_result(
            cluster_type=cluster_type,
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            run_id=run_id,
            result=result,
        )
        if not detection.is_abnormal:
            dedupe_key = detection.alert_dedupe_key
            self._repository.delete_pending_cluster_status_event(bucket_date=bucket_date, dedupe_key=dedupe_key)
            return False

        return bool(
            self._repository.upsert_cluster_status_event(
                alert_type="cluster_status_issue",
                occurred_at=resolved_occurred_at,
                bucket_date=bucket_date,
                dedupe_key=detection.alert_dedupe_key,
                run_id=run_id,
                payload_json=detection.alert_payload(),
            ),
        )

    def _create_event(self, **payload: object) -> bool:
        try:
            self._repository.create_event(**payload)
        except IntegrityError:
            return False
        return True

    @staticmethod
    def _resolve_bucket_date(occurred_at: datetime):
        china_time = time_utils.to_china(occurred_at)
        if china_time is None:
            return time_utils.now_china().date()
        return china_time.date()

    @staticmethod
    def _resolve_backup_issue_reason_text(backup_status: str) -> str | None:
        if backup_status == "not_backed_up":
            return "当天没有备份"
        if backup_status == "backup_stale":
            return "备份异常（最近备份超过24小时）"
        return None
