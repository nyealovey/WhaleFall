# 命名规范重构文档

> 基于最新代码扫描，识别出 **79 项命名一致性问题 + 60+ 项语义问题**
> 
> 提供完整的重构方案、执行顺序和命令模板，便于后续重构

本目录包含项目命名规范重构的相关文档和工具。

---

## 📊 快速概览

| 类别 | 数量 | 状态 |
|-----|------|------|
| 后端文件命名问题 | 18 个 | 🔴 待重构 |
| 前端目录命名问题 | 5 个 | 🔴 待重构 |
| 前端 JS 文件命名问题 | 13 个 | 🔴 待重构 |
| 前端 CSS 文件命名问题 | 8 个 | 🔴 待重构 |
| 函数命名问题（基础） | 38 个 | 🟡 待重构 |
| 函数语义问题（深度） | 60+ 个 | 🟡 待分析 |
| **总计** | **139 项** | - |

**预计工作量**: 5-7 天  
**风险等级**: 低-中  
**执行方式**: 推荐执行 `scripts/refactor_naming.sh`（支持 dry-run / skip-tests），亦可按命令模板手动处理

---

## 📚 文档列表

### 1. [重构总结](./重构总结.md) ⭐ 推荐先读

**内容**: 重构项目的总体概述
- 发现的问题统计
- 重构目标和预期收益
- 已创建的文档说明
- 执行建议和风险评估
- 下一步行动计划

**适用对象**: 所有人员  
**阅读时间**: 10 分钟

### 2. [命名规范重构指南](./命名规范重构指南.md)

完整的重构指南，包括：
- 命名规范概述（基于 Google Style Guide）
- 后端命名规范（Python）
- 前端命名规范（JavaScript/CSS）
- 重构优先级
- 详细的重构实施计划
- 检查清单和参考资源

**适用对象**: 所有开发人员
**阅读时间**: 30-45 分钟

### 3. [重构优先级清单](./重构优先级清单.md)

快速参考清单，包括：
- 按优先级排序的重构任务（🔴 高、🟡 中、🟢 低）
- 可复制的命令模板
- 验证清单
- 预计时间和风险评估
- 回滚计划

**适用对象**: 项目负责人、技术主管  
**阅读时间**: 10-15 分钟

### 4. [完整重构清单](./完整重构清单.md)

详细的重构任务清单，包括：
- 所有 79 项重构任务的完整列表
- 详细的重命名对照表
- 命令模板 / 示例脚本
- 执行顺序建议
- 验证清单

**适用对象**: 执行重构的开发人员  
**阅读时间**: 20-30 分钟

### 5. [执行顺序说明](./执行顺序说明.md) ⚠️ 重要

**为什么顺序很重要？**
- 先重命名目录，再重命名文件
- 避免重复修改路径引用
- 减少 50% 的工作量

**内容**:
- 错误顺序 vs 正确顺序对比
- 详细的执行步骤
- 常见错误和解决方案
- 最佳实践

**适用对象**: 所有执行重构的人员  
**阅读时间**: 10-15 分钟

### 6. [函数语义问题分析](./函数语义问题分析.md) 🔍 深度分析

**发现更多问题**:
- 函数名与实际功能不符
- 命名不一致（statistics vs stats）
- 命名模糊（api_list, api_detail）
- 命名冗余（api_ 前缀/后缀）

**内容**:
- 60+ 个函数命名问题
- 详细的问题分析
- 重构建议和示例
- 命名规范指南

**适用对象**: 关注代码质量的开发人员  
**阅读时间**: 20-30 分钟

## 自动化工具

### scripts/refactor_naming.sh

- **定位**: `scripts/refactor_naming.sh`
- **功能**:
  - 先重命名前端目录，再处理后端/前端文件
  - 自动更新 Python 导入与前端引用
  - 支持 `--dry-run`（只打印，不修改）与 `--skip-tests`
  - 默认在完成后运行 `make test` / `make quality`
  - 生成 `docs/refactoring/重构执行报告_*.md`

```bash
# 预览所有操作
./scripts/refactor_naming.sh --dry-run

# 实际执行并自动生成报告
./scripts/refactor_naming.sh

# 如已手动验证，可跳过测试
./scripts/refactor_naming.sh --skip-tests
```

## 命令模板（可选）

如需只执行部分操作，可参考下列命令片段（与脚本保持一致次序）：

```bash
# 目录重命名
git mv app/static/js/pages/capacity_stats app/static/js/pages/capacity-stats

# 文件重命名
git mv app/views/account_classification_form_view.py app/views/classification_forms.py

# 更新导入（macOS）
rg -l "from app\.routes\.database_aggr" app \
  | xargs sed -i '' 's/from app\.routes\.database_aggr/from app.routes.database_aggregations/g'

# 搜索残留引用
rg "capacity_stats/" app/static app/templates
```

## 重构流程

### 快速开始（推荐）

⚠️ **重要**: 请先阅读 [执行顺序说明](./执行顺序说明.md)，脚本也是按该顺序执行的。

