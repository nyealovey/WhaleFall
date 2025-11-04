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

（内容详见原始需求文档）
