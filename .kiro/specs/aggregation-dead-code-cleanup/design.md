# 聚合统计死代码清理设计文档

## Overview

本设计文档描述了聚合统计功能的死代码清理方案。通过静态代码分析和动态引用检查，系统性地识别和删除未使用的代码，减少代码库复杂度，降低维护成本。清理范围包括服务方法、API端点、任务函数、辅助函数、模型字段和导入语句。

## Architecture

### 清理流程架构

```
┌─────────────────────────────────────────────────────────────┐
│                    死代码识别阶段                              │
├─────────────────────────────────────────────────────────────┤
│  1. 静态分析工具扫描                                          │
│     - AST 解析识别所有定义                                    │
│     - 引用关系图构建                                          │
│     - 未使用代码标记                                          │
│                                                              │
│  2. 动态引用检查                                              │
│     - 前端代码搜索 API 调用                                   │
│     - 调度器配置检查任务注册                                  │
│     - 测试代码引用验证                                        │
│                                                              │
│  3. 特殊场景识别                                              │
│     - 重复方法检测                                            │
│     - 未使用字段分析                                          │
│     - 导入语句清理                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    死代码分类阶段                              │
├─────────────────────────────────────────────────────────────┤
│  高优先级：完全未使用且安全删除                                │
│  中优先级：可能未使用但需要进一步验证                          │
│  低优先级：使用频率低但可能有特殊用途                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    安全性验证阶段                              │
├─────────────────────────────────────────────────────────────┤
│  - 运行单元测试                                               │
│  - 检查外部依赖                                               │
│  - 数据库迁移影响分析                                         │
│  - Git 历史引用搜索                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    代码清理执行阶段                            │
├─────────────────────────────────────────────────────────────┤
│  1. 按优先级顺序删除                                          │
│  2. 清理相关导入                                              │
│  3. 更新路由注册                                              │
│  4. 创建数据库迁移（如需要）                                  │
│  5. 运行测试验证                                              │
│  6. 生成变更日志                                              │
└─────────────────────────────────────────────────────────────┘
```

### 工具链架构

```
┌──────────────────┐
│  Python AST      │  解析 Python 代码结构
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  Ruff/Flake8     │  检测未使用的导入和变量
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  Git Grep        │  搜索代码引用
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  自定义分析脚本   │  生成死代码报告
└──────────────────┘
```

## Components and Interfaces

### 1. 死代码分析器 (DeadCodeAnalyzer)

负责识别和分类死代码。

**接口设计：**

```python
class DeadCodeAnalyzer:
    """死代码分析器"""
    
    def analyze_service_methods(self, service_path: str) -> List[DeadMethod]:
        """分析服务类中的未使用方法"""
        pass
    
    def analyze_api_endpoints(self, routes_path: str) -> List[DeadEndpoint]:
        """分析未使用的 API 端点"""
        pass
    
    def analyze_task_functions(self, tasks_path: str) -> List[DeadTask]:
        """分析未使用的任务函数"""
        pass
    
    def analyze_helper_functions(self, module_path: str) -> List[DeadHelper]:
        """分析未使用的辅助函数"""
        pass
    
    def analyze_model_fields(self, model_path: str) -> List[DeadField]:
        """分析未使用的模型字段"""
        pass
    
    def analyze_imports(self, file_path: str) -> List[DeadImport]:
        """分析未使用的导入语句"""
        pass
    
    def detect_duplicate_methods(self, service_path: str) -> List[DuplicateMethod]:
        """检测重复的方法实现"""
        pass
```

**设计决策：**
- 使用 Python AST 模块进行静态分析，避免执行代码
- 支持增量分析，只分析修改过的文件
- 提供详细的位置信息（文件路径、行号）

### 2. 引用检查器 (ReferenceChecker)

验证代码是否被引用。

**接口设计：**

```python
class ReferenceChecker:
    """引用检查器"""
    
    def check_method_references(self, method_name: str, class_name: str) -> List[Reference]:
        """检查方法引用"""
        pass
    
    def check_api_endpoint_usage(self, endpoint_path: str, method: str) -> List[APICall]:
        """检查 API 端点在前端的调用情况"""
        pass
    
    def check_task_registration(self, task_name: str) -> bool:
        """检查任务是否在调度器中注册"""
        pass
    
    def check_field_usage(self, model_name: str, field_name: str) -> List[FieldAccess]:
        """检查模型字段的读写情况"""
        pass
    
    def search_in_tests(self, symbol_name: str) -> List[TestReference]:
        """在测试代码中搜索引用"""
        pass
```

**设计决策：**
- 使用 `git grep` 进行全局搜索，速度快且准确
- 支持正则表达式匹配，处理不同的引用方式
- 区分测试代码和生产代码的引用

