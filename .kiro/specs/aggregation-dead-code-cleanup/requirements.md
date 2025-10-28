# 聚合统计死代码清理需求文档

## Introduction

本文档定义了聚合统计功能的死代码清理需求。通过系统性地识别和删除未使用的代码，减少代码库的复杂度，降低维护成本，提高代码可读性。本次清理聚焦于聚合统计相关的服务、路由、任务和模型代码。

## Glossary

- **Dead Code**: 死代码，指在代码库中定义但从未被调用或使用的函数、方法、类或变量
- **Aggregation Service**: 聚合服务，位于 `app/services/database_size_aggregation_service.py`
- **Aggregation Routes**: 聚合路由，位于 `app/routes/aggregations.py`
- **Aggregation Tasks**: 聚合任务，位于 `app/tasks/database_size_aggregation_tasks.py`
- **Aggregation Models**: 聚合模型，包括 DatabaseSizeAggregation 和 InstanceSizeAggregation
- **API Endpoint**: API端点，指通过HTTP访问的路由函数
- **Helper Function**: 辅助函数，指仅在模块内部使用的私有函数
- **Public Method**: 公共方法，指可以被外部模块调用的类方法

## Requirements

### Requirement 1: 识别未使用的服务方法

**User Story:** 作为开发人员，我希望识别 DatabaseSizeAggregationService 中所有未被调用的公共方法，以便安全地删除它们

#### Acceptance Criteria

1. WHEN 扫描整个代码库时，THE System SHALL 列出 DatabaseSizeAggregationService 中所有公共方法
2. WHEN 检查每个公共方法时，THE System SHALL 验证该方法是否被其他模块引用
3. WHEN 发现未被引用的方法时，THE System SHALL 生成包含方法名、行号和定义位置的清单
4. THE System SHALL 区分真正的死代码和仅在测试中使用的方法
5. THE System SHALL 标记以下可疑的未使用方法：
   - `calculate_today_aggregations()`
   - `calculate_today_instance_aggregations()`
   - `get_aggregations()`
   - `get_instance_aggregations()`
   - `get_trends_analysis()`
   - `_format_aggregation()`
   - `_format_instance_aggregation()`
   - `_summarize_instance_period()`

### Requirement 2: 识别未使用的API端点

**User Story:** 作为开发人员，我希望识别聚合路由中所有未被前端调用的API端点，以便删除或标记为废弃

#### Acceptance Criteria

1. WHEN 分析 aggregations.py 路由文件时，THE System SHALL 列出所有定义的API端点
2. WHEN 检查前端代码时，THE System SHALL 搜索每个API端点的调用情况
3. WHEN 发现未被前端调用的端点时，THE System SHALL 生成包含路径、HTTP方法和函数名的清单
4. THE System SHALL 检查以下可疑的API端点：
   - `/api/aggregate` (可能与 `/api/manual_aggregate` 重复)
   - `/api/aggregate-today` (可能未使用)
   - `/api/aggregate/status` (引用了不存在的 `task_get_aggregation_status` 函数)
5. WHERE API端点被标记为死代码，THE System SHALL 验证删除该端点不会破坏现有功能

### Requirement 3: 识别未使用的任务函数

**User Story:** 作为开发人员，我希望识别聚合任务模块中所有未被调度器调用的任务函数，以便删除它们

#### Acceptance Criteria

1. WHEN 分析 database_size_aggregation_tasks.py 时，THE System SHALL 列出所有导出的任务函数
2. WHEN 检查任务调度配置时，THE System SHALL 验证每个任务函数是否被注册到调度器
3. WHEN 检查其他模块时，THE System SHALL 验证任务函数是否被手动调用
4. THE System SHALL 检查以下可疑的任务函数：
   - `calculate_instance_aggregations()` (可能未被调度)
   - `calculate_period_aggregations()` (可能未被调度)
   - `get_aggregation_status()` (未完成实现，代码被截断)
   - `validate_aggregation_config()` (在 __init__.py 中导出但可能未实现)
5. THE System SHALL 验证 `run_daily_aggregation()` 等辅助函数是否仅在主任务中使用

### Requirement 4: 识别未使用的辅助函数

**User Story:** 作为开发人员，我希望识别聚合模块中所有未被使用的私有辅助函数，以便删除它们

#### Acceptance Criteria

1. WHEN 分析服务类的私有方法时，THE System SHALL 检查每个以下划线开头的方法是否被调用
2. WHEN 分析任务模块的辅助函数时，THE System SHALL 检查每个非导出函数是否被使用
3. THE System SHALL 生成未使用的辅助函数清单，包括函数名和所在文件
4. THE System SHALL 特别检查以下辅助函数：
   - `_initialize_instance_state()` (仅在一处使用，可能可以内联)
   - `_update_instance_state()` (仅在一处使用，可能可以内联)
   - `_run_period_aggregation()` (被多次调用，应保留)
5. WHERE 辅助函数仅被调用一次，THE System SHALL 建议是否应该内联该函数

