"""Cache namespace (Phase 4A 缓存管理)."""

from __future__ import annotations

from typing import ClassVar, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.cache.cache_actions_service import CacheActionsService
from app.utils.decorators import require_csrf
from app.utils.request_payload import parse_payload

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
            stats_result = CacheActionsService().get_cache_stats()
            stats = stats_result.stats
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
        parsed_json = request.get_json(silent=True)
        raw: object = parsed_json if isinstance(parsed_json, dict) else {}
        payload = parse_payload(raw)
        operator_id = getattr(current_user, "id", None)

        def _execute():
            instance_id = cast("int | None", payload.get("instance_id"))
            username = cast("str | None", payload.get("username"))
            message = CacheActionsService().clear_user_cache(
                instance_id=instance_id,
                username=username,
                operator_id=operator_id,
            )
            return self.success(message=message)

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
        parsed_json = request.get_json(silent=True)
        raw: object = parsed_json if isinstance(parsed_json, dict) else {}
        payload = parse_payload(raw)
        operator_id = getattr(current_user, "id", None)

        def _execute():
            instance_id = cast("int | None", payload.get("instance_id"))
            message = CacheActionsService().clear_instance_cache(instance_id=instance_id, operator_id=operator_id)
            return self.success(message=message)

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
        operator_id = getattr(current_user, "id", None)

        def _execute():
            result = CacheActionsService().clear_all_cache(operator_id=operator_id)
            cleared_count = result.cleared_count
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
        parsed_json = request.get_json(silent=True)
        raw: object = parsed_json if isinstance(parsed_json, dict) else {}
        payload = parse_payload(raw)
        operator_id = getattr(current_user, "id", None)

        def _execute():
            db_type = cast("str | None", payload.get("db_type"))
            message = CacheActionsService().clear_classification_cache(db_type=db_type, operator_id=operator_id)
            return self.success(message=message)

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
            result = CacheActionsService().get_classification_cache_stats()
            return self.success(
                data={
                    "cache_stats": result.cache_stats,
                    "db_type_stats": result.db_type_stats,
                    "cache_enabled": result.cache_enabled,
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