### 3. 报告生成器 (ReportGenerator)

生成死代码清理报告。

**接口设计：**

```python
class ReportGenerator:
    """报告生成器"""
    
    def generate_markdown_report(self, analysis_results: AnalysisResults) -> str:
        """生成 Markdown 格式的报告"""
        pass
    
    def categorize_dead_code(self, dead_code_items: List[DeadCodeItem]) -> CategorizedReport:
        """按优先级分类死代码"""
        pass
    
    def estimate_cleanup_impact(self, dead_code_items: List[DeadCodeItem]) -> ImpactEstimate:
        """估算清理影响"""
        pass
```

**设计决策：**
- 报告以 Markdown 格式输出，便于阅读和分享
- 包含详细的位置信息和删除建议
- 提供代码行数和文件大小的统计

### 4. 代码清理器 (CodeCleaner)

执行代码删除操作。

**接口设计：**

```python
class CodeCleaner:
    """代码清理器"""
    
    def remove_method(self, file_path: str, method_name: str, class_name: str = None) -> bool:
        """删除方法"""
        pass
    
    def remove_api_endpoint(self, file_path: str, endpoint_function: str) -> bool:
        """删除 API 端点"""
        pass
    
    def remove_import(self, file_path: str, import_statement: str) -> bool:
        """删除导入语句"""
        pass
    
    def create_field_migration(self, model_name: str, field_name: str) -> str:
        """创建字段删除的数据库迁移"""
        pass
    
    def cleanup_unused_imports(self, file_path: str) -> int:
        """清理文件中的未使用导入"""
        pass
```

**设计决策：**
- 使用 AST 重写而非字符串替换，保证代码结构正确
- 每次删除后自动运行代码格式化工具
- 支持批量操作和回滚

## Data Models

### 死代码项数据结构

```python
@dataclass
class DeadCodeItem:
    """死代码项"""
    type: str  # method, endpoint, task, helper, field, import
    name: str
    location: CodeLocation
    priority: str  # high, medium, low
    reason: str
    risk_level: str  # safe, caution, risky
    estimated_lines: int
    references: List[Reference]
    
@dataclass
class CodeLocation:
    """代码位置"""
    file_path: str
    line_start: int
    line_end: int
    class_name: Optional[str] = None
    
@dataclass
class Reference:
    """引用信息"""
    file_path: str
    line_number: int
    context: str
    reference_type: str  # production, test, comment
```

### 分析结果数据结构

```python
@dataclass
class AnalysisResults:
    """分析结果"""
    dead_methods: List[DeadCodeItem]
    dead_endpoints: List[DeadCodeItem]
    dead_tasks: List[DeadCodeItem]
    dead_helpers: List[DeadCodeItem]
    dead_fields: List[DeadCodeItem]
    dead_imports: List[DeadCodeItem]
    duplicate_methods: List[DuplicateMethod]
    total_lines: int
    analysis_timestamp: datetime
```

## Error Handling

### 错误处理策略

1. **分析阶段错误**
   - 文件读取失败：记录警告，跳过该文件
   - AST 解析失败：记录错误，标记文件需要手动检查
   - 引用搜索超时：使用缓存结果或标记为需要验证

2. **清理阶段错误**
   - 删除操作失败：回滚更改，记录详细错误信息
   - 测试失败：停止清理，生成失败报告
   - 迁移创建失败：跳过字段删除，保留字段标记为废弃

3. **验证阶段错误**
   - 测试运行失败：标记为高风险，不自动删除
   - 外部依赖检查失败：人工审核

### 错误恢复机制

```python
class CleanupTransaction:
    """清理事务管理"""
    
    def __init__(self):
        self.changes: List[Change] = []
        self.backup_files: Dict[str, str] = {}
    
    def begin(self):
        """开始事务"""
        pass
    
    def commit(self):
        """提交更改"""
        pass
    
    def rollback(self):
        """回滚所有更改"""
        for file_path, backup_content in self.backup_files.items():
            with open(file_path, 'w') as f:
                f.write(backup_content)
```

**设计决策：**
- 每次删除前创建文件备份
- 支持原子性操作，要么全部成功要么全部回滚
- 详细记录每个操作的日志

## Testing Strategy

### 测试方法

1. **单元测试**
   - 测试死代码分析器的各个方法
   - 测试引用检查器的搜索准确性
   - 测试代码清理器的删除操作

2. **集成测试**
   - 测试完整的分析-清理流程
   - 验证清理后代码的正确性
   - 测试回滚机制

3. **验证测试**
   - 运行现有的测试套件
   - 验证 API 端点的可访问性
   - 检查数据库迁移的正确性

### 测试数据

创建包含已知死代码的测试文件：