### Requirement 5: 识别未使用的模型字段

**User Story:** 作为开发人员，我希望识别聚合模型中所有未被使用的数据库字段，以便考虑删除或标记为废弃

#### Acceptance Criteria

1. WHEN 分析 DatabaseSizeAggregation 模型时，THE System SHALL 列出所有定义的字段
2. WHEN 检查代码库时，THE System SHALL 验证每个字段是否被读取或写入
3. WHEN 发现未使用的字段时，THE System SHALL 生成包含字段名、模型名和表名的清单
4. THE System SHALL 特别检查以下可疑字段：
   - `avg_log_size_mb` (代码中显示设置为 None，可能不再使用)
   - `max_log_size_mb` (代码中显示设置为 None，可能不再使用)
   - `min_log_size_mb` (代码中显示设置为 None，可能不再使用)
   - `log_size_change_mb` (代码中显示设置为 None，可能不再使用)
   - `log_size_change_percent` (代码中显示设置为 None，可能不再使用)
   - `trend_direction` (在 DatabaseSizeAggregation 中未使用，仅在 InstanceSizeAggregation 中使用)
5. THE System SHALL 区分真正未使用的字段和为未来功能预留的字段

### Requirement 6: 识别重复的方法实现

**User Story:** 作为开发人员，我希望识别功能完全相同的重复方法，以便删除冗余代码

#### Acceptance Criteria

1. WHEN 分析聚合服务时，THE System SHALL 识别具有相同实现的方法对
2. THE System SHALL 检查以下可疑的重复方法：
   - `calculate_daily_aggregations()` vs `calculate_today_aggregations()` (功能相同)
   - `calculate_daily_instance_aggregations()` vs `calculate_today_instance_aggregations()` (功能相同)
3. WHERE 发现重复方法，THE System SHALL 建议保留哪个方法并删除另一个
4. THE System SHALL 检查所有调用点，确保删除后不会破坏功能
5. THE System SHALL 生成重复方法的对比报告，显示代码相似度

### Requirement 7: 识别未使用的导入

**User Story:** 作为开发人员，我希望识别聚合模块中所有未使用的导入语句，以便清理它们

#### Acceptance Criteria

1. WHEN 分析每个聚合相关文件时，THE System SHALL 列出所有导入语句
2. WHEN 检查文件内容时，THE System SHALL 验证每个导入是否被使用
3. WHEN 发现未使用的导入时，THE System SHALL 生成包含导入语句和文件路径的清单
4. THE System SHALL 使用静态分析工具（如 flake8 或 pylint）自动检测未使用的导入
5. THE System SHALL 特别检查 aggregations.py 中的导入，因为该文件引用了不存在的函数

### Requirement 8: 生成死代码清理报告

**User Story:** 作为开发人员，我希望获得一份完整的死代码清理报告，以便系统性地进行清理工作

#### Acceptance Criteria

1. THE System SHALL 生成包含所有死代码的综合报告
2. THE Report SHALL 按照优先级对死代码进行分类：
   - 高优先级：完全未使用且安全删除的代码
   - 中优先级：可能未使用但需要进一步验证的代码
   - 低优先级：使用频率低但可能有特殊用途的代码
3. THE Report SHALL 包含每个死代码项的详细信息：
   - 代码位置（文件路径和行号）
   - 代码类型（方法、函数、类、字段等）
   - 未使用的原因分析
   - 删除风险评估
   - 建议的清理操作
4. THE Report SHALL 估算清理死代码后可以减少的代码行数
5. THE Report SHALL 以 Markdown 格式输出，便于阅读和分享

### Requirement 9: 验证删除安全性

**User Story:** 作为开发人员，我希望在删除死代码前验证删除的安全性，以便避免破坏现有功能

#### Acceptance Criteria

1. WHEN 准备删除代码时，THE System SHALL 运行所有相关的单元测试
2. WHEN 删除API端点时，THE System SHALL 检查是否有外部系统依赖该端点
3. WHEN 删除数据库字段时，THE System SHALL 检查是否有数据迁移依赖该字段
4. THE System SHALL 使用 git grep 或类似工具搜索代码引用
5. THE System SHALL 建议在删除前创建功能分支，以便回滚

### Requirement 10: 执行死代码清理

**User Story:** 作为开发人员，我希望按照清理报告系统性地删除死代码，以便完成代码库的清理工作

#### Acceptance Criteria

1. THE System SHALL 按照优先级顺序删除死代码
2. WHEN 删除方法或函数时，THE System SHALL 同时删除相关的导入语句
3. WHEN 删除API端点时，THE System SHALL 同时删除相关的路由注册
4. WHEN 删除数据库字段时，THE System SHALL 创建数据库迁移脚本
5. THE System SHALL 在每次删除后运行测试套件，确保没有破坏现有功能
6. THE System SHALL 记录所有删除操作，生成变更日志
7. THE System SHALL 在删除完成后更新相关文档
8. THE System SHALL 统计清理前后的代码行数和文件大小对比
