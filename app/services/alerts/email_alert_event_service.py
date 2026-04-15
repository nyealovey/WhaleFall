"""邮件告警事件服务."""

from __future__ import annotations

from datetime import date, datetime
from typing import cast

from sqlalchemy.exc import IntegrityError

from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.repositories.instances_repository import InstancesRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.services.veeam.instance_backup_read_service import resolve_backup_status
from app.utils.time_utils import time_utils

LOOKBACK_DAYS = 3
MB_PER_GB = 1024


class EmailAlertEventService:
    """邮件告警事件服务."""

    def __init__(
        self,
        repository: EmailAlertsRepository | None = None,
        settings_service: EmailAlertSettingsService | None = None,
        instances_repository: InstancesRepository | None = None,
        veeam_repository: VeeamRepository | None = None,
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
        if not bool(settings.global_enabled) or not bool(settings.database_capacity_enabled):
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
            if baseline is None:
                continue
            baseline_size_mb = cast(int, baseline.size_mb)
            baseline_collected_date = cast(date, baseline.collected_date)
            if baseline_size_mb <= 0:
                continue

            current_size_mb = int(cast("int | str", raw_size_mb))
            size_change_mb = current_size_mb - baseline_size_mb
            if size_change_mb <= 0:
                continue

            size_change_percent = round((size_change_mb / baseline_size_mb) * 100, 2)
            size_change_gb = size_change_mb / MB_PER_GB
            if size_change_percent < int(settings.database_capacity_percent_threshold):
                continue
            if size_change_gb < int(settings.database_capacity_absolute_gb_threshold):
                continue

            baseline_age_days = (current_date - baseline_collected_date).days
            if baseline_age_days < 1 or baseline_age_days > LOOKBACK_DAYS:
                continue

            if self._create_event(
                alert_type="database_capacity_growth",
                occurred_at=resolved_occurred_at,
                bucket_date=bucket_date,
                dedupe_key=f"{instance_id}:{database_name}",
                instance_id=instance_id,
                database_name=database_name,
                payload_json={
                    "instance_id": instance_id,
                    "instance_name": row.get("instance_name"),
                    "database_name": database_name,
                    "current_size_mb": current_size_mb,
                    "baseline_size_mb": baseline_size_mb,
                    "size_change_mb": size_change_mb,
                    "size_change_percent": size_change_percent,
                    "baseline_collected_date": baseline_collected_date.isoformat(),
                    "baseline_age_days": baseline_age_days,
                    "current_collected_date": current_date.isoformat(),
                },
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
        if not bool(settings.global_enabled):
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
        if not bool(settings.global_enabled) or not bool(settings.privileged_account_enabled):
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
        if not bool(settings.global_enabled) or not bool(getattr(settings, "backup_issue_enabled", False)):
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
