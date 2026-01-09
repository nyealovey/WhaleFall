# Services 服务层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/services/` 目录下所有服务类的编写规范

---

## 核心原则

**Service = 业务编排 + 校验逻辑 + 事务控制**

```python
# ✅ Service 职责
- 业务逻辑编排与协调
- 输入校验与数据规范化
- 调用 Repository 执行数据操作
- 控制事务边界（commit/rollback）
- 返回领域对象或 DTO

# ❌ Service 禁止
- 直接组装 SQL Query（应由 Repository）
- 返回 HTTP Response（应由 Routes/API）
- 直接处理请求参数解析（应由 Routes/API）
- 包含模板渲染逻辑
```

---

## 目录结构

```
services/
├── __init__.py
├── {domain}/                      # 领域子目录
│   ├── __init__.py
│   ├── {entity}_read_service.py   # 读操作服务
│   ├── {entity}_write_service.py  # 写操作服务
│   ├── {entity}_list_service.py   # 列表服务
│   └── {action}_service.py        # 特定操作服务
├── common/                        # 通用服务
│   └── filter_options_service.py
└── {simple}_service.py            # 简单服务（无需子目录）
```

### 目录组织原则

| 场景 | 组织方式 | 示例 |
|------|---------|------|
| 单一实体，多种操作 | 领域子目录 | `instances/instance_write_service.py` |
| 跨实体业务 | 领域子目录 | `aggregation/aggregation_service.py` |
| 简单独立功能 | 根目录单文件 | `cache_service.py` |

---

## 服务分类规范

### 读服务（Read Service）

```python
"""实例列表 Service.

职责:
- 组织 repository 调用并将领域对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.instances_repository import InstancesRepository
from app.types.instances import InstanceListFilters, InstanceListItem
from app.types.listing import PaginatedResult


class InstanceListService:
    """实例列表业务编排服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        """初始化服务并注入实例仓库."""
        self._repository = repository or InstancesRepository()

    def list_instances(
        self,
        filters: InstanceListFilters,
    ) -> PaginatedResult[InstanceListItem]:
        """分页列出实例列表."""
        page_result, metrics = self._repository.list_instances(filters)
        items = self._build_list_items(page_result.items, metrics)
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    def _build_list_items(
        self,
        instances: list,
        metrics: object,
    ) -> list[InstanceListItem]:
        """构建列表项 DTO."""
        # 转换逻辑
        ...
```

### 写服务（Write Service）

```python
"""实例写操作 Service.

职责:
- 处理实例的创建/更新/删除/恢复编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response, 不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.errors import ConflictError, ValidationError
from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository
from app.schemas.instances import InstanceCreatePayload
from app.schemas.validation import validate_or_raise
from app.utils.structlog_config import log_info


@dataclass(slots=True)
class InstanceCreateOutcome:
    """实例创建结果."""

    instance: Instance
    created: bool


class InstanceWriteService:
    """实例写操作服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        """初始化写操作服务."""
        self._repository = repository or InstancesRepository()

    def create(
        self,
        payload: dict,
        *,
        operator_id: int | None = None,
    ) -> Instance:
        """创建实例."""
        params = validate_or_raise(InstanceCreatePayload, payload)

        # 业务校验
        if self._repository.exists_by_name(params.name):
            raise ConflictError("实例名称已存在")

        # 创建实体
        instance = Instance(**params.model_dump())
        self._repository.add(instance)

        # 记录日志
        log_info(
            "创建数据库实例",
            module="instances",
            user_id=operator_id,
            instance_id=instance.id,
        )

        return instance
```

---

## 方法命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `get_` | 获取单个对象/详情 | `get_instance_detail()` |
| `list_` | 获取列表 | `list_instances()` |
| `create` | 创建操作 | `create()` |
| `update` | 更新操作 | `update()` |
| `delete` / `soft_delete` | 删除操作 | `soft_delete()` |
| `restore` | 恢复操作 | `restore()` |
| `sync_` | 同步操作 | `sync_accounts()` |
| `export_` | 导出操作 | `export_to_excel()` |
| `validate_` | 校验操作 | `validate_expression()` |

---

## 依赖注入规范

