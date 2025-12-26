"""通用资源表单服务基类.

---------------------------------
负责封装表单校验、模型赋值、数据库写入与统一的结果返回.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.types import (
    ContextDict,
    MutablePayloadDict,
    PayloadMapping,
    ResourceIdentifier,
    ResourcePayload,
    SupportsResourceId,
)

ResultT = TypeVar("ResultT")
ResourceT = TypeVar("ResourceT", bound=SupportsResourceId)


@dataclass(slots=True)
class ServiceResult(Generic[ResultT]):
    """统一的服务层返回结构.

    用于封装服务层操作的结果,包含成功状态、数据、消息和额外信息.

    Attributes:
        success: 操作是否成功.
        data: 返回的数据对象,失败时为 None.
        message: 返回消息,用于前端展示.
        message_key: 消息键,用于国际化.
        extra: 额外信息字典,用于传递详细错误或调试信息.

    """

    success: bool
    data: ResultT | None = None
    message: str | None = None
    message_key: str | None = None
    extra: MutablePayloadDict = field(default_factory=dict)

    @classmethod
    def ok(cls, data: ResultT, message: str | None = None) -> ServiceResult[ResultT]:
        """创建成功结果.

        Args:
            data: 返回的数据对象.
            message: 可选的成功消息.

        Returns:
            成功的 ServiceResult 实例.

        """
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(
        cls,
        message: str,
        *,
        message_key: str | None = None,
        extra: PayloadMapping | None = None,
    ) -> ServiceResult[ResultT]:
        """创建失败结果.

        Args:
            message: 错误消息.
            message_key: 可选的消息键,用于国际化.
            extra: 可选的额外信息字典.

        Returns:
            失败的 ServiceResult 实例.

        """
        payload = dict(extra) if extra else {}
        return cls(success=False, data=None, message=message, message_key=message_key, extra=payload)


class BaseResourceService(Generic[ResourceT]):
    """资源表单服务基类.

    提供通用的资源创建和更新流程,子类只需实现 validate、assign、after_save 等钩子即可.

    Attributes:
        model: 关联的模型类,子类必须设置.

    """

    model: type[ResourceT] | None = None

    def load(self, resource_id: ResourceIdentifier) -> ResourceT | None:
        """根据主键加载资源.

        Args:
            resource_id: 资源主键 ID.

        Returns:
            资源实例,不存在时返回 None.

        Raises:
            RuntimeError: 当 model 未配置时抛出.

        """
        if not self.model:
            msg = f"{self.__class__.__name__} 未配置 model"
            raise RuntimeError(msg)
        return self.model.query.get(resource_id)  # type: ignore[attr-defined]

    # --------------------------------------------------------------------- #
    # 钩子
    # --------------------------------------------------------------------- #
    def sanitize(self, payload: ResourcePayload) -> MutablePayloadDict:
        """清理原始请求数据,默认转换为普通字典.

        Args:
            payload: 原始请求数据.

        Returns:
            清理后的数据字典.

        """
        return dict(payload or {})

    def validate(self, data: MutablePayloadDict, *, resource: ResourceT | None) -> ServiceResult[MutablePayloadDict]:
        """子类应该实现具体校验逻辑.

        Args:
            data: 清理后的数据.
            resource: 已存在的资源实例(编辑场景),创建时为 None.

        Returns:
            校验结果,成功时返回清理后的数据,失败时返回错误信息.

        """
        del resource
        return ServiceResult.ok(data)

    def assign(self, instance: ResourceT, data: MutablePayloadDict) -> None:
        """将数据写入模型实例,必须由子类实现.

        Args:
            instance: 模型实例.
            data: 已校验的数据.

        Returns:
            None: 赋值完成后返回,具体逻辑由子类实现.

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """
        raise NotImplementedError

    def after_save(self, instance: ResourceT, data: MutablePayloadDict) -> None:
        """保存成功后的钩子(可选).

        Args:
            instance: 已保存的模型实例.
            data: 已校验的数据.

        Returns:
            None: 默认不进行任何操作,子类可覆盖.

        """
        del instance, data

    def build_context(self, *, resource: ResourceT | None) -> ContextDict:
        """提供模板渲染所需的额外上下文.

        Args:
            resource: 资源实例,创建时为 None.

        Returns:
            上下文字典.

        """
        del resource
        return {}

    # --------------------------------------------------------------------- #
    # 主流程
    # --------------------------------------------------------------------- #
    def upsert(self, payload: ResourcePayload, resource: ResourceT | None = None) -> ServiceResult[ResourceT]:
        """创建或更新资源.

        执行完整的资源保存流程:清理数据 -> 校验 -> 赋值 -> 保存 -> 后置钩子.

        Args:
            payload: 原始请求数据.
            resource: 已存在的实例(编辑场景),创建时为 None.

        Returns:
            ServiceResult 实例,成功时包含保存后的资源对象,失败时包含错误信息.

        """
        sanitized = self.sanitize(payload)
        validation = self.validate(sanitized, resource=resource)
        if not validation.success:
            return ServiceResult.fail(
                validation.message or "验证失败", message_key=validation.message_key, extra=validation.extra,
            )

        instance = resource or self._create_instance()
        self.assign(instance, validation.data or sanitized)

        try:
            db.session.add(instance)
            db.session.flush()
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.exception(
                "资源表单保存失败: %s",
                self.__class__.__name__,
            )
            return ServiceResult.fail("保存失败,请稍后再试", extra={"exception": str(exc)})

        self.after_save(instance, validation.data or sanitized)
        return ServiceResult.ok(instance)

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _create_instance(self) -> ResourceT:
        """创建新的模型实例.

        Returns:
            新创建的模型实例.

        Raises:
            RuntimeError: 当 model 未配置时抛出.

        """
        if not self.model:
            msg = f"{self.__class__.__name__} 未配置 model"
            raise RuntimeError(msg)
        return self.model()  # type: ignore[call-arg]
