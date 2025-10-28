# 聚合统计功能重构需求文档

## Introduction

本文档定义了聚合统计功能的重构需求，旨在清理死代码、优化代码结构、提升可维护性。聚合统计功能负责计算数据库容量的日/周/月/季度统计数据，支持数据库级别和实例级别的聚合。

## Glossary

- **Aggregation Service**: 聚合服务，负责计算统计聚合数据的核心服务类
- **Database Size Aggregation**: 数据库级别的容量聚合统计
- **Instance Size Aggregation**: 实例级别的容量聚合统计
- **Period Type**: 统计周期类型，包括 daily（日）、weekly（周）、monthly（月）、quarterly（季度）
- **Dead Code**: 死代码，指未被调用或已废弃的代码
- **Sync Session**: 同步会话，用于跟踪聚合任务的执行状态

## Requirements

### Requirement 1: 识别和清理死代码

**User Story:** 作为开发人员，我希望识别并清理聚合统计模块中的死代码，以便提高代码可维护性和减少技术债务

#### Acceptance Criteria

1. WHEN 分析聚合服务代码时，THE System SHALL 识别所有未被调用的公共方法
2. WHEN 分析聚合任务代码时，THE System SHALL 识别所有未被使用的辅助函数
3. WHEN 分析路由代码时，THE System SHALL 识别所有未被前端调用的API端点
4. WHEN 发现死代码时，THE System SHALL 生成包含文件路径、函数名和原因的清单
5. WHERE 代码被标记为死代码，THE System SHALL 验证该代码确实没有被任何模块引用

### Requirement 2: 分析代码重复和冗余

**User Story:** 作为开发人员，我希望识别聚合统计模块中的重复代码和冗余逻辑，以便进行合并和简化

#### Acceptance Criteria

1. WHEN 分析聚合服务方法时，THE System SHALL 识别具有相似逻辑的方法对
2. WHEN 发现重复的周期计算逻辑时，THE System SHALL 标记可以提取为通用函数的代码块
3. WHEN 分析数据库聚合和实例聚合时，THE System SHALL 识别可以共享的计算逻辑
4. WHEN 发现冗余的数据格式化代码时，THE System SHALL 建议统一的格式化方法
5. THE System SHALL 生成重复代码的详细报告，包括相似度百分比和建议的重构方案

### Requirement 3: 优化服务层结构

**User Story:** 作为开发人员，我希望优化聚合服务的代码结构，以便提高代码的可读性和可测试性

#### Acceptance Criteria

1. THE Aggregation Service SHALL 将周期计算逻辑（daily/weekly/monthly/quarterly）统一为参数化方法
2. THE Aggregation Service SHALL 将数据库聚合和实例聚合的公共逻辑提取为私有辅助方法
3. THE Aggregation Service SHALL 使用策略模式或工厂模式简化周期类型的处理
4. THE Aggregation Service SHALL 将分区管理逻辑封装为独立的方法或类
5. THE Aggregation Service SHALL 确保所有公共方法都有明确的文档字符串和类型注解

### Requirement 4: 简化任务调度逻辑

**User Story:** 作为开发人员，我希望简化聚合任务的调度逻辑，以便减少代码复杂度和提高可维护性

#### Acceptance Criteria

1. THE Aggregation Tasks SHALL 将重复的周期执行逻辑（run_daily/weekly/monthly/quarterly）合并为通用函数
2. THE Aggregation Tasks SHALL 简化实例状态管理逻辑，减少嵌套层级
3. THE Aggregation Tasks SHALL 将同步会话管理逻辑提取为独立的辅助函数
4. THE Aggregation Tasks SHALL 统一错误处理和日志记录的格式
5. THE Aggregation Tasks SHALL 减少函数参数数量，使用配置对象或数据类传递参数

### Requirement 5: 清理未使用的API端点

**User Story:** 作为开发人员，我希望识别并清理未被前端使用的聚合API端点，以便减少维护负担

#### Acceptance Criteria

1. WHEN 分析聚合路由时，THE System SHALL 识别所有定义的API端点
2. WHEN 检查前端代码时，THE System SHALL 验证每个API端点是否被调用
3. WHEN 发现未使用的API端点时，THE System SHALL 生成包含端点路径和HTTP方法的清单
4. WHERE API端点仅用于内部测试，THE System SHALL 建议将其移至测试专用路由
5. THE System SHALL 保留核心功能API，标记可选或废弃的API端点

### Requirement 6: 优化数据模型和查询

**User Story:** 作为开发人员，我希望优化聚合统计的数据模型和数据库查询，以便提高性能和减少资源消耗

#### Acceptance Criteria

1. THE System SHALL 分析聚合模型中未使用的字段，建议删除或标记为废弃
2. THE System SHALL 识别可以添加索引的查询模式，提高查询性能
3. THE System SHALL 检查是否存在N+1查询问题，建议使用批量查询或预加载
4. THE System SHALL 验证分区表的使用是否正确，确保查询包含分区键
5. THE System SHALL 分析聚合计算的SQL查询，建议使用数据库原生聚合函数优化性能

### Requirement 7: 改进错误处理和日志

**User Story:** 作为开发人员，我希望改进聚合统计的错误处理和日志记录，以便更容易诊断和解决问题

#### Acceptance Criteria

1. THE System SHALL 统一所有聚合方法的异常处理模式
2. THE System SHALL 确保所有关键操作都有适当的日志记录
3. THE System SHALL 使用结构化日志记录，包含必要的上下文信息
4. THE System SHALL 区分预期错误（如数据不存在）和异常错误（如数据库连接失败）
5. THE System SHALL 在聚合失败时提供清晰的错误消息和恢复建议

### Requirement 8: 添加代码文档和注释

**User Story:** 作为开发人员，我希望为聚合统计模块添加完善的文档和注释，以便新开发人员快速理解代码

#### Acceptance Criteria

1. THE System SHALL 为所有公共类和方法添加详细的文档字符串
2. THE System SHALL 在复杂的业务逻辑处添加解释性注释
3. THE System SHALL 为聚合计算的数学公式添加说明注释
4. THE System SHALL 创建模块级别的README文档，说明聚合功能的整体架构
5. THE System SHALL 为关键的数据流程添加流程图或序列图

### Requirement 9: 提取可复用的工具函数

**User Story:** 作为开发人员，我希望将聚合统计中的通用逻辑提取为可复用的工具函数，以便在其他模块中使用

#### Acceptance Criteria

1. THE System SHALL 将日期范围计算逻辑提取为独立的工具函数
2. THE System SHALL 将统计指标计算（平均值、最大值、最小值）提取为通用函数
3. THE System SHALL 将变化率计算逻辑提取为可复用的函数
4. THE System SHALL 将数据格式化逻辑提取为独立的格式化工具
5. THE System SHALL 将提取的工具函数放置在适当的utils模块中，并添加单元测试

### Requirement 10: 优化测试覆盖率

**User Story:** 作为开发人员，我希望提高聚合统计模块的测试覆盖率，以便确保代码质量和防止回归

#### Acceptance Criteria

1. THE System SHALL 为所有公共方法添加单元测试
2. THE System SHALL 为关键的业务逻辑添加集成测试
3. THE System SHALL 测试边界条件和异常情况
4. THE System SHALL 使用测试数据工厂简化测试数据的创建
5. THE System SHALL 确保测试覆盖率达到80%以上
