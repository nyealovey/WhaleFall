# 配置与环境变量重构计划

## 目标
- 在单一入口集中加载配置（沿用 `app/config.py`），统一校验与默认值策略。
- 强制校验 `SECRET_KEY`、`JWT_SECRET_KEY` 强度与存在性，缺失时启动失败。
- 通过环境变量配置 APScheduler 持久层连接；Cookie 安全标志环境化。
- 将 `scripts/validate_env.sh` 接入 CI 流程，构建阶段即校验。

## 现状
- 环境文件：`env.development`、`env.production`，变量说明分散。
- 安全：CSRF/登录配置在 `app/__init__.py`，Cookie 安全标志已部分设置。
- 调度器：`app/scheduler.py` 使用硬编码路径 `userdata/scheduler.db`。

## 风险
- 变量分散读取，无集中校验；生产安全性不可控。
- 调度器持久层不可环境化，迁移与部署不便。

## 优先级与改进
- P0：集中校验入口与强制检查；环境化持久层连接。
- P1：Cookie 安全策略环境化（`secure/httponly/samesite`）；变量对照表文档化。
- P2：在 CI 中强制执行 `validate_env.sh` 并暴露失败原因。

## 产出与检查清单
- 环境变量对照表（名称/含义/默认值/安全建议/范围）。
- 配置入口设计与校验策略说明；失败退出准则。