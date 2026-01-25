---
title: Backend 分层示例(长示例)
aliases:
  - backend-layer-examples
tags:
  - reference
  - reference/examples
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: `standards/backend/layer/**` 引用的长代码示例与正反例集合(非规则 SSOT)
related:
  - "[[reference/examples/README]]"
  - "[[standards/backend/guide/layer/README]]"
  - "[[standards/doc/guide/document-boundary]]"
---

# Backend 分层示例(长示例)

> [!important] 说明
> 本文仅用于承载长示例代码, 便于 standards 引用与收敛. 规则 SSOT 以 `docs/Obsidian/standards/**` 为准.

## API Layer 示例

### Namespace 模板

```python
"""实例 API."""

from flask_restx import Namespace, fields, reqparse

from app.api.v1.models.envelope import make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.services.instances.instance_list_service import InstanceListService

ns = Namespace("instances", description="实例管理")

parser = reqparse.RequestParser()
parser.add_argument("page", type=int, default=1, location="args")
parser.add_argument("limit", type=int, default=20, location="args")
parser.add_argument("search", type=str, location="args")

InstanceModel = ns.model(
    "Instance",
    {
        "id": fields.Integer(description="实例 ID"),
        "name": fields.String(description="实例名称"),
        "db_type": fields.String(description="数据库类型"),
    },
)

InstanceListData = ns.model(
    "InstanceListData",
    {
        "items": fields.List(fields.Nested(InstanceModel)),
        "total": fields.Integer(),
    },
)

InstanceListSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceListSuccessEnvelope",
    InstanceListData,
)

_list_service = InstanceListService()


@ns.route("/")
class InstancesResource(BaseResource):
    """实例列表资源."""

    @ns.doc("list_instances")
    @ns.expect(parser)
    @ns.marshal_with(InstanceListSuccessEnvelope)
    def get(self):
        """获取实例列表."""
        args = parser.parse_args()

        def _execute():
            result = _list_service.list_instances(args)
            return self.success(data=result, message="实例列表获取成功")

        return self.safe_call(
            _execute,
            module="instances_api",
            action="list",
            public_error="获取实例列表失败",
            context={"page": args.get("page"), "limit": args.get("limit")},
        )
```

## Models Layer 示例

### 模型结构

```python
"""实例模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from datetime import datetime


class Instance(db.Model):
    __tablename__ = "instances"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    db_type = db.Column(db.String(50), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=time_utils.now,
        onupdate=time_utils.now,
    )
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host if include_sensitive else None,
            "port": self.port,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        return data

    def __repr__(self) -> str:
        return f"<Instance {self.name}>"

    if TYPE_CHECKING:
        id: int
        name: str
        db_type: str
        host: str
        port: int
```

## Repository Layer 示例

### 仓储基本结构

```python
"""实例仓储."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Query

from app import db
from app.models.instance import Instance
from app.core.types.listing import PaginatedResult

if TYPE_CHECKING:
    from app.core.types.instances import InstanceListFilters


class InstancesRepository:
    @staticmethod
    def get_active_instance(instance_id: int) -> Instance | None:
        return (
            Instance.query.filter_by(id=instance_id, deleted_at=None)
            .first()
        )

    def list_instances(self, filters: InstanceListFilters) -> PaginatedResult[Instance]:
        query = Instance.query.filter(Instance.deleted_at.is_(None))
        query = self._apply_filters(query, filters)
        query = self._apply_sorting(query, filters)

        total = query.count()
        items = query.offset(filters.offset).limit(filters.limit).all()
        return PaginatedResult(items=items, total=total)

    def add(self, instance: Instance) -> None:
        db.session.add(instance)
        db.session.flush()

    def _apply_filters(self, query: Query, filters: InstanceListFilters) -> Query:
        ...
```

## Routes Layer 示例

### 页面路由(模板渲染)

