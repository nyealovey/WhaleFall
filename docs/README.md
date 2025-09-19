# 鲸落 (TaifishV4) 文档中心

欢迎来到鲸落项目文档中心！这里包含了项目的所有技术文档、使用指南和开发资料。

## 📚 文档分类

### 🏗️ 项目架构 (architecture/)
- [项目结构说明](architecture/PROJECT_STRUCTURE.md) - 项目目录结构和文件组织
- [技术规格文档](architecture/spec.md) - 详细的技术规格和API文档

### 🗄️ 数据库相关 (database/)
- [数据库驱动指南](database/DATABASE_DRIVERS.md) - 支持的数据库驱动和配置
- [数据库权限总览](database/DATABASE_PERMISSIONS_OVERVIEW.md) - 各数据库权限管理
- [MySQL权限管理](database/MYSQL_PERMISSIONS.md) - MySQL权限配置和使用
- [PostgreSQL权限管理](database/POSTGRESQL_PERMISSIONS.md) - PostgreSQL权限配置
- [SQL Server权限管理](database/SQL_SERVER_PERMISSIONS.md) - SQL Server权限配置
- [Oracle权限管理](database/ORACLE_PERMISSIONS.md) - Oracle权限配置
- [Oracle驱动指南](database/ORACLE_DRIVER_GUIDE.md) - Oracle驱动安装和配置
- [Oracle权限要求](database/ORACLE_PERMISSION_REQUIREMENTS.md) - Oracle权限详细要求
- [数据库初始化](database/database_initialization.md) - 数据库初始化指南

### 🚀 部署和运维 (deployment/)
- [Docker架构](deployment/DOCKER_ARCHITECTURE.md) - Docker容器化架构
- [环境配置](deployment/ENVIRONMENT_SETUP.md) - 环境变量和配置
- [生产部署](deployment/PRODUCTION_DEPLOYMENT.md) - 生产环境部署流程
- [部署总结](deployment/DEPLOYMENT_SUMMARY.md) - 部署方案总结
- [两部分部署](deployment/PRODUCTION_TWO_PART_DEPLOYMENT.md) - 基础环境+Flask应用部署
- [基础环境部署成功](deployment/BASE_ENVIRONMENT_DEPLOYMENT_SUCCESS.md) - 基础环境部署记录
- [部署清理总结](deployment/DEPLOYMENT_CLEANUP_SUMMARY.md) - 部署文档清理记录
- [生产部署完成](deployment/PRODUCTION_DEPLOYMENT_COMPLETE.md) - 生产环境部署完成报告
- [Docker代理配置](deployment/DOCKER_PROXY_CONFIGURATION.md) - Docker代理和镜像源配置指南
- [Nginx简化配置](deployment/NGINX_SIMPLIFIED_CONFIG.md) - Nginx配置简化和优化说明
- [Flask应用管理](deployment/FLASK_APPLICATION_MANAGEMENT.md) - Flask应用启动、停止、调试和监控指南

### 🛠️ 开发指南 (development/)
- [开发环境搭建](development/ENVIRONMENT_SETUP.md) - 本地开发环境配置
- [开发指南](development/DEVELOPMENT_GUIDE.md) - 开发规范和最佳实践
- [数据库迁移](development/DATABASE_MIGRATION.md) - 数据库版本管理

### 🔧 问题修复 (fixes/)
- [数据库字段修复](fixes/DATABASE_FIELDS_FIX_SUMMARY.md) - 数据库表字段缺失问题修复
- [Nginx 502错误修复](fixes/NGINX_502_FIX_SUMMARY.md) - Nginx代理配置问题修复
- [会话超时修复](fixes/SESSION_TIMEOUT_FIX_SUMMARY.md) - 会话管理配置修复

### 📖 使用指南 (guides/)
- [Nginx配置切换](guides/NGINX_CONFIG_SWITCHING_GUIDE.md) - 主机/容器Flask模式切换
- [资源管理](guides/VENDOR_RESOURCES_MANAGEMENT.md) - 前端资源本地化管理
- [Logo更新指南](guides/LOGO_UPDATE_INSTRUCTIONS.md) - 应用Logo更新说明

### 📊 项目报告 (reports/)
- [脚本清理总结](reports/SCRIPTS_CLEANUP_SUMMARY.md) - 项目脚本整理和清理报告
- [故障排除](development/TROUBLESHOOTING.md) - 常见问题和解决方案

### ⚡ 功能特性 (features/)
- 功能特性文档已整合到技术规格文档中

### 📖 使用指南 (guides/)
- [快速参考](guides/QUICK_REFERENCE.md) - 常用命令和配置速查
- [部署指南](guides/README_DEPLOYMENT.md) - 生产环境部署说明
- [UV使用指南](guides/UV_USAGE_GUIDE.md) - Python包管理工具使用
- [Oracle环境配置](guides/ORACLE_SETUP.md) - Oracle环境搭建指南

### 📝 项目文档 (project/)
- [需求文档](project/需求.md) - 项目需求规格说明
- [项目说明](project/whalefall.md) - 项目详细介绍
- [任务清单](project/todolist.md) - 开发任务跟踪

### 📊 报告文档 (reports/)
- [开发报告](reports/report.md) - 开发过程记录

### 📋 架构决策记录 (adr/)
- [x86_64架构决策](adr/0001-x86_64-architecture.md) - 架构选择说明

### 🔌 API文档 (api/)
- [API接口文档](api/) - RESTful API接口说明

## 🎯 快速导航

### 新用户入门
1. 阅读 [项目结构说明](architecture/PROJECT_STRUCTURE.md) 了解项目架构
2. 查看 [快速参考](guides/QUICK_REFERENCE.md) 获取常用信息
3. 按照 [开发环境搭建](development/ENVIRONMENT_SETUP.md) 配置环境

### 开发者指南
1. 阅读 [开发指南](development/DEVELOPMENT_GUIDE.md) 了解开发规范
2. 查看 [技术规格文档](architecture/spec.md) 了解API设计
3. 参考 [数据库权限总览](database/DATABASE_PERMISSIONS_OVERVIEW.md) 了解权限管理

### 运维人员
1. 查看 [部署指南](guides/README_DEPLOYMENT.md) 进行生产部署
2. 阅读 [Docker架构](deployment/DOCKER_ARCHITECTURE.md) 了解容器化
3. 参考 [环境配置](deployment/ENVIRONMENT_SETUP.md) 配置生产环境

## 📞 支持

如果您在使用过程中遇到问题，请参考：
- [故障排除指南](development/TROUBLESHOOTING.md)
- [项目GitHub仓库](https://github.com/nyealovey/TaifishingV4)
- [技术规格文档](spec.md) 中的API说明

---

**最后更新**: 2025年9月14日
**文档版本**: v2.1.0
**维护者**: 鲸落开发团队