```python
# test_dead_code_sample.py
class TestService:
    def used_method(self):
        """被使用的方法"""
        pass
    
    def unused_method(self):
        """未使用的方法"""
        pass
    
    def _used_helper(self):
        """被使用的辅助方法"""
        pass
    
    def _unused_helper(self):
        """未使用的辅助方法"""
        pass
```

### 测试覆盖率目标

- 死代码分析器：90% 覆盖率
- 引用检查器：85% 覆盖率
- 代码清理器：95% 覆盖率（关键组件）

## Implementation Details

### 已识别的死代码清单

基于代码分析，以下是已识别的可疑死代码：

#### 1. 服务方法 (DatabaseSizeAggregationService)

**高优先级（完全未使用）：**

- `calculate_today_aggregations()` - 与 `calculate_daily_aggregations()` 功能完全相同，重复实现
- `calculate_today_instance_aggregations()` - 与 `calculate_daily_instance_aggregations()` 功能完全相同，重复实现
- `get_aggregations()` - 未被任何路由或任务调用
- `get_instance_aggregations()` - 未被任何路由或任务调用
- `get_trends_analysis()` - 未被任何路由或任务调用
- `_format_aggregation()` - 仅在 `get_aggregations()` 中使用，而后者未被调用
- `_format_instance_aggregation()` - 仅在 `get_instance_aggregations()` 中使用，而后者未被调用

**中优先级（需要验证）：**

- `_summarize_instance_period()` - 仅在 `calculate_*_aggregations_for_instance` 方法中使用，需要验证这些方法是否被调用

#### 2. API 端点 (aggregations.py)

**高优先级：**

- `/api/aggregate` (POST) - 与 `/api/manual_aggregate` 功能重复，可能未被前端使用
- `/api/aggregate-today` (POST) - 调用已废弃的 `calculate_today_aggregations()`，可能未被前端使用
- `/api/aggregate/status` (GET) - 引用了不存在的 `task_get_aggregation_status` 函数，代码错误

#### 3. 任务函数 (database_size_aggregation_tasks.py)

**中优先级：**

- `calculate_instance_aggregations()` - 在 `__init__.py` 中导出，但可能未被调度器注册
- `calculate_period_aggregations()` - 在 `__init__.py` 中导出，但可能未被调度器注册
- `get_aggregation_status()` - 实现不完整（代码被截断），且未被路由正确调用
- `validate_aggregation_config()` - 在 `__init__.py` 中导出，但可能未被使用

**低优先级（辅助函数）：**

- `_initialize_instance_state()` - 仅在一处使用，可以考虑内联
- `_update_instance_state()` - 仅在一处使用，可以考虑内联
- `_run_period_aggregation()` - 被多次调用，应保留

#### 4. 模型字段

**高优先级（明确设置为 None）：**

在 `DatabaseSizeAggregation` 模型中：
- `avg_log_size_mb` - 代码中显式设置为 None
- `max_log_size_mb` - 代码中显式设置为 None
- `min_log_size_mb` - 代码中显式设置为 None
- `log_size_change_mb` - 代码中显式设置为 None
- `log_size_change_percent` - 代码中显式设置为 None

**中优先级（需要验证）：**

- `trend_direction` - 在 `DatabaseSizeAggregation` 中未使用，仅在 `InstanceSizeAggregation` 中使用

### 清理执行计划

#### 阶段 1：删除重复方法（高优先级）

1. 删除 `calculate_today_aggregations()`
   - 所有调用点改为使用 `calculate_daily_aggregations()`
   - 更新相关注释和文档

2. 删除 `calculate_today_instance_aggregations()`
   - 所有调用点改为使用 `calculate_daily_instance_aggregations()`

#### 阶段 2：删除未使用的 API 端点（高优先级）

1. 删除 `/api/aggregate` 端点
   - 验证前端是否使用
   - 如果使用，重定向到 `/api/manual_aggregate`

2. 删除 `/api/aggregate-today` 端点
   - 验证前端是否使用
   - 如果使用，更新为调用 `calculate_daily_aggregations()`

3. 修复 `/api/aggregate/status` 端点
   - 修复 `task_get_aggregation_status` 函数引用错误
   - 或删除该端点（如果未使用）

#### 阶段 3：删除未使用的服务方法（高优先级）

1. 删除 `get_aggregations()`、`get_instance_aggregations()`、`get_trends_analysis()`
2. 删除 `_format_aggregation()` 和 `_format_instance_aggregation()`

#### 阶段 4：清理模型字段（中优先级）

1. 创建数据库迁移，删除日志相关字段：
   - `avg_log_size_mb`
   - `max_log_size_mb`
   - `min_log_size_mb`
   - `log_size_change_mb`
   - `log_size_change_percent`

