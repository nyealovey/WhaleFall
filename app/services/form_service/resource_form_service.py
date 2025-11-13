"""
通用资源表单服务基类
---------------------------------
负责封装表单校验、模型赋值、数据库提交与统一的结果返回。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Mapping, TypeVar

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db

TModel = TypeVar("TModel")


@dataclass(slots=True)
class ServiceResult(Generic[TModel]):
    """统一的服务层返回结构。"""

    success: bool
    data: TModel | None = None
    message: str | None = None
    message_key: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: TModel, message: str | None = None) -> "ServiceResult[TModel]":
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(
        cls,
        message: str,
        *,
        message_key: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> "ServiceResult[Any]":
        payload = dict(extra) if extra else {}
        return cls(success=False, data=None, message=message, message_key=message_key, extra=payload)


class BaseResourceService(Generic[TModel]):
    """
    资源表单服务基类。

    子类只需实现 validate/assign/after_save 等钩子即可。
    """

    model: type[TModel] | None = None

    def load(self, resource_id: int) -> TModel | None:
        """根据主键加载资源。"""
        if not self.model:
            raise RuntimeError(f"{self.__class__.__name__} 未配置 model")
        return self.model.query.get(resource_id)  # type: ignore[attr-defined]

    # --------------------------------------------------------------------- #
    # 钩子
    # --------------------------------------------------------------------- #
    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理原始请求数据，默认转换为普通字典。"""
        return dict(payload or {})

    def validate(self, data: dict[str, Any], *, resource: TModel | None) -> ServiceResult[dict[str, Any]]:
        """子类应该实现具体校验逻辑。"""
        return ServiceResult.ok(data)

    def assign(self, instance: TModel, data: dict[str, Any]) -> None:
        """将数据写入模型实例，必须由子类实现。"""
        raise NotImplementedError

    def after_save(self, instance: TModel, data: dict[str, Any]) -> None:  # noqa: D401
        """保存成功后的钩子（可选）。"""
        return None

    def build_context(self, *, resource: TModel | None) -> dict[str, Any]:
        """提供模板渲染所需的额外上下文。"""
        return {}

    # --------------------------------------------------------------------- #
    # 主流程
    # --------------------------------------------------------------------- #
    def upsert(self, payload: Mapping[str, Any], resource: TModel | None = None) -> ServiceResult[TModel]:
        """
        创建或更新资源。

        Args:
            payload: 原始请求数据
            resource: 已存在的实例（编辑场景）
        """
        sanitized = self.sanitize(payload)
        validation = self.validate(sanitized, resource=resource)
        if not validation.success:
            return ServiceResult.fail(validation.message or "验证失败", message_key=validation.message_key, extra=validation.extra)

        instance = resource or self._create_instance()
        self.assign(instance, validation.data or sanitized)

        try:
            db.session.add(instance)
            db.session.commit()
        except SQLAlchemyError as exc:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.exception(f"资源表单保存失败: {self.__class__.__name__}")
            return ServiceResult.fail("保存失败，请稍后再试", extra={"exception": str(exc)})

        self.after_save(instance, validation.data or sanitized)
        return ServiceResult.ok(instance)

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _create_instance(self) -> TModel:
        if not self.model:
            raise RuntimeError(f"{self.__class__.__name__} 未配置 model")
        return self.model()  # type: ignore[call-arg]
