"""风险中心规则配置服务."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect

from app import db
from app.core.exceptions import ValidationError
from app.models.risk_center_rule_setting import RiskCenterRuleSetting
from app.schemas.risk_center import RiskCenterRulesUpdatePayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload

RISK_SEVERITIES = {"high", "medium", "low"}


@dataclass(frozen=True)
class RiskRuleDefinition:
    """内置风险规则定义."""

    rule_key: str
    category: str
    label: str
    description: str
    default_severity: str


RISK_RULE_DEFINITIONS: tuple[RiskRuleDefinition, ...] = (
    RiskRuleDefinition("backup_missing", "backup", "备份缺失", "未匹配到 Veeam 机器备份快照", "high"),
    RiskRuleDefinition("backup_stale", "backup", "备份滞后", "最近备份超过 24 小时", "medium"),
    RiskRuleDefinition("capacity_growth_critical", "capacity", "容量增长过快", "容量聚合增长率超过高风险阈值", "high"),
    RiskRuleDefinition("capacity_growth_warning", "capacity", "容量增长偏快", "容量聚合增长率超过中风险阈值", "medium"),
    RiskRuleDefinition("audit_disabled", "audit", "审计未启用", "发现审计配置但没有启用目标", "medium"),
    RiskRuleDefinition("audit_missing", "audit", "审计未配置", "未发现实例审计配置快照或审计目标", "medium"),
    RiskRuleDefinition("access_superuser", "access", "存在高权账号", "账号具备超级权限", "low"),
    RiskRuleDefinition("access_recent_change", "access", "权限近期变更", "最近 24 小时有账户变更", "medium"),
    RiskRuleDefinition("cluster_abnormal", "cluster", "群集异常", "副节点实例存在群集同步或复制异常", "medium"),
    RiskRuleDefinition("task_failed", "task", "定时任务失败", "最近 24 小时存在失败任务", "medium"),
)

RISK_RULE_DEFINITION_MAP = {definition.rule_key: definition for definition in RISK_RULE_DEFINITIONS}


def _rule_table_exists() -> bool:
    return inspect(db.engine).has_table(RiskCenterRuleSetting.__tablename__)


class RiskCenterRuleSettingsService:
    """读取和保存风险中心规则配置."""

    @staticmethod
    def build_default_map() -> dict[str, dict[str, object]]:
        return {
            definition.rule_key: {
                "rule_key": definition.rule_key,
                "category": definition.category,
                "label": definition.label,
                "description": definition.description,
                "default_severity": definition.default_severity,
                "severity": definition.default_severity,
                "enabled": True,
            }
            for definition in RISK_RULE_DEFINITIONS
        }

    def get_rule_map(self) -> dict[str, dict[str, object]]:
        rules = self.build_default_map()
        if not _rule_table_exists():
            return rules

        rows = RiskCenterRuleSetting.query.all()
        for row in rows:
            rule = rules.get(str(row.rule_key))
            if rule is None:
                continue
            severity = str(row.severity or "").strip()
            rule["enabled"] = bool(row.enabled)
            rule["severity"] = severity if severity in RISK_SEVERITIES else rule["default_severity"]
        return rules

    def list_rules(self) -> dict[str, object]:
        rules = self.get_rule_map()
        return {"rules": [rules[definition.rule_key] for definition in RISK_RULE_DEFINITIONS]}

    def update_rules(self, payload: object) -> dict[str, object]:
        sanitized = parse_payload(payload, list_fields=["rules"])
        parsed = validate_or_raise(RiskCenterRulesUpdatePayload, sanitized)
        if not _rule_table_exists():
            raise ValidationError("风险规则配置表尚未初始化")

        for raw_item in parsed.rules:
            rule_key = raw_item.rule_key
            definition = RISK_RULE_DEFINITION_MAP.get(rule_key)
            if definition is None:
                raise ValidationError(f"未知风险规则: {rule_key}")
            severity = raw_item.severity

            setting = RiskCenterRuleSetting.query.filter(RiskCenterRuleSetting.rule_key == rule_key).first()
            if setting is None:
                setting = RiskCenterRuleSetting()
                setting.rule_key = rule_key
                db.session.add(setting)
            setting.enabled = raw_item.enabled
            setting.severity = severity

        db.session.commit()
        return self.list_rules()

    def resolve_rule(self, rule_key: str, rule_map: dict[str, dict[str, object]] | None = None) -> dict[str, object]:
        rules = rule_map or self.get_rule_map()
        rule = rules.get(rule_key)
        if rule is not None:
            return rule
        return {
            "rule_key": rule_key,
            "category": "other",
            "label": rule_key,
            "description": "",
            "default_severity": "medium",
            "severity": "medium",
            "enabled": True,
        }
