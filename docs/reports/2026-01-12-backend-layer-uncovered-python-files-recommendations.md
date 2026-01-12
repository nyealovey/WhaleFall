# 未被 layer(13 篇)标准覆盖的后端 Python 文件：盘点与建议（2026-01-12）
> 状态: Draft  
> 创建: 2026-01-12  
> 更新: 2026-01-12  
> 口径: “layer 标准覆盖范围”= `docs/Obsidian/standards/backend/layer/` 下 13 篇标准的 scope（`app/api, app/constants, app/forms+views, app/infra(+app/scheduler.py), app/models, app/repositories, app/routes, app/schemas, app/services, app/settings.py, app/tasks, app/types, app/utils`）

## 0. 未覆盖清单（按当前口径）

### 0.1 `app/**` 内未覆盖（4 个）

- `app/__init__.py`
- `app/core/__init__.py`
- `app/core/exceptions.py`
- `app/errors.py`

### 0.2 仓库根目录入口未覆盖（2 个）

- `app.py`
- `wsgi.py`

> 说明：以上文件虽然不在 layer(13 篇)标准的 scope 内，但其中 `app/__init__.py`、`app.py`、`wsgi.py` 已由非 layer 标准 [[standards/backend/bootstrap-and-entrypoint|Bootstrap/Entrypoint 启动规范]] 覆盖；而 `app/core/**` 属于 shared kernel(跨层复用的核心对象)，建议以“非 layer 标准”补齐其职责与依赖边界；`app/errors.py` 作为历史 import 路径的兼容 re-export，可在 shared kernel 标准中一并说明，无需单独定义为一层。

## 1. 归类与建议（补标准 vs 维持为入口特例）

| 路径 | 角色归类 | 是否已有标准覆盖 | 推荐动作 | 主要理由 |
|---|---|---|---|---|
| `app/core/exceptions.py` | Shared Kernel | **缺非 layer 标准** | **补齐 shared kernel 标准**（建议新增 `shared-kernel-standards.md`，不纳入 layer 集合） | 异常定义/语义字段属于跨层复用的核心对象；需要明确“异常定义不感知 HTTP、status 映射在 API 边界完成”等依赖边界。 |
| `app/errors.py` | Shared Kernel 兼容门面 | 已覆盖：见 `app/core/**` 的约束 | **保留为兼容特例** | 用于避免全仓 import 迁移导致大面积 diff；不应再承载 HTTP status 等传输层概念。 |
| `app/__init__.py` | App Bootstrap(应用装配)层 | 已覆盖：[[standards/backend/bootstrap-and-entrypoint]] | **保持非 layer，不单开一层** | 它是 app factory 与扩展/蓝图/错误处理/调度器的组装入口，不应被误解为业务分层之一。 |
| `app.py`/`wsgi.py` | 运行入口 | 已覆盖：[[standards/backend/bootstrap-and-entrypoint]] | **保持为入口特例** | 入口文件允许少量启动相关副作用（例如 WSGI patch），但必须遵循入口规范的“禁止承载业务逻辑/查库”。 |

## 2. 最小化补文档清单（建议先做这 1 篇）

如果目标是让“分层+shared kernel”口径形成闭环：

1) `Shared Kernel 编写规范`：覆盖 `app/core/**`（建议文件名：`docs/Obsidian/standards/backend/shared-kernel-standards.md`）
