# 类型导入与 `cast()` 治理方案

> 更新时间：2025-12-11 11:45  
> 关联报告：`docs/reports/ruff_full_2025-12-11_112236.txt`（TC006/TC001/UP037 共 140+ 条告警）

## 1. 症状与风险
- **TC006**：`typing.cast()` 传入运行期可见类型（如 `cast(AccountQuery, ...)`），一旦该类型定义在当前模块下方或存在循环依赖，Python 会尝试解析真实对象，引发导入错误。  
- **TC001/TC003**：大量 `typing`/`typing_extensions` 在运行期导入，既拖慢启动又破坏 `TYPE_CHECKING` 约定，部分文件还导致 `F401`。  
- **UP037**：在已经启用 `from __future__ import annotations` 的文件里仍保留引号注解，Pyright/Ruff 对相同类型做双重推迟，造成风格不一致。

这些问题集中在表单、视图与路由层（`app/forms/definitions/base.py`、`app/views/mixins/resource_forms.py`、`app/routes/accounts/ledgers.py` 等），任何小改动都会被 Ruff 拒绝，严重影响提交效率。

## 2. 目标
1. **根除** 当前报告中的 `TC006/TC001/UP037` 告警（约 140 条）。  
2. **建立基线**：新增模块默认使用 `TYPE_CHECKING` + 字符串化 cast，不再重复劳动。  
3. **沉淀别名**：在 `app/types/` 中补充 Query/Context/Tuple 别名，减少每次手写复杂泛型。

## 3. 处理策略
### 3.1 文件级规范
1. 统一在相关模块顶部添加：
   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING, Protocol, runtime_checkable
   ```
2. 所有重量级导入（服务、模型、表单）置于：
   ```python
   if TYPE_CHECKING:
       from app.services.form_service.base import BaseResourceService
   ```
3. `cast()` 目标改为字符串，并优先引用别名（例如 `cast("AccountQuery", AccountPermission.query)`）。

### 3.2 别名沉淀
- 在 `app/types/structures.py` 新增：
  ```python
  AccountQuery = QueryProtocol[AccountPermission]
  ClassificationQuery = QueryProtocol[ClassificationRule]
  ```
- 视图/表单模块统一 `from app.types.structures import AccountQuery`，避免重复定义。

### 3.3 自动化脚本
位于 `scripts/tools/` 的 `fix_typing_imports.py`（新增）负责：
1. 识别 `cast(Type, ...)` 并转写为 `cast("Type", ...)`。  
2. 将 `typing` 导入迁移至 `TYPE_CHECKING` 块。  
3. 自动插入 `from __future__ import annotations`（若缺失）。  
脚本运行方式：
```bash
python scripts/tools/fix_typing_imports.py app/forms app/views app/routes
```

## 4. 分阶段落地
| 阶段 | 范围 | 负责人 | 预计完成 | 验证 |
| --- | --- | --- | --- | --- |
| Phase 1 | `app/forms/definitions/*.py` | @owner-forms | 12-11 下午 | `ruff --select TC006,TC001,UP037` |
| Phase 2 | `app/views/mixins/*.py`、`app/views/*forms.py` | @owner-views | 12-12 上午 | `ruff --select TC006,TC001,D102` |
| Phase 3 | 路由层（`accounts/ledgers.py`, `accounts/sync.py` 等） | @owner-routes | 12-12 晚 | `ruff --select TC006,TC001,TRY` |


## 5. 验收清单
- [ ] 运行 `./scripts/refactor_naming.sh --dry-run`（确保无引用漂移）。  
- [ ] `ruff check <touched files> --select TC006,TC001,UP037,I001,F401`.  
- [ ] `npx pyright app`（验证 TYPE_CHECKING + 别名未破坏类型检查）。  
- [ ] 关键路由/表单执行 smoke（登录后台、打开账户台账、提交流程）。

完成以上步骤后，再次生成 `docs/reports/ruff_full_*`，确保类型导入相关告警清零，并在 PR 中附上此文档链接，提醒后续开发遵循该规范。
