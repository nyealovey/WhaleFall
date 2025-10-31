
# 项目文件命名一致性分析与重构方案

## 执行摘要

本方案聚焦 1.2.0 重构后遗留的命名杂糅问题，目标是统一命名策略、清理冗余实现，并形成可执行的命名检测流程。建议以“服务层 → 工具层 → 路由层 → 其他层”顺序推进，每阶段完成后运行命名检查脚本并提交变更。


## 一、Services 层命名整改

- **现状**：同时存在 `<功能>_service.py` 与 `<功能>_manager.py`；聚合模块改名后仍有旧 Runner 文件（`database_runner.py`、`instance_runner.py`）。
- **策略**：
  - 文件后缀限定为 `service`、`factory`、`adapter`、`runner`。
  - 类名保持 CapWords，如 `AggregationService`、`AccountSyncAdapter`。
  - 子目录（`*_adapters/`、`*_filters/`）仅放置对应职责文件。
- **重构清单**（✅ 已执行）：
  - `services/cache_manager.py` → `cache_service.py`（与 utils 版本合并）。
  - `services/account_sync_adapters/account_sync_service.py` → 上移为 `services/account_sync_service.py`。
  - `services/capacity_sync_adapters/capacity_sync_service.py` → 上移为 `services/capacity_sync_service.py`。
  - `services/aggregation/database_runner.py` → `database_aggregation_runner.py`。
  - `services/aggregation/instance_runner.py` → `instance_aggregation_runner.py`。
- **检测片段**：
```python
SERVICE_SUFFIXES = {"service", "factory", "adapter", "runner"}
for path in Path("app/services").rglob("*.py"):
    if path.stem.split('_')[-1] not in SERVICE_SUFFIXES:
        errors.append(f"{path}: 建议使用统一后缀 (service/factory/adapter/runner)")
```


## 二、Utils 层命名整改

- **问题点**：存在 `cache_manager.py`、`filter_data.py` 等语义模糊命名，`_utils`、`_manager`、无后缀混用。
- **策略**：
  - 纯函数集合统一为 `<功能>_utils.py`。
  - 涉及状态或外部交互的逻辑迁移到 services。
  - 单一职责类采用 `<功能>_<角色>.py`（如 `rate_limiter.py`）。
- **重构清单**（进行中）：
  - ✅ `utils/cache_manager.py` → 已重命名为 `cache_utils.py`，服务层合并。
  - ✅ `utils/filter_data.py` → `query_filter_utils.py`。
  - ✅ `utils/password_manager.py` → 已重命名为 `password_crypto_utils.py`。
  - ✅ `utils/sqlserver_connection_diagnostics.py` → `sqlserver_connection_utils.py`。
- **检测片段**：
```python
UTIL_SUFFIXES = {"utils", "builder", "validator", "parser", "limiter"}
for path in Path("app/utils").glob("*.py"):
    if path.stem.split('_')[-1] not in UTIL_SUFFIXES:
        errors.append(f"{path}: 建议遵循 utils 命名约定")
```


## 三、Routes 层命名整改

- **现状**：`instances_detail.py`、`instances_stats.py` 复合复数命名；`tags.py` 与 `tags_batch.py` 分工不清。
- **策略**：
  - 路由文件名需与 Blueprint 名称一致，默认使用复数资源名以对应 REST 路径。
  - 如业务上要求单数（例如 `instance.py` 对应 `instance_bp`，但 URL 前缀仍为 `/instances`），必须同步更新所有 `url_for`、模板和文档引用，避免运行期找不到端点。
  - 单例资源（`dashboard.py`、`scheduler.py`）保持单数。
- **重构清单**：
  - ✅ `instances_detail.py` → 已改为 `instance_detail.py`。
  - ✅ `instances_stats.py` → 已改为 `instance_statistics.py`。
  - ✅ `database_stats.py` → 已更名为 `databases.py`。
  - ✅ `storage_sync.py` → 已更名为 `storage.py`（统一 REST 前缀 `/storage`）。
  - ✅ `instances.py` → 已更名为 `instance.py`，并将 Blueprint 名称统一为 `instance`。
- **Blueprint 示例**：
```python
instance_bp = Blueprint("instance", __name__, url_prefix="/instances")
@instance_bp.route("/<int:instance_id>")
def get_instance(instance_id):
    ...
```


## 四、其他层建议

- **Models**：保持 `<模型单数>.py`；统计模型使用 `<实体>_<维度>.py`。
- **Tasks**：延续 `<功能>_tasks.py`。
- **Shell 脚本**：`<场景>_<动作>.sh`，如 `deploy_prod_app.sh`。
- **静态资源**：CSS/JS 按页面模块命名 `pages/<模块>.css`。

## 五、实施计划

1. 服务层命名调整 → 更新引用 → 提交。
2. 工具层合并重命名 → 添加检测脚本。
3. 路由层统一 → 校验 Blueprint → 更新文档。
4. 脚本/文档同步 → 修正 README、部署脚本、SQL。
5. 添加 pre-commit / CI 命名检查 → 完成回归测试。

## 六、命名规范速查

| 层级 | 命名格式 | 示例 |
| --- | --- | --- |
| Services | `<功能>_service.py` / `<功能>_factory.py` | `account_sync_service.py` |
| Utils | `<功能>_utils.py`、`<功能>_<角色>.py` | `time_utils.py`、`rate_limiter.py` |
| Routes | `<资源>.py`（与 Blueprint 名称一致，默认复数） | `instance.py`、`sync_sessions.py` |
| Tasks | `<功能>_tasks.py` | `database_size_aggregation_tasks.py` |
| Models | `<模型单数>.py` | `instance.py`、`database.py` |
| Shell 脚本 | `<场景>_<动作>.sh` | `repair_aggregations.sh` |

## 七、自动化检查入口

```bash
python scripts/code/check_naming_conventions.py --staged
python scripts/code/audit_naming_conventions.py --report naming-report.json
```

---

**文档版本**：2.0  
**创建日期**：2025-10-31  
**最后更新**：2025-10-31  
**维护者**：开发团队