```python
"""实例管理路由."""

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.services.instances.instance_list_page_service import InstanceListPageService
from app.utils.decorators import view_required
from app.infra.route_safety import safe_route_call

instances_bp = Blueprint("instances", __name__)
_page_service = InstanceListPageService()


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例列表页面."""
    search = (request.args.get("search") or "").strip()
    db_type = (request.args.get("db_type") or "").strip()

    def _render() -> str:
        context = _page_service.build_context(search=search, db_type=db_type)
        return render_template("instances/list.html", **context.__dict__)

    return safe_route_call(
        _render,
        module="instances",
        action="index",
        public_error="加载页面失败",
        context={"search": search, "db_type": db_type},
    )
```

### JSON 路由(统一封套)

```python
from flask import Blueprint, request

from app.services.tags.tag_list_service import TagListService
from app.utils.response_utils import jsonify_unified_success
from app.infra.route_safety import safe_route_call

tags_bp = Blueprint("tags", __name__)
_service = TagListService()


@tags_bp.route("/api/tags")
def list_tags():
    def _execute():
        search = (request.args.get("search") or "").strip()
        items = _service.list(search=search)
        return jsonify_unified_success(data={"items": items}, message="标签列表获取成功")

    return safe_route_call(
        _execute,
        module="tags",
        action="list_tags",
        public_error="获取标签列表失败",
    )
```

## Services Layer 示例

### Read Service

```python
"""实例列表 Service."""

from __future__ import annotations

from app.repositories.instances_repository import InstancesRepository
from app.core.types.instances import InstanceListFilters, InstanceListItem
from app.core.types.listing import PaginatedResult


class InstanceListService:
    """实例列表业务编排服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        self._repository = repository or InstancesRepository()

    def list_instances(self, filters: InstanceListFilters) -> PaginatedResult[InstanceListItem]:
        page_result, metrics = self._repository.list_instances(filters)
        items = self._build_list_items(page_result.items, metrics)
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    def _build_list_items(self, instances: list, metrics: object) -> list[InstanceListItem]:
        ...
```

### Write Service + Outcome

```python
from dataclasses import dataclass

from app.core.exceptions import ConflictError
from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository
from app.schemas.instances import InstanceCreatePayload
from app.schemas.validation import validate_or_raise


@dataclass(slots=True)
class InstanceCreateOutcome:
    instance: Instance
    created: bool


class InstanceWriteService:
    def __init__(self, repository: InstancesRepository | None = None) -> None:
        self._repository = repository or InstancesRepository()

    def create(self, payload: dict) -> InstanceCreateOutcome:
        params = validate_or_raise(InstanceCreatePayload, payload)
        if self._repository.exists_by_name(params.name):
            raise ConflictError("实例名称已存在")

        instance = Instance(**params.model_dump())
        self._repository.add(instance)  # flush only
        return InstanceCreateOutcome(instance=instance, created=True)
```

## Tasks Layer 示例

### 兼容有无 app context 的任务模板

```python
from __future__ import annotations

from flask import has_app_context

from app import create_app
from app.services.accounts_sync.accounts_sync_service import accounts_sync_service
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


def sync_accounts(instance_ids: list[int] | None = None) -> dict:
    def _execute() -> dict:
        logger.info(
            "开始账户同步任务",
            module="tasks",
            task="sync_accounts",
            instance_count=len(instance_ids) if instance_ids else "all",
        )
        return accounts_sync_service.sync_batch(instance_ids)

    if has_app_context():
        return _execute()

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        return _execute()
```

## Forms 示例

### 表单定义

```python
"""实例表单定义."""

from wtforms import IntegerField, SelectField, StringField
from wtforms.validators import DataRequired, Length, NumberRange

from app.forms.definitions.base import BaseFormDefinition


INSTANCE_FORM_DEFINITION = BaseFormDefinition(
    model_name="Instance",
    template="instances/form.html",
    fields=[
        {
            "name": "name",
            "type": StringField,
            "label": "实例名称",
            "validators": [
                DataRequired(message="实例名称不能为空"),
                Length(min=1, max=255, message="名称长度 1-255 字符"),
            ],
        },
        {
            "name": "port",
            "type": IntegerField,
            "label": "端口",
            "validators": [DataRequired(), NumberRange(min=1, max=65535)],
        },
        {
            "name": "db_type",
            "type": SelectField,
            "label": "数据库类型",
            "choices": [("mysql", "MySQL"), ("postgresql", "PostgreSQL")],
        },
    ],
)
```
