"""Cache namespace (Phase 4A 缓存管理)."""

from __future__ import annotations

from typing import ClassVar

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields

import app.services.cache_service as cache_service_module
from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.errors import ConflictError, NotFoundError, SystemError, ValidationError
from app.models.instance import Instance
from app.services.account_classification.orchestrator import AccountClassificationService
from app.utils.decorators import require_csrf
from app.utils.route_safety import log_with_context
from app.utils.structlog_config import log_info

ns = Namespace("cache", description="缓存管理")

ErrorEnvelope = get_error_envelope_model(ns)

CacheStatsData = ns.model(
    "CacheStatsData",
    {
        "stats": fields.Raw(required=True, description="缓存统计信息"),
    },
)

CacheStatsSuccessEnvelope = make_success_envelope_model(ns, "CacheStatsSuccessEnvelope", CacheStatsData)

CacheClearAllData = ns.model(
    "CacheClearAllData",
    {
        "cleared_count": fields.Integer(required=True),
    },
)

CacheClearAllSuccessEnvelope = make_success_envelope_model(ns, "CacheClearAllSuccessEnvelope", CacheClearAllData)

CacheClassificationStatsData = ns.model(
    "CacheClassificationStatsData",
    {
        "cache_stats": fields.Raw(required=True),
        "db_type_stats": fields.Raw(required=True),
        "cache_enabled": fields.Boolean(required=True),
    },
)

CacheClassificationStatsSuccessEnvelope = make_success_envelope_model(
    ns,
    "CacheClassificationStatsSuccessEnvelope",
    CacheClassificationStatsData,
)


def _require_cache_service():
    manager = cache_service_module.cache_service
    if manager is None:
        raise SystemError("缓存服务未初始化")
    return manager


@ns.route("/stats")
class CacheStatsResource(BaseResource):
    """缓存统计资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", CacheStatsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取缓存统计."""

        def _execute():
            manager = _require_cache_service()
            stats = manager.get_cache_stats()
            return self.success(data={"stats": stats}, message="缓存统计获取成功")

        return self.safe_call(
            _execute,
            module="cache",
            action="get_cache_stats",
            public_error="获取缓存统计失败",
            context={"endpoint": "stats"},
        )


ClearUserCachePayload = ns.model(
    "ClearUserCachePayload",
    {
        "instance_id": fields.Integer(required=True),
        "username": fields.String(required=True),
    },
)


@ns.route("/actions/clear-user")
class CacheClearUserResource(BaseResource):
    """用户缓存清除资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.expect(ClearUserCachePayload, validate=False)
    @ns.response(200, "OK", make_success_envelope_model(ns, "CacheClearUserSuccessEnvelope"))
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """清除用户缓存."""
        payload = request.get_json(silent=True) or {}

        def _execute():
            manager = _require_cache_service()
            instance_id = payload.get("instance_id")
            username = payload.get("username")
            if not instance_id or not username:
                raise ValidationError("缺少必要参数: instance_id 和 username")

            instance = Instance.query.get(instance_id)
            if not instance:
                raise NotFoundError("实例不存在")

            success = manager.invalidate_user_cache(instance_id, username)
            if not success:
                raise ConflictError("用户缓存清除失败")

            log_info(
                "用户缓存清除成功",
                module="cache",
                instance_id=instance_id,
                username=username,
                operator_id=getattr(current_user, "id", None),
            )
            return self.success(message="用户缓存清除成功")

        return self.safe_call(
            _execute,
            module="cache",
            action="clear_user_cache",
            public_error="清除用户缓存失败",
            context={"instance_id": payload.get("instance_id"), "username": payload.get("username")},
            expected_exceptions=(ValidationError, NotFoundError, ConflictError),
        )


ClearInstanceCachePayload = ns.model(
    "ClearInstanceCachePayload",
    {
        "instance_id": fields.Integer(required=True),
    },
)


@ns.route("/actions/clear-instance")
class CacheClearInstanceResource(BaseResource):
    """实例缓存清除资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.expect(ClearInstanceCachePayload, validate=False)
    @ns.response(200, "OK", make_success_envelope_model(ns, "CacheClearInstanceSuccessEnvelope"))
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """清除实例缓存."""
        payload = request.get_json(silent=True) or {}

        def _execute():
            manager = _require_cache_service()
            instance_id = payload.get("instance_id")
            if not instance_id:
                raise ValidationError("缺少必要参数: instance_id")

            instance = Instance.query.get(instance_id)
            if not instance:
                raise NotFoundError("实例不存在")

            success = manager.invalidate_instance_cache(instance_id)
            if not success:
                raise ConflictError("实例缓存清除失败")

            log_info(
                "实例缓存清除成功",
                module="cache",
                instance_id=instance_id,
                operator_id=getattr(current_user, "id", None),
            )
            return self.success(message="实例缓存清除成功")

        return self.safe_call(
            _execute,
            module="cache",
            action="clear_instance_cache",
            public_error="清除实例缓存失败",
            context={"instance_id": payload.get("instance_id")},
            expected_exceptions=(ValidationError, NotFoundError, ConflictError),
        )