2. 从模型定义中删除这些字段

#### 阶段 5：清理任务函数（低优先级）

1. 验证 `calculate_instance_aggregations()` 和 `calculate_period_aggregations()` 的使用情况
2. 修复或删除 `get_aggregation_status()`
3. 验证 `validate_aggregation_config()` 的使用情况

#### 阶段 6：清理导入语句（低优先级）

1. 运行 `ruff check --select F401` 检测未使用的导入
2. 自动删除未使用的导入语句

### 验证检查清单

每个阶段完成后执行：

- [ ] 运行所有单元测试
- [ ] 运行集成测试
- [ ] 检查代码格式（ruff format）
- [ ] 检查类型提示（mypy）
- [ ] 手动测试相关功能
- [ ] 更新文档

### 预期清理效果

- **代码行数减少**：预计减少 300-500 行代码
- **文件大小减少**：预计减少 15-20 KB
- **方法数量减少**：预计减少 10-15 个方法
- **API 端点减少**：预计减少 2-3 个端点
- **数据库字段减少**：预计减少 5 个字段

## Design Decisions and Rationales

### 决策 1：使用 AST 而非正则表达式

**理由：**
- AST 解析更准确，能理解代码结构
- 避免误删注释或字符串中的相似代码
- 支持复杂的代码重构操作

**权衡：**
- AST 解析速度较慢
- 需要处理语法错误的文件

### 决策 2：分阶段清理而非一次性清理

**理由：**
- 降低风险，每个阶段都可以验证
- 便于回滚和问题定位
- 允许在清理过程中调整策略

**权衡：**
- 清理周期较长
- 需要多次运行测试

### 决策 3：保留辅助函数而非内联

**理由：**
- 辅助函数提高代码可读性
- 便于单元测试
- 未来可能被其他地方使用

**权衡：**
- 代码行数减少效果不明显
- 可能存在过度抽象

### 决策 4：创建数据库迁移而非直接删除字段

**理由：**
- 保证数据安全
- 支持回滚操作
- 符合数据库变更最佳实践

**权衡：**
- 需要额外的迁移脚本
- 清理周期较长

### 决策 5：使用事务机制管理清理操作

**理由：**
- 保证原子性，避免部分清理导致的不一致
- 支持快速回滚
- 便于错误恢复

**权衡：**
- 实现复杂度增加
- 需要额外的备份存储空间

## Security Considerations

### 安全检查

1. **代码注入风险**
   - 不执行动态生成的代码
   - 所有文件操作使用白名单路径

2. **数据丢失风险**
   - 删除前创建完整备份
   - 支持一键恢复

3. **权限控制**
   - 清理操作需要管理员权限
   - 记录所有清理操作的审计日志

### 审计日志

```python
@dataclass
class CleanupAuditLog:
    """清理审计日志"""
    timestamp: datetime
    operator: str
    operation: str  # analyze, delete, rollback
    target: str
    result: str  # success, failed
    details: Dict[str, Any]
```

## Performance Considerations

### 性能优化策略

1. **增量分析**
   - 只分析修改过的文件
   - 缓存分析结果

2. **并行处理**
   - 多文件分析并行执行
   - 使用进程池加速

3. **索引优化**
   - 构建代码引用索引
   - 加速搜索操作

### 预期性能指标

- 全量分析时间：< 5 分钟
- 增量分析时间：< 30 秒
- 单个文件清理时间：< 5 秒
- 完整清理流程：< 30 分钟

## Monitoring and Logging

### 监控指标

- 分析成功率
- 清理成功率
- 回滚次数
- 平均清理时间

### 日志级别

- **DEBUG**：详细的分析过程
- **INFO**：清理操作记录
- **WARNING**：可疑代码标记
- **ERROR**：清理失败错误

### 日志示例

```python
log_info(
    "开始分析死代码",
    module="dead_code_cleanup",
    target_files=["service.py", "routes.py"],
)

log_warning(
    "发现可疑的未使用方法",
    module="dead_code_cleanup",
    method="calculate_today_aggregations",
    file="database_size_aggregation_service.py",
    line=350,
)

log_info(
    "删除死代码成功",
    module="dead_code_cleanup",
    deleted_lines=45,
    file="database_size_aggregation_service.py",
)
```

## Future Enhancements

### 可能的改进方向

1. **自动化清理**
   - 集成到 CI/CD 流程
   - 定期自动分析和报告

2. **智能建议**
   - 使用机器学习识别死代码模式
   - 提供重构建议

3. **可视化报告**
   - 生成交互式 HTML 报告
   - 代码依赖关系图

4. **增量清理**
   - 支持部分清理
   - 逐步验证和提交

5. **集成开发工具**
   - IDE 插件支持
   - 实时死代码提示
