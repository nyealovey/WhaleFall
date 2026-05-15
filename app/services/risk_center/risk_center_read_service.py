"""Risk center read service.

Aggregates existing instance, backup, capacity, access, and task data into
card-ready DTOs for the DBA risk center.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from typing import Any, cast

from sqlalchemy import func, inspect

from app import db
from app.core.constants.status_types import TaskRunStatus
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.repositories.instances_repository import InstancesRepository
from app.repositories.jumpserver_repository import JumpServerRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.veeam.instance_backup_read_service import resolve_backup_status
from app.utils.time_utils import time_utils

SEVERITY_ORDER = {
    "critical": 0,
    "warning": 1,
    "info": 2,
    "unknown": 3,
    "ok": 4,
}
SEVERITY_SCORE = {
    "critical": 100,
    "warning": 50,
    "info": 10,
    "unknown": 1,
    "ok": 0,
}
VISIBLE_SEVERITY_KEYS = ("critical", "warning", "ok")
SEVERITY_TONE = {
    "critical": "danger",
    "warning": "warning",
    "info": "info",
    "unknown": "muted",
    "ok": "success",
}
SEVERITY_STATUS_TEXT = {
    "critical": "Critical",
    "warning": "Warning",
    "info": "Notice",
    "unknown": "Unknown",
    "ok": "Healthy",
}
BACKUP_STALE_HOURS = 24
CAPACITY_STALE_HOURS = 48
CAPACITY_WARNING_GROWTH_RATE = 30
CAPACITY_CRITICAL_GROWTH_RATE = 60
RECENT_WINDOW_HOURS = 24
AUDIT_INFO_CONFIG_KEY = "audit_info"
METRIC_RISK_CATEGORIES = {"backup", "audit", "managed"}


def _table_exists(table_name: str) -> bool:
    return inspect(db.engine).has_table(table_name)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _to_utc_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return time_utils.to_utc(value)
    if isinstance(value, str):
        return time_utils.to_utc(value)
    return None


def _format_age(value: datetime | None, *, now: datetime) -> str:
    if value is None:
        return "未知"
    delta = now - value
    if delta < timedelta(minutes=1):
        return "刚刚"
    if delta < timedelta(hours=1):
        return f"{max(int(delta.total_seconds() // 60), 1)}分钟前"
    if delta < timedelta(days=1):
        return f"{max(int(delta.total_seconds() // 3600), 1)}小时前"
    return f"{max(delta.days, 1)}天前"


def _format_size_mb(value: int | None) -> str:
    if value is None:
        return "未采集"
    if value >= 1024 * 1024:
        return f"{value / 1024 / 1024:.1f}TB"
    if value >= 1024:
        return f"{value / 1024:.1f}GB"
    return f"{value}MB"


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(cast(Any, value))
    except (TypeError, ValueError):
        return default


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _compact_task_name(value: object) -> str:
    name = str(value or "").strip()
    if name.endswith("任务"):
        return name.removesuffix("任务").strip() or name
    return name


def _task_failure_label(failed_task: TaskRunItem) -> str:
    run = getattr(failed_task, "run", None)
    task_name = _compact_task_name(getattr(run, "task_name", ""))
    if task_name:
        return task_name if task_name.endswith("失败") else f"{task_name}失败"

    task_key = str(getattr(run, "task_key", "") or "").strip().lower()
    if "account" in task_key:
        return "账户同步失败"
    if "database" in task_key or task_key.startswith("db_") or "_db_" in task_key:
        return "数据库同步失败"
    if "backup" in task_key or "veeam" in task_key:
        return "备份同步失败"
    return "定时任务失败"


def _visible_severity_bucket(severity: object) -> str:
    normalized = str(severity or "").strip()
    if normalized in {"critical", "warning"}:
        return normalized
    return "ok"


def _risk(
    *,
    category: str,
    severity: str,
    label: str,
    detail: str,
    occurred_at: datetime | None = None,
    target_url: str | None = None,
) -> dict[str, object]:
    return {
        "category": category,
        "severity": severity,
        "label": label,
        "detail": detail,
        "occurred_at": _iso(occurred_at),
        "target_url": target_url,
    }


class RiskCenterReadService:
    """Builds current-state risk center summaries and cards."""

    def build_summary(self) -> dict[str, object]:
        cards = self._build_cards()
        severity_counts = self._build_severity_counts(cards)
        db_type_counts: dict[str, dict[str, int]] = {}
        for card in cards:
            db_type = str(card["db_type"])
            db_type_counts.setdefault(db_type, {"total": 0, "critical": 0, "warning": 0, "ok": 0})
            db_type_counts[db_type]["total"] += 1
            db_type_counts[db_type][_visible_severity_bucket(card["overall_severity"])] += 1

        return {
            "total_instances": len(cards),
            "severity_counts": severity_counts,
            "db_type_counts": db_type_counts,
            "top_risks": cards[:8],
            "generated_at": time_utils.now().isoformat(),
        }

    def list_cards(
        self,
        *,
        severity: str = "",
        db_type: str = "",
        status: str = "",
        tag: str = "",
        search: str = "",
        page: int = 1,
        limit: int = 24,
    ) -> dict[str, object]:
        cards = self._build_cards()
        filtered = [
            card
            for card in cards
            if self._matches_filters(
                card,
                severity=severity,
                db_type=db_type,
                status=status,
                tag=tag,
                search=search,
            )
        ]
        safe_page = max(int(page or 1), 1)
        safe_limit = min(max(int(limit or 24), 1), 100)
        total = len(filtered)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
        return {
            "items": filtered[start:end],
            "total": total,
            "page": safe_page,
            "pages": max(ceil(total / safe_limit), 1),
            "limit": safe_limit,
        }

    def _build_cards(self) -> list[dict[str, object]]:
        instances = self._list_instances()
        if not instances:
            return []

        instance_ids = [int(instance.id) for instance in instances]
        now = time_utils.now()
        backup_map = VeeamRepository.fetch_backup_summary_map(instances)
        latest_capacity = self._latest_capacity_map(instance_ids)
        latest_growth = self._latest_growth_map(instance_ids)
        audit_map = self._audit_snapshot_map(instance_ids)
        managed_ids = JumpServerRepository.fetch_managed_instance_ids(instances)
        access_map = self._access_summary_map(instance_ids, since=now - timedelta(hours=RECENT_WINDOW_HOURS))
        failed_task_map = self._failed_task_map(instance_ids, since=now - timedelta(hours=RECENT_WINDOW_HOURS))
        tag_map = (
            InstancesRepository.fetch_tags_map(instance_ids)
            if _table_exists("tags") and _table_exists("instance_tags")
            else {}
        )

        cards = [
            self._build_card(
                instance=instance,
                now=now,
                backup=backup_map.get(int(instance.id), {}),
                capacity=latest_capacity.get(int(instance.id)),
                growth=latest_growth.get(int(instance.id)),
                audit=audit_map.get(int(instance.id)),
                managed=int(instance.id) in managed_ids,
                access=access_map.get(int(instance.id), {}),
                failed_task=failed_task_map.get(int(instance.id)),
                tags=tag_map.get(int(instance.id), []),
            )
            for instance in instances
        ]
        cards.sort(
            key=lambda item: (
                SEVERITY_ORDER.get(str(item["overall_severity"]), 99),
                -_as_int(item["risk_score"]),
                str(item["name"]).lower(),
            )
        )
        return cards

    def _build_card(
        self,
        *,
        instance: Instance,
        now: datetime,
        backup: dict[str, object],
        capacity: InstanceSizeStat | None,
        growth: InstanceSizeAggregation | None,
        audit: InstanceConfigSnapshot | None,
        managed: bool,
        access: dict[str, int],
        failed_task: TaskRunItem | None,
        tags: list[Any],
    ) -> dict[str, object]:
        risks: list[dict[str, object]] = []
        backup_metric, backup_risks = self._build_backup_metric(instance, backup, now=now)
        capacity_metric, capacity_risks = self._build_capacity_metric(instance, capacity, growth, now=now)
        audit_metric, audit_risks = self._build_audit_metric(instance, audit)
        managed_metric = self._build_managed_metric(instance, managed)
        access_metric, access_risks = self._build_access_metric(instance, access)
        task_metric, task_risks = self._build_task_metric(instance, failed_task)
        risks.extend(backup_risks)
        risks.extend(capacity_risks)
        risks.extend(audit_risks)
        risks.extend(access_risks)
        risks.extend(task_risks)
        if not bool(instance.is_active):
            risks.append(
                _risk(
                    category="instance",
                    severity="warning",
                    label="实例停用",
                    detail="实例当前处于停用状态",
                    target_url=f"/instances/{int(instance.id)}",
                )
            )

        overall = self._resolve_overall_severity(risks)
        risk_score = min(sum(SEVERITY_SCORE.get(str(risk["severity"]), 0) for risk in risks), 999)
        risk_flags = self._build_visible_risk_flags(risks)
        status_band = self._build_status_band(
            severity=overall,
            risks=risks,
            last_seen=self._resolve_last_seen(backup_metric, audit_metric, capacity_metric, task_metric),
            now=now,
        )
        tag_payload = [
            {"name": str(tag.name), "display_name": str(tag.display_name or tag.name)}
            for tag in tags
            if getattr(tag, "name", None)
        ]
        return {
            "instance_id": int(instance.id),
            "name": str(instance.name),
            "db_type": str(instance.db_type),
            "host": str(instance.host),
            "port": int(instance.port),
            "subtitle": f"{str(instance.db_type).upper()} · {instance.host}:{instance.port}",
            "status": "inactive" if not bool(instance.is_active) else "active",
            "overall_severity": overall,
            "risk_score": risk_score,
            "risk_flags": risk_flags,
            "risk_items": risks,
            "backup": backup_metric,
            "audit": audit_metric,
            "managed": managed_metric,
            "capacity": capacity_metric,
            "access": access_metric,
            "tasks": task_metric,
            "status_band": status_band,
            "tags": tag_payload,
            "links": {
                "detail": f"/instances/{int(instance.id)}",
                "backup": f"/instances/{int(instance.id)}#backup",
                "audit": f"/instances/{int(instance.id)}#audit",
                "capacity": f"/capacity/instances?instance_id={int(instance.id)}",
                "accounts": f"/accounts/ledgers?instance_id={int(instance.id)}",
                "tasks": f"/history/sessions?instance_id={int(instance.id)}",
            },
        }

    @staticmethod
    def _list_instances() -> list[Instance]:
        return (
            cast(Any, Instance.query)
            .filter(Instance.deleted_at.is_(None))
            .order_by(Instance.id.asc())
            .all()
        )

    @staticmethod
    def _build_severity_counts(cards: list[dict[str, object]]) -> dict[str, int]:
        counts = dict.fromkeys(VISIBLE_SEVERITY_KEYS, 0)
        for card in cards:
            counts[_visible_severity_bucket(card.get("overall_severity"))] += 1
        return counts

    @staticmethod
    def _matches_filters(
        card: dict[str, object],
        *,
        severity: str,
        db_type: str,
        status: str,
        tag: str,
        search: str,
    ) -> bool:
        severity_matches = True
        if severity and severity != "all":
            severity_matches = (
                _visible_severity_bucket(card["overall_severity"]) == "ok"
                if severity == "ok"
                else card["overall_severity"] == severity
            )
        db_type_matches = not (db_type and db_type != "all" and card["db_type"] != db_type)
        status_matches = not (status and status != "all" and card["status"] != status)
        tag_matches = True
        if tag:
            tags = card.get("tags")
            tag_names = {str(item.get("name")) for item in tags if isinstance(item, dict)} if isinstance(tags, list) else set()
            tag_matches = tag in tag_names
        search_matches = True
        if search:
            term = search.strip().lower()
            haystack = f"{card['name']} {card['host']} {card['db_type']}".lower()
            search_matches = not term or term in haystack
        return severity_matches and db_type_matches and status_matches and tag_matches and search_matches

    @staticmethod
    def _build_backup_metric(
        instance: Instance,
        backup: dict[str, object],
        *,
        now: datetime,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        latest_backup_at = _to_utc_datetime(backup.get("latest_backup_at") if isinstance(backup, dict) else None)
        status = resolve_backup_status(latest_backup_at=latest_backup_at.isoformat() if latest_backup_at else None)
        if status == "backed_up":
            return {
                "label": "24h内",
                "detail": "备份",
                "status": status,
                "tone": "success",
                "last_seen_at": _iso(latest_backup_at),
            }, []
        if status == "backup_stale":
            return {
                "label": "备份过期",
                "detail": "备份",
                "status": status,
                "tone": "warning",
                "last_seen_at": _iso(latest_backup_at),
            }, [
                _risk(
                    category="backup",
                    severity="warning",
                    label="备份滞后",
                    detail=f"最近备份为 {_format_age(latest_backup_at, now=now)}",
                    occurred_at=latest_backup_at,
                    target_url=f"/instances/{int(instance.id)}#backup",
                )
            ]
        return {
            "label": "未备份",
            "detail": "备份",
            "status": status,
            "tone": "danger",
            "last_seen_at": None,
        }, [
            _risk(
                category="backup",
                severity="critical",
                label="备份缺失",
                detail="未匹配到 Veeam 机器备份快照",
                target_url=f"/instances/{int(instance.id)}#backup",
            )
        ]

    @staticmethod
    def _build_audit_metric(
        instance: Instance,
        snapshot: InstanceConfigSnapshot | None,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        target_url = f"/instances/{int(instance.id)}#audit"
        facts = snapshot.facts if snapshot is not None and isinstance(snapshot.facts, dict) else {}
        has_audit = _as_bool(facts.get("has_audit")) if isinstance(facts, dict) else False
        enabled_count = _as_int(facts.get("enabled_audit_count")) if isinstance(facts, dict) else 0
        last_sync_at = _to_utc_datetime(snapshot.last_sync_time) if snapshot is not None else None

        if has_audit and enabled_count > 0:
            return {
                "label": "已启用",
                "detail": "审计",
                "tone": "success",
                "status": "enabled",
                "enabled_count": enabled_count,
                "last_seen_at": _iso(last_sync_at),
                "target_url": target_url,
            }, []
        if has_audit:
            return {
                "label": "未启用",
                "detail": "审计",
                "tone": "warning",
                "status": "configured_disabled",
                "enabled_count": enabled_count,
                "last_seen_at": _iso(last_sync_at),
                "target_url": target_url,
            }, [
                _risk(
                    category="audit",
                    severity="warning",
                    label="审计未启用",
                    detail="已发现审计配置，但当前没有启用的审计目标",
                    occurred_at=last_sync_at,
                    target_url=target_url,
                )
            ]
        return {
            "label": "未配置",
            "detail": "审计",
            "tone": "warning",
            "status": "not_configured",
            "enabled_count": 0,
            "last_seen_at": _iso(last_sync_at),
            "target_url": target_url,
        }, [
            _risk(
                category="audit",
                severity="warning",
                label="审计未配置",
                detail="未发现实例审计配置快照或审计目标",
                occurred_at=last_sync_at,
                target_url=target_url,
            )
        ]

    @staticmethod
    def _build_managed_metric(instance: Instance, managed: bool) -> dict[str, object]:
        target_url = f"/instances/{int(instance.id)}"
        if managed:
            return {
                "label": "已托管",
                "detail": "托管",
                "tone": "success",
                "status": "managed",
                "target_url": target_url,
            }
        return {
            "label": "未托管",
            "detail": "托管",
            "tone": "info",
            "status": "unmanaged",
            "target_url": target_url,
        }

    @staticmethod
    def _build_capacity_metric(
        instance: Instance,
        capacity: InstanceSizeStat | None,
        growth: InstanceSizeAggregation | None,
        *,
        now: datetime,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        if capacity is None:
            return {
                "label": "未采集",
                "detail": "Capacity",
                "tone": "muted",
                "status": "unknown",
                "last_seen_at": None,
            }, [
                _risk(
                    category="capacity",
                    severity="unknown",
                    label="容量未采集",
                    detail="缺少实例容量采集数据",
                    target_url=f"/capacity/instances?instance_id={int(instance.id)}",
                )
            ]

        risks: list[dict[str, object]] = []
        collected_at = _to_utc_datetime(capacity.collected_at)
        stale = collected_at is None or now - collected_at > timedelta(hours=CAPACITY_STALE_HOURS)
        raw_growth_rate = cast(Any, growth).growth_rate if growth is not None else None
        growth_rate = float(raw_growth_rate) if raw_growth_rate is not None else None
        growth_calculated_at = _to_utc_datetime(cast(Any, growth).calculated_at) if growth is not None else None
        tone = "success"
        label = _format_size_mb(int(capacity.total_size_mb or 0))
        status = "ok"
        if growth_rate is not None and growth_rate >= CAPACITY_CRITICAL_GROWTH_RATE:
            tone = "danger"
            label = f"+{growth_rate:.0f}%"
            status = "critical"
            risks.append(
                _risk(
                    category="capacity",
                    severity="critical",
                    label="容量增长过快",
                    detail=f"最近聚合增长率 {growth_rate:.0f}%",
                    occurred_at=growth_calculated_at,
                    target_url=f"/capacity/instances?instance_id={int(instance.id)}",
                )
            )
        elif growth_rate is not None and growth_rate >= CAPACITY_WARNING_GROWTH_RATE:
            tone = "warning"
            label = f"+{growth_rate:.0f}%"
            status = "warning"
            risks.append(
                _risk(
                    category="capacity",
                    severity="warning",
                    label="容量增长偏快",
                    detail=f"最近聚合增长率 {growth_rate:.0f}%",
                    occurred_at=growth_calculated_at,
                    target_url=f"/capacity/instances?instance_id={int(instance.id)}",
                )
            )
        if stale:
            tone = "warning" if tone == "success" else tone
            status = "warning" if status == "ok" else status
            risks.append(
                _risk(
                    category="capacity",
                    severity="warning",
                    label="容量采集过期",
                    detail=f"最近采集为 {_format_age(collected_at, now=now)}",
                    occurred_at=collected_at,
                    target_url=f"/capacity/instances?instance_id={int(instance.id)}",
                )
            )
        return {
            "label": label,
            "detail": "Capacity",
            "tone": tone,
            "status": status,
            "total_size_mb": int(capacity.total_size_mb or 0),
            "growth_rate": growth_rate,
            "last_seen_at": _iso(collected_at),
        }, risks

    @staticmethod
    def _build_access_metric(instance: Instance, access: dict[str, int]) -> tuple[dict[str, object], list[dict[str, object]]]:
        superuser_count = int(access.get("superuser_count", 0))
        locked_count = int(access.get("locked_count", 0))
        change_count = int(access.get("recent_change_count", 0))
        risks: list[dict[str, object]] = []
        label = "正常"
        tone = "success"
        if superuser_count > 0:
            label = f"{superuser_count} 高权"
            tone = "info"
            risks.append(
                _risk(
                    category="access",
                    severity="info",
                    label="存在高权账号",
                    detail=f"{superuser_count} 个账号具备超级权限",
                    target_url=f"/accounts/ledgers?instance_id={int(instance.id)}",
                )
            )
        if change_count > 0:
            if label == "正常":
                label = "有变更"
                tone = "warning"
            risks.append(
                _risk(
                    category="access",
                    severity="warning",
                    label="权限近期变更",
                    detail=f"最近 24 小时有 {change_count} 条账户变更",
                    target_url=f"/history/account-change-logs?instance_id={int(instance.id)}",
                )
            )
        return {
            "label": label,
            "detail": "Access",
            "tone": tone,
            "superuser_count": superuser_count,
            "locked_count": locked_count,
            "recent_change_count": change_count,
        }, risks

    @staticmethod
    def _build_task_metric(instance: Instance, failed_task: TaskRunItem | None) -> tuple[dict[str, object], list[dict[str, object]]]:
        if failed_task is None:
            return {
                "label": "正常",
                "detail": "定时任务",
                "tone": "success",
                "last_seen_at": None,
            }, []
        occurred_at = _to_utc_datetime(failed_task.started_at or failed_task.completed_at)
        failure_label = _task_failure_label(failed_task)
        return {
            "label": failure_label,
            "detail": "定时任务",
            "tone": "warning",
            "last_seen_at": _iso(occurred_at),
        }, [
            _risk(
                category="task",
                severity="warning",
                label=failure_label,
                detail=str(failed_task.error_message or failed_task.item_name or "最近 24 小时存在失败任务"),
                occurred_at=occurred_at,
                target_url=f"/history/sessions?instance_id={int(instance.id)}",
            )
        ]

    @staticmethod
    def _resolve_overall_severity(risks: list[dict[str, object]]) -> str:
        if not risks:
            return "ok"
        severities = [str(risk["severity"]) for risk in risks]
        return min(severities, key=lambda item: SEVERITY_ORDER.get(item, 99))

    @staticmethod
    def _build_visible_risk_flags(risks: list[dict[str, object]]) -> list[dict[str, object]]:
        return [risk for risk in risks if str(risk.get("category")) not in METRIC_RISK_CATEGORIES]

    @staticmethod
    def _resolve_last_seen(*metrics: dict[str, object]) -> datetime | None:
        candidates = [_to_utc_datetime(metric.get("last_seen_at")) for metric in metrics]
        resolved = [item for item in candidates if item is not None]
        return max(resolved) if resolved else None

    @staticmethod
    def _build_status_band(
        *,
        severity: str,
        risks: list[dict[str, object]],
        last_seen: datetime | None,
        now: datetime,
    ) -> dict[str, object]:
        tone = SEVERITY_TONE.get(severity, "muted")
        if severity == "ok":
            detail = f"最近同步 {_format_age(last_seen, now=now)}" if last_seen else "当前无风险"
        elif risks:
            detail = str(risks[0]["label"])
        else:
            detail = "缺少可判断数据"
        return {
            "label": f"{SEVERITY_STATUS_TEXT.get(severity, 'Unknown')} · {detail}",
            "tone": tone,
            "severity": severity,
        }

    @staticmethod
    def _latest_capacity_map(instance_ids: list[int]) -> dict[int, InstanceSizeStat]:
        if not instance_ids or not _table_exists(InstanceSizeStat.__tablename__):
            return {}
        latest_subquery = (
            db.session.query(
                InstanceSizeStat.instance_id.label("instance_id"),
                func.max(InstanceSizeStat.collected_at).label("latest_collected_at"),
            )
            .filter(InstanceSizeStat.instance_id.in_(instance_ids), InstanceSizeStat.is_deleted.is_(False))
            .group_by(InstanceSizeStat.instance_id)
            .subquery()
        )
        rows = (
            db.session.query(InstanceSizeStat)
            .join(
                latest_subquery,
                (InstanceSizeStat.instance_id == latest_subquery.c.instance_id)
                & (InstanceSizeStat.collected_at == latest_subquery.c.latest_collected_at),
            )
            .all()
        )
        return {_as_int(cast(Any, row).instance_id): row for row in rows}

    @staticmethod
    def _latest_growth_map(instance_ids: list[int]) -> dict[int, InstanceSizeAggregation]:
        if not instance_ids or not _table_exists(InstanceSizeAggregation.__tablename__):
            return {}
        latest_subquery = (
            db.session.query(
                InstanceSizeAggregation.instance_id.label("instance_id"),
                func.max(InstanceSizeAggregation.period_start).label("latest_period_start"),
            )
            .filter(InstanceSizeAggregation.instance_id.in_(instance_ids))
            .group_by(InstanceSizeAggregation.instance_id)
            .subquery()
        )
        rows = (
            db.session.query(InstanceSizeAggregation)
            .join(
                latest_subquery,
                (InstanceSizeAggregation.instance_id == latest_subquery.c.instance_id)
                & (InstanceSizeAggregation.period_start == latest_subquery.c.latest_period_start),
            )
            .all()
        )
        return {_as_int(cast(Any, row).instance_id): row for row in rows}

    @staticmethod
    def _audit_snapshot_map(instance_ids: list[int]) -> dict[int, InstanceConfigSnapshot]:
        if not instance_ids or not _table_exists(InstanceConfigSnapshot.__tablename__):
            return {}
        rows = (
            db.session.query(InstanceConfigSnapshot)
            .filter(
                InstanceConfigSnapshot.instance_id.in_(instance_ids),
                InstanceConfigSnapshot.config_key == AUDIT_INFO_CONFIG_KEY,
            )
            .all()
        )
        return {_as_int(cast(Any, row).instance_id): row for row in rows}

    @staticmethod
    def _access_summary_map(instance_ids: list[int], *, since: datetime) -> dict[int, dict[str, int]]:
        output = {instance_id: {"superuser_count": 0, "locked_count": 0, "recent_change_count": 0} for instance_id in instance_ids}
        if not instance_ids:
            return output
        if _table_exists(AccountPermission.__tablename__) and _table_exists(InstanceAccount.__tablename__):
            rows = (
                db.session.query(AccountPermission, InstanceAccount)
                .join(InstanceAccount, AccountPermission.instance_account_id == InstanceAccount.id)
                .filter(AccountPermission.instance_id.in_(instance_ids), InstanceAccount.is_active.is_(True))
                .all()
            )
            for permission, _account in rows:
                instance_id = int(permission.instance_id)
                if bool(permission.is_superuser):
                    output[instance_id]["superuser_count"] += 1
                if bool(permission.is_locked):
                    output[instance_id]["locked_count"] += 1
        if _table_exists(AccountChangeLog.__tablename__):
            change_rows = (
                db.session.query(AccountChangeLog.instance_id, func.count(AccountChangeLog.id))
                .filter(
                    AccountChangeLog.instance_id.in_(instance_ids),
                    AccountChangeLog.change_time >= since,
                    AccountChangeLog.status == "success",
                )
                .group_by(AccountChangeLog.instance_id)
                .all()
            )
            for instance_id, count in change_rows:
                output[int(instance_id)]["recent_change_count"] = int(count or 0)
        return output

    @staticmethod
    def _failed_task_map(instance_ids: list[int], *, since: datetime) -> dict[int, TaskRunItem]:
        if not instance_ids or not _table_exists(TaskRunItem.__tablename__) or not _table_exists(TaskRun.__tablename__):
            return {}
        rows = (
            db.session.query(TaskRunItem)
            .join(TaskRun, TaskRun.run_id == TaskRunItem.run_id)
            .filter(
                TaskRunItem.instance_id.in_(instance_ids),
                TaskRunItem.status == TaskRunStatus.FAILED,
                TaskRun.started_at >= since,
            )
            .order_by(TaskRun.started_at.desc(), TaskRunItem.id.desc())
            .all()
        )
        output: dict[int, TaskRunItem] = {}
        for row in rows:
            instance_id = _as_int(cast(Any, row).instance_id) if row.instance_id is not None else 0
            output.setdefault(instance_id, row)
        return output