@ns.route("/actions/clear-all")
class CacheClearAllResource(BaseResource):
    """全量缓存清除资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", CacheClearAllSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """清除所有缓存."""

        def _execute():
            manager = _require_cache_service()
            instances = Instance.query.filter_by(is_active=True).all()

            cleared_count = 0
            for instance in instances:
                try:
                    if manager.invalidate_instance_cache(instance.id):
                        cleared_count += 1
                except cache_service_module.CACHE_EXCEPTIONS as exc:
                    log_with_context(
                        "error",
                        "清除实例缓存失败",
                        module="cache",
                        action="clear_all_cache",
                        context={"instance_id": instance.id},
                        extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                    )

            log_info(
                "批量清除缓存完成",
                module="cache",
                cleared_count=cleared_count,
                operator_id=getattr(current_user, "id", None),
            )
            return self.success(
                data={"cleared_count": cleared_count},
                message=f"已清除 {cleared_count} 个实例的缓存",
            )

        return self.safe_call(
            _execute,
            module="cache",
            action="clear_all_cache",
            public_error="清除所有缓存失败",
            context={"scope": "all_instances"},
        )


ClearClassificationCachePayload = ns.model(
    "ClearClassificationCachePayload",
    {
        "db_type": fields.String(required=False, description="数据库类型(可选)"),
    },
)


@ns.route("/actions/clear-classification")
class CacheClearClassificationActionResource(BaseResource):
    """分类缓存清除动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("update")]

    @ns.expect(ClearClassificationCachePayload, validate=False)
    @ns.response(200, "OK", make_success_envelope_model(ns, "CacheClearClassificationSuccessEnvelope"))
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """清除分类缓存."""
        payload = request.get_json(silent=True) or {}

        def _execute():
            db_type_raw = (payload.get("db_type") or "").strip()
            if db_type_raw:
                valid_db_types = {"mysql", "postgresql", "sqlserver", "oracle"}
                normalized_type = db_type_raw.lower()
                if normalized_type not in valid_db_types:
                    raise ValidationError(f"不支持的数据库类型: {db_type_raw}")

                result = AccountClassificationService().invalidate_db_type_cache(normalized_type)
                if not result:
                    raise ConflictError(f"数据库类型 {db_type_raw} 缓存清除失败")

                log_info(
                    f"数据库类型 {db_type_raw} 缓存清除成功",
                    module="cache",
                    operator_id=getattr(current_user, "id", None),
                    db_type=normalized_type,
                )
                return self.success(message=f"数据库类型 {db_type_raw} 缓存已清除")

            result = AccountClassificationService().invalidate_cache()
            if not result:
                raise ConflictError("分类缓存清除失败")

            log_info(
                "分类缓存清除成功",
                module="cache",
                operator_id=getattr(current_user, "id", None),
            )
            return self.success(message="分类缓存已清除")

        return self.safe_call(
            _execute,
            module="cache",
            action="clear_classification_cache",
            public_error="清除分类缓存失败",
            context={"target": "classification", "db_type": payload.get("db_type")},
            expected_exceptions=(ValidationError, ConflictError),
        )


@ns.route("/classification/stats")
class CacheClassificationStatsResource(BaseResource):
    """分类缓存统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CacheClassificationStatsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取分类缓存统计."""

        def _execute():
            manager = _require_cache_service()

            stats = manager.get_cache_stats()
            db_type_stats: dict[str, dict[str, object]] = {}
            db_types = ["mysql", "postgresql", "sqlserver", "oracle"]

            for db_type in db_types:
                try:
                    rules_cache = manager.get_classification_rules_by_db_type_cache(db_type)
                    db_type_stats[db_type] = {
                        "rules_cached": rules_cache is not None,
                        "rules_count": len(rules_cache) if rules_cache else 0,
                    }
                except cache_service_module.CACHE_EXCEPTIONS as exc:
                    log_with_context(
                        "error",
                        "获取数据库类型缓存统计失败",
                        module="cache",
                        action="get_classification_cache_stats",
                        context={"db_type": db_type},
                        extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                    )
                    db_type_stats[db_type] = {
                        "rules_cached": False,
                        "rules_count": 0,
                        "error": str(exc),
                    }

            return self.success(
                data={
                    "cache_stats": stats,
                    "db_type_stats": db_type_stats,
                    "cache_enabled": True,
                },
                message="分类缓存统计获取成功",
            )

        return self.safe_call(
            _execute,
            module="cache",
            action="get_classification_cache_stats",
            public_error="获取分类缓存统计失败",
            context={"endpoint": "classification_stats"},
        )