```bash
# 1. 确保工作目录干净
git status

# 2. 阅读执行顺序与完整清单
cat docs/refactoring/执行顺序说明.md
cat docs/refactoring/完整重构清单.md

# 3. 预览脚本（可多次执行）
./scripts/refactor_naming.sh --dry-run

# 4. 执行重构
./scripts/refactor_naming.sh

# 5. 查看报告 & 推送
ls docs/refactoring/重构执行报告_*.md | tail -n 1
git checkout -b refactor/naming-$(date +%Y%m%d)
git commit -am "refactor: rename legacy modules"
```

### 详细执行建议

- 即使使用脚本，也建议先 `--dry-run` 核对输出。
- 脚本支持断点重试；若部分重命名已完成，会自动跳过。
- 如需定制操作，可结合“命令模板”章节手动执行。
- 默认模式会在最后运行 `make test` / `make quality` 并生成执行报告。

## 重构范围

### 高优先级（建议优先执行）

✅ 后端文件重命名
- 路由文件（`database_aggr.py` → `database_aggregations.py` 等）
- 表单视图文件（`*_form_view.py` → `*_forms.py`）

✅ 前端文件重命名
- JavaScript 文件（下划线改为连字符）
- CSS 文件（下划线改为连字符）

✅ 导入路径更新
- Python 导入语句
- HTML 模板引用

### 中优先级（需要手动执行）

⚠️ 函数重命名
- 移除冗余的 `api_` 前缀
- 修复语法错误（`get_instances_aggregations` → `get_instance_aggregations`）
- 移除 `_optimized` 后缀

⚠️ 类重命名
- 简化过长的服务类名
- 统一后缀使用

⚠️ 变量命名优化
- 避免缩写
- 统一布尔变量前缀

### 低优先级（可选）

📝 文档和注释
- 添加 docstring
- 统一注释风格

📝 代码组织
- 优化文件结构
- 提取重复代码

## 验证和测试

### 建议的自动验证

在每个阶段结束后运行以下命令：

```bash
# 单元测试
make test

# 代码质量检查
make quality
```

### 手动验证

重构后建议手动测试以下功能：

- [ ] 用户登录和认证
- [ ] 实例管理（创建、编辑、删除）
- [ ] 凭据管理
- [ ] 账户同步
- [ ] 容量统计
- [ ] 标签管理
- [ ] 定时任务
- [ ] 前端页面加载

## 回滚方案

在执行任何批量重命名前，建议手动创建标签或临时分支，便于回滚。

### 方法 1: 创建/恢复标签

```bash
# 操作前创建标签
git tag backup-before-naming-$(date +%Y%m%d%H%M%S)

# 出现问题时回滚
git reset --hard backup-before-naming-20251113XXXXXX
```

### 方法 2: 使用临时分支

```bash
# 在独立分支上重构
git checkout -b refactor/naming-conventions

# 若需要放弃，直接删除分支
git checkout main
git branch -D refactor/naming-conventions
```

### 方法 3: 回滚单个文件

```bash
git checkout backup-before-naming-20251113XXXXXX -- path/to/file.py
```

## 常见问题

### Q: 重构会影响现有功能吗？

A: 文件重命名和导入路径更新不会影响功能，但需要充分测试。函数和类重命名需要更新所有调用点。

### Q: 重构需要多长时间？

A: 
- 文件与目录重命名：半天内可完成（含引用排查）
- 函数重命名：约 2-3 天，需要更新所有调用
- 类/变量优化：按模块切分，预计 1-2 天
- 验证与回归：1 天

整体周期取决于并行度和代码评审安排，通常 5-7 天即可完成一次集中重构。

### Q: 可以分阶段执行吗？

A: 可以。建议按优先级分阶段推进：
1. 目录 → 文件（后端/前端）
2. 函数命名（API、聚合函数、optimized 后缀）
3. 类与变量命名
4. 文档与注释收尾

每个阶段完成后立即合并，避免长期分叉。

### Q: 可以自动化吗？

A: 可以。使用 `scripts/refactor_naming.sh` 即可完成目录/文件重命名、引用替换、测试与报告生成。如需定制，可在该脚本基础上扩展更多校验逻辑。

### Q: 如何确保不遗漏任何引用？

A: 
1. 使用 IDE 的全局搜索功能
2. 运行完整的测试套件
3. 使用 `grep` 或 `rg` 搜索旧名称
4. 代码审查

### Q: 重构后需要更新文档吗？

A: 是的，需要更新：
- API 文档
- 服务和工具函数索引
- README.md
- AGENTS.md

## 参考资源

### 命名规范

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
- [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)

### 重构最佳实践

- [Refactoring: Improving the Design of Existing Code](https://martinfowler.com/books/refactoring.html)
- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)

## 贡献

如果您发现命名不一致或有改进建议，请：

1. 在 Issue 中提出
2. 更新相关文档
3. 提交 Pull Request

## 更新日志

- 2025-11-13: 同步最新代码状态、恢复 `scripts/refactor_naming.sh` 并补充 dry-run / 报告能力。
- 2025-11-12: 创建初始重构文档。

---

*本文档将随着重构进展持续更新*
