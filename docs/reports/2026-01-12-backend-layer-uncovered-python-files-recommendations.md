# 未被 layer(13 篇)+shared kernel 标准覆盖的后端 Python 文件：盘点与建议（2026-01-12）
> 状态: Draft  
> 创建: 2026-01-12  
> 更新: 2026-01-12  
> 口径: “覆盖范围”= `docs/Obsidian/standards/backend/layer/` 下 13 篇标准的 scope + `docs/Obsidian/standards/backend/shared-kernel-standards.md` 的 scope（`app/core/**`）

## 0. 未覆盖清单（按当前口径）

### 0.1 `app/**` 内未覆盖（1 个）

- `app/__init__.py`

### 0.2 仓库根目录入口未覆盖（2 个）

- `app.py`
- `wsgi.py`

> 说明：以上文件虽然不在 layer(13 篇)+shared kernel 标准的 scope 内，但 `app/__init__.py`、`app.py`、`wsgi.py` 已由非 layer 标准 [[standards/backend/bootstrap-and-entrypoint|Bootstrap/Entrypoint 启动规范]] 覆盖。对比“仅 layer(13 篇)”口径：`app/core/__init__.py` 与 `app/core/exceptions.py` 已由 shared kernel 标准补齐，不再属于未覆盖清单。

## 1. 归类与建议（补标准 vs 维持为入口特例）

| 路径 | 角色归类 | 是否已有标准覆盖 | 推荐动作 | 主要理由 |
|---|---|---|---|---|
| `app/__init__.py` | App Bootstrap(应用装配)层 | 已覆盖：[[standards/backend/bootstrap-and-entrypoint]] | **保持非 layer，不单开一层** | 它是 app factory 与扩展/蓝图/错误处理/调度器的组装入口，不应被误解为业务分层之一。 |
| `app.py`/`wsgi.py` | 运行入口 | 已覆盖：[[standards/backend/bootstrap-and-entrypoint]] | **保持为入口特例** | 入口文件允许少量启动相关副作用（例如 WSGI patch），但必须遵循入口规范的“禁止承载业务逻辑/查库”。 |

## 2. 最小化补文档清单（本次口径下）

如果目标是让“layer(13 篇)+shared kernel”口径形成闭环：

1) 已补齐：`Shared Kernel 编写规范`（`docs/Obsidian/standards/backend/shared-kernel-standards.md`）
2) 已存在：`Bootstrap/Entrypoint 启动规范`（`docs/Obsidian/standards/backend/bootstrap-and-entrypoint.md`）
