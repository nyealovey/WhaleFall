# 鲸落 (TaifishV4) 文档中心

[![Version](https://img.shields.io/badge/Version-v1.2.0-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

> 鲸落是一个基于 Flask 的数据库资源管理平台，围绕实例、账户、容量与任务调度等日常运维场景提供一站式支持。

## 🚀 v1.2.0 亮点

- **AggregationService 落地**：聚合服务命名与目录统一，方便后续扩展更多统计维度。
- **同步会话增强**：新增 `scope` 标记，手动聚合的进度与定时任务保持一致，UI 即时反映实例/数据库维度。
- **容量统计体验升级**：前端使用自然周期结束日，手动聚合时自动补齐回调，解决此前“running/pending”卡住的问题。
- **版本资料同步**：README、部署脚本、数据库初始化脚本及页面页脚更新为 v1.2.0。

## 📚 文档目录结构

### 📁 api/ - API接口文档
- `README.md` - API接口总览
- `API_ROUTES_DOCUMENTATION.md` - 详细的API路由文档
- `FUNCTION_DOCUMENTATION.md` - 函数接口文档
- `connection-api-migration.md` - 连接API迁移文档

### 📁 architecture/ - 架构设计
- `PROJECT_STRUCTURE.md` - 项目结构说明
- `spec.md` - 技术规格文档
- `database_relationship_solution.md` - 数据库关系解决方案
- `sync_capacity_refactor.md` - 同步容量重构方案

### 📁 constants/ - 常量文档
- `README.md` - 常量使用说明
- `CONSTANTS_DOCUMENTATION.md` - 常量定义文档
- `usage_report.json` - 使用情况报告

### 📁 database/ - 数据库文档
- `DATABASE_DRIVERS.md` - 数据库驱动说明
- `DATABASE_PERMISSIONS_OVERVIEW.md` - 数据库权限概览
- `SQLSERVER_PASSWORD_POLICY_DISABLED.md` - SQL Server密码策略

### 📁 deployment/ - 部署文档
- `README.md` - 部署指南总览
- `PRODUCTION_DEPLOYMENT.md` - 生产环境部署
- `HOT_UPDATE_GUIDE.md` - 热更新指南
- `GITIGNORE_DATABASE_FILES.md` - 数据库文件忽略配置

### 📁 development/ - 开发文档
- `README.md` - 开发指南总览
- `DEVELOPMENT_SETUP.md` - 开发环境搭建
- `timezone_handling.md` - 时区处理规范
- `unit_test_analysis_report.md` - 单元测试分析报告
- `unit_test_summary_report.md` - 单元测试总结报告
- `css-refactoring-plan.md` - CSS重构计划
- `flatly-theme-integration.md` - Flatly主题集成
- `STYLE_GUIDE.md` - 代码风格指南

### 📁 features/ - 功能特性文档
包含各个功能模块的详细技术文档，如：
- `account_classification_technical_doc.md` - 账户分类技术文档
- `account_sync_technical_doc.md` - 账户同步技术文档
- `capacity_sync_technical_doc.md` - 容量同步技术文档
- `dashboard_technical_doc.md` - 仪表板技术文档
- `logging_center_technical_doc.md` - 日志中心技术文档
- 等等...

### 📁 fixes/ - 问题修复文档
- `README.md` - 修复记录总览
- `aggregation_api_parameter_fix.md` - 聚合API参数修复
- `aggregation_logging_fix.md` - 聚合日志修复
- `mysql_capacity_sync_fix.md` - MySQL容量同步修复
- 等等...

### 📁 guides/ - 使用指南
- `DEVELOPMENT_SETUP.md` - 开发环境搭建指南
- `QUICK_REFERENCE.md` - 快速参考手册
- `UV_USAGE_GUIDE.md` - UV使用指南

### 📁 project/ - 项目文档
- `taifish.md` - 项目介绍
- `todolist.md` - 任务清单
- `template_css_js_mapping.md` - 模板CSS/JS映射
- `templates_static_inventory.md` - 模板静态资源清单

### 📁 refactoring/ - 重构文档
- `csrf_cleanup_report.md` - CSRF清理报告
- `stats_coupling_analysis.md` - 统计耦合分析
- `frontend_api_fix_report.md` - 前端API修复报告
- `stats_refactoring_completion.md` - 统计重构完成报告
- `stats_refactoring_progress.md` - 统计重构进度
- `stats_responsibility_analysis.md` - 统计职责分析

### 📁 reports/ - 项目报告
- `code_analysis_report.md` - 代码分析报告
- `code_duplication_analysis.md` - 代码重复分析
- `PROJECT_ERRORS_ANALYSIS.md` - 项目错误分析
- `route_issues_analysis.md` - 路由问题分析

### 📁 requirements/ - 需求文档
- `technical_documentation_requirements.md` - 技术文档需求

### 📁 security/ - 安全文档
- `SECURITY_CONFIGURATION.md` - 安全配置指南

### 📁 updates/ - 更新文档
- `aggregation_session_management.md` - 聚合会话管理更新

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

### 3. 容量统计功能 (v1.1.3新增)
- **数据库容量统计**: 按数据库维度的容量分析
- **实例容量统计**: 按实例维度的容量聚合
- **容量趋势图表**: 可视化容量变化趋势
- **时间范围筛选**: 支持按时间范围查看容量数据

### 4. 数据同步管理
- **增量同步**: 支持增量数据同步
- **冲突处理**: 智能处理数据同步冲突
- **同步监控**: 实时监控同步状态和进度
- **回滚机制**: 支持同步失败时的数据回滚

### 5. 任务调度管理
- **轻量级调度**: 基于APScheduler的任务调度
- **任务持久化**: 任务状态存储在PostgreSQL数据库
- **监控日志**: 任务执行监控和日志记录
- **动态管理**: 支持任务的启用/禁用和立即执行

### 6. 日志监控中心
- **统一日志**: 结构化日志记录和聚合
- **实时监控**: 系统状态和性能监控
- **日志分析**: 日志搜索、筛选和分析
- **优化显示**: 日志条目对齐优化，最新日志在顶部

## 🛠️ 技术栈

### 后端技术
- **Web框架**: Flask 3.1.2
- **数据库ORM**: SQLAlchemy 2.0.43
- **任务调度**: APScheduler 3.11.0
- **缓存**: Redis 6.4.0+
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

### 当前版本: v1.2.0 (2025-10-31)
- 🔧 聚合服务重命名为 `AggregationService`，提升模块职责清晰度
- 🔄 统一“统计当前周期”实例/数据库回调逻辑，修复手动聚合卡死问题
- 🗂️ 同步会话记录新增 scope 信息，便于区分聚合维度

### 历史版本
- [v1.2.0](../CHANGELOG.md#120---2025-10-31) - 聚合服务重构与同步会话改进
- [v1.1.2](../CHANGELOG.md#112---2025-10-13) - 版本统一更新、样式优化
- [v1.1.1](../CHANGELOG.md#111---2025-10-09) - 容量同步修复、数据库容量统计
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

**最后更新**: 2025-10-31  
**文档版本**: v1.2.0  
**维护团队**: TaifishingV4 Team
