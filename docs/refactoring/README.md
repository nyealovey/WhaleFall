# 命名规范重构文档

> 基于全面代码扫描，发现 **73+ 项命名问题**
> 
> 提供完整的重构方案、自动化工具和详细文档

本目录包含项目命名规范重构的相关文档和工具。

---

## 📊 快速概览

| 类别 | 数量 | 状态 |
|-----|------|------|
| 后端文件命名问题 | 17 个 | 🔴 待重构 |
| 前端目录命名问题 | 5 个 | 🔴 待重构 |
| 前端 JS 文件命名问题 | 13 个 | 🔴 待重构 |
| 前端 CSS 文件命名问题 | 8 个 | 🔴 待重构 |
| 函数命名问题（基础） | 35+ 个 | 🟡 待重构 |
| 函数语义问题（深度） | 60+ 个 | 🟡 待分析 |
| **总计** | **138+ 项** | - |

**预计工作量**: 5-7 天  
**风险等级**: 低-中  
**自动化程度**: 目录和文件重命名 100% 自动化

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
- 快速执行脚本
- 验证清单
- 预计时间和风险评估
- 回滚计划

**适用对象**: 项目负责人、技术主管  
**阅读时间**: 10-15 分钟

### 4. [完整重构清单](./完整重构清单.md)

详细的重构任务清单，包括：
- 所有 78+ 项重构任务的完整列表
- 详细的重命名对照表
- 自动化脚本代码
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

### 重构脚本

位置: `scripts/refactor_naming.sh`

#### 功能

- 自动重命名后端文件
- 自动重命名前端文件
- 自动更新导入路径
- 自动更新前端引用
- 运行测试验证
- 生成重构报告

#### 使用方法

```bash
# 1. 预览模式（不实际修改文件）
./scripts/refactor_naming.sh --dry-run

# 2. 执行重构
./scripts/refactor_naming.sh

# 3. 查看帮助
./scripts/refactor_naming.sh --help
```

#### 注意事项

- 执行前确保工作目录干净（无未提交更改）
- 脚本会自动创建备份标签
- 脚本会自动创建重构分支
- 建议先在 dry-run 模式下预览

## 重构流程

### 快速开始（推荐）

⚠️ **重要**: 请先阅读 [执行顺序说明](./执行顺序说明.md) 了解为什么顺序很重要！

```bash
# 1. 确保工作目录干净
git status

# 2. 阅读执行顺序说明（重要！）
cat docs/refactoring/执行顺序说明.md

# 3. 预览重构（推荐）
./scripts/refactor_naming.sh --dry-run

# 4. 执行重构（脚本会按正确顺序执行）
./scripts/refactor_naming.sh

# 5. 查看重构报告
cat docs/refactoring/重构执行报告_*.md

# 6. 推送更改
git push origin refactor/naming-conventions-YYYYMMDD
```

**脚本执行顺序**（已优化）：
1. ✅ 先重命名目录（5 个）
2. ✅ 再重命名文件（38 个）
3. ✅ 最后更新引用（一次性完成）

### 手动执行（高级）

如果需要更精细的控制，可以参考[命名规范重构指南](./命名规范重构指南.md)中的详细步骤手动执行。

## 重构范围

### 高优先级（已包含在自动化脚本中）

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

### 自动验证

脚本会自动运行以下验证：

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

如果重构出现问题，可以使用以下方法回滚：

### 方法 1: 使用备份标签

```bash
# 查看备份标签
git tag | grep backup-before-refactor

# 回滚到备份点
git reset --hard backup-before-refactor-YYYYMMDD_HHMMSS
```

### 方法 2: 删除重构分支

```bash
# 切换回主分支
git checkout main

# 删除重构分支
git branch -D refactor/naming-conventions-YYYYMMDD
```

### 方法 3: 回滚特定文件

```bash
# 回滚单个文件
git checkout backup-before-refactor-YYYYMMDD_HHMMSS -- <file_path>
```

## 常见问题

### Q: 重构会影响现有功能吗？

A: 文件重命名和导入路径更新不会影响功能，但需要充分测试。函数和类重命名需要更新所有调用点。

### Q: 重构需要多长时间？

A: 
- 自动化脚本执行: 5-10 分钟
- 测试验证: 1-2 小时
- 手动函数/类重命名: 3-5 天
- 总计: 3-7 天（取决于范围）

### Q: 可以分阶段执行吗？

A: 可以。建议按优先级分阶段执行：
1. 第一阶段: 文件重命名（使用自动化脚本）
2. 第二阶段: 函数重命名（手动执行）
3. 第三阶段: 类重命名（手动执行）
4. 第四阶段: 变量优化（可选）

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

- 2025-11-12: 创建初始重构文档和自动化脚本
- 待更新: 执行重构后的实际结果

---

*本文档将随着重构进展持续更新*
