# 鲸落 (TaifishV4) 文档中心

[![Version](https://img.shields.io/badge/Version-v1.1.1-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

> 鲸落是一个基于Flask的DBA数据库管理Web应用，提供多数据库实例管理、账户管理、任务调度、日志监控等功能。

## 📚 文档目录

### 🏗️ 架构设计
- [项目结构](./architecture/PROJECT_STRUCTURE.md) - 详细的项目目录结构和模块说明
- [技术规格](./architecture/spec.md) - 系统架构设计和技术规格文档

### 🚀 功能特性
- [核心功能](./features/CORE_FEATURES.md) - 系统核心功能模块介绍
- [账户分类管理](./features/ACCOUNT_CLASSIFICATION.md) - 智能账户分类和权限管理
- [数据同步管理](./features/DATA_SYNC_MANAGEMENT.md) - 多数据库数据同步功能

### 🔧 开发指南
- [开发环境搭建](./development/DEVELOPMENT_SETUP.md) - 本地开发环境配置指南
- [代码规范](./development/CODING_STANDARDS.md) - 代码编写规范和最佳实践
- [测试指南](./development/TESTING_GUIDE.md) - 单元测试和集成测试指南

### 🗄️ 数据库
- [数据库设计](./database/DATABASE_SCHEMA.md) - 数据库表结构设计
- [数据迁移](./database/MIGRATIONS.md) - 数据库迁移和版本管理
- [性能优化](./database/PERFORMANCE_OPTIMIZATION.md) - 数据库查询优化策略

### 🔌 API接口
- [API文档](./api/README.md) - RESTful API接口文档
- [认证授权](./api/AUTHENTICATION.md) - 用户认证和权限控制
- [错误处理](./api/ERROR_HANDLING.md) - API错误码和异常处理

### 🚀 部署运维
- [生产环境部署](./deployment/PRODUCTION_DEPLOYMENT.md) - 生产环境部署指南
- [Docker部署](./deployment/DOCKER_DEPLOYMENT.md) - 容器化部署方案
- [监控告警](./deployment/MONITORING.md) - 系统监控和告警配置

### 🔒 安全配置
- [安全配置](./security/SECURITY_CONFIGURATION.md) - 系统安全配置指南
- [权限管理](./security/PERMISSION_MANAGEMENT.md) - 用户权限和角色管理

### 📊 项目报告
- [项目进度](./project/todolist.md) - 项目开发进度和任务清单
- [错误分析](./reports/PROJECT_ERRORS_ANALYSIS.md) - 项目错误分析和解决方案
- [模板静态资源清单](./project/templates_static_inventory.md) - 模板和静态资源清单

### 📖 用户指南
- [快速开始](./guides/QUICK_START.md) - 系统快速入门指南
- [用户手册](./guides/USER_MANUAL.md) - 详细的功能使用说明
- [常见问题](./guides/FAQ.md) - 常见问题和解决方案
- [故障排除](./guides/TROUBLESHOOTING.md) - 故障诊断和排除指南

## 🎯 核心功能模块

### 1. 数据库实例管理
- **多数据库支持**: PostgreSQL、MySQL、SQL Server、Oracle
- **实例监控**: 实时状态监控和性能统计
- **连接管理**: 安全的数据库连接和凭据管理

### 2. 账户分类管理 (核心功能)
- **智能分类**: 基于权限规则的自动账户分类
- **权限扫描**: 实时更新账户权限信息
- **多分类支持**: 支持账户分配到多个分类
- **规则配置**: 支持多种数据库类型的权限规则

### 3. 数据同步管理
- **增量同步**: 支持增量数据同步
- **冲突处理**: 智能处理数据同步冲突
- **同步监控**: 实时监控同步状态和进度
- **回滚机制**: 支持同步失败时的数据回滚

### 4. 任务调度管理
- **轻量级调度**: 基于APScheduler的任务调度
- **任务持久化**: 任务状态存储在PostgreSQL数据库
- **监控日志**: 任务执行监控和日志记录
- **动态管理**: 支持任务的启用/禁用和立即执行

### 5. 日志监控中心
- **统一日志**: 结构化日志记录和聚合
- **实时监控**: 系统状态和性能监控
- **日志分析**: 日志搜索、筛选和分析
- **告警通知**: 异常情况自动告警

### 6. 标签管理系统
- **标签分类**: 支持标签按分类管理
- **批量操作**: 支持批量分配和移除标签
- **权限控制**: 基于角色的标签管理权限
- **搜索筛选**: 强大的标签搜索和筛选功能

## 🛠️ 技术栈

### 后端技术
- **Web框架**: Flask 3.1.2
- **数据库ORM**: SQLAlchemy 1.4.54
- **任务调度**: APScheduler 3.10.4
- **缓存**: Redis 5.0.7
- **数据库**: PostgreSQL (主数据库)
- **Python版本**: 3.11+

### 前端技术
- **UI框架**: Bootstrap 5.3.2
- **JavaScript**: jQuery 3.7.1
- **图表库**: Chart.js 4.4.0
- **图标**: Font Awesome 6.4.0
- **模板引擎**: Jinja2

### 开发工具
- **代码质量**: Black, isort, Ruff, MyPy
- **测试框架**: pytest
- **容器化**: Docker, Docker Compose
- **Web服务器**: Gunicorn, Nginx
- **版本控制**: Git

## 📈 版本历史

### 当前版本: v1.1.1 (2025-10-09)
- 修复自动分类功能BUG
- 优化标签管理页面
- 修复Jinja2模板语法错误
- 解决JavaScript重复加载问题
- 优化实例显示布局

### 历史版本
- [v1.0.9](../CHANGELOG.md#109---2025-09-25) - 统一搜索框功能
- [v1.0.8](../CHANGELOG.md#108---2025-09-24) - 日志中心优化
- [更多版本历史](../CHANGELOG.md)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](../LICENSE) 文件了解详情。

## 📞 联系我们

- **项目主页**: [GitHub Repository](https://github.com/nyealovey/TaifishingV4)
- **问题反馈**: [Issues](https://github.com/nyealovey/TaifishingV4/issues)
- **讨论交流**: [Discussions](https://github.com/nyealovey/TaifishingV4/discussions)

---

**最后更新**: 2025-09-25  
**文档版本**: v1.1.1  
**维护团队**: TaifishingV4 Team