```python
class InstanceWriteService:
    """支持依赖注入的服务."""

    def __init__(
        self,
        repository: InstancesRepository | None = None,
        tag_repository: TagsRepository | None = None,
    ) -> None:
        """初始化服务，支持测试时注入 mock."""
        self._repository = repository or InstancesRepository()
        self._tag_repository = tag_repository or TagsRepository()
```

---

## 事务处理规范

```python
# ✅ 正确：Service 控制事务边界
class InstanceWriteService:
    def create(self, payload: dict) -> Instance:
        """创建实例（含事务控制）."""
        instance = Instance(**payload)
        self._repository.add(instance)  # flush only
        self._sync_tags(instance, payload.get("tags", []))
        db.session.commit()  # Service 决定提交
        return instance

# ✅ 正确：使用 nested transaction
class BatchService:
    def batch_create(self, items: list[dict]) -> list[Instance]:
        """批量创建（支持部分回滚）."""
        results = []
        for item in items:
            try:
                with db.session.begin_nested():
                    instance = self._create_single(item)
                    results.append(instance)
            except ValidationError:
                continue  # 单条失败不影响其他
        db.session.commit()
        return results

# ❌ 错误：Repository 中 commit
class InstancesRepository:
    def add(self, instance: Instance) -> None:
        db.session.add(instance)
        db.session.commit()  # 不应在 Repository 中 commit
```

---

## 返回值规范

### 使用 Outcome dataclass

```python
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class InstanceSoftDeleteOutcome:
    """实例软删除结果."""

    instance: Instance
    deletion_mode: Literal["soft"]


@dataclass(slots=True)
class InstanceRestoreOutcome:
    """实例恢复结果."""

    instance: Instance
    restored: bool  # False 表示本来就未删除
```

### 使用 DTO 类型

```python
from app.types.instances import InstanceListItem, InstanceDetail
from app.types.listing import PaginatedResult


class InstanceListService:
    def list_instances(self, filters) -> PaginatedResult[InstanceListItem]:
        """返回分页 DTO 列表."""
        ...

    def get_detail(self, instance_id: int) -> InstanceDetail:
        """返回详情 DTO."""
        ...
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app.repositories.*` | 数据仓储 |
| `app.models.*` | 数据模型（仅用于类型） |
| `app.types.*` | 类型定义 |
| `app.schemas.*` | 校验 Schema |
| `app.errors` | 业务异常 |
| `app.utils.*` | 工具函数 |
| `app.constants.*` | 常量 |
| 其他 `app.services.*` | 跨服务调用 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.routes.*` | 路由层 |
| `app.api.*` | API 层 |
| `flask.request` | 请求对象 |
| `flask.Response` | 响应对象 |

---

## 文件命名规范

| 命名模式 | 用途 | 示例 |
|---------|------|------|
| `{entity}_read_service.py` | 读取服务 | `instance_detail_read_service.py` |
| `{entity}_write_service.py` | 写入服务 | `instance_write_service.py` |
| `{entity}_list_service.py` | 列表服务 | `instance_list_service.py` |
| `{entity}_{action}_service.py` | 特定操作 | `accounts_sync_service.py` |
| `{domain}_service.py` | 领域服务 | `aggregation_service.py` |

---

## 类命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 读服务 | `{Entity}{Action}ReadService` | `InstanceDetailReadService` |
| 写服务 | `{Entity}WriteService` | `InstanceWriteService` |
| 列表服务 | `{Entity}ListService` | `InstanceListService` |
| 操作服务 | `{Entity}{Action}Service` | `AccountsSyncService` |
| 结果类 | `{Entity}{Action}Outcome` | `InstanceSoftDeleteOutcome` |

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 300 行 | 按职责拆分多个 Service |
| 单类方法数 | 10 个 | 拆分为 Read/Write/List Service |
| 单方法行数 | 50 行 | 提取私有方法或拆分步骤 |

---

## 日志规范

```python
from app.utils.structlog_config import log_info, log_warning


class InstanceWriteService:
    def create(self, payload: dict, *, operator_id: int | None = None) -> Instance:
        """创建实例."""
        instance = Instance(**payload)
        self._repository.add(instance)

        # 记录业务日志
        log_info(
            "创建数据库实例",
            module="instances",
            user_id=operator_id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
        )

        return instance
```

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
