# 021 dependency and utils library refactor progress

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-03
> 更新: 2026-01-03
> 范围: Python backend dependencies, `app/utils`, auth rate limiting, payload validation
> 关联方案: `021-dependency-and-utils-library-refactor-plan.md`
> 关联: `docs/Obsidian/standards/changes-standards.md`, `docs/Obsidian/standards/documentation-standards.md`

---

## 当前状态(摘要)

- 已完成现状扫描与候选项梳理, 并沉淀为 plan 文档.
- 尚未开始改代码与依赖变更, 需要先建立 Phase 0 基线验证口径.

## Checklist

### Phase 0: 基线与回归口径

- [ ] 跑通门禁: `make typecheck`
- [ ] 跑通门禁: `ruff check app`
- [ ] 跑通门禁: `uv run pytest -m unit`
- [ ] 记录限流行为基线(HTML + API + header)

### Phase 1: 依赖清理(只做无争议项)

- [ ] 二次扫描确认无引用: `loguru`, `requests`, `pytz`, `bleach`, `psycopg2-binary`
- [ ] 决策并记录: `psycopg2-binary` 是否保留(结合生产 `DATABASE_URL` 方言)
- [ ] 更新依赖与锁文件: `pyproject.toml`, `uv.lock`, `requirements*.txt`
- [ ] 验收: `uv run pytest -m unit` + 启动自检

### Phase 2: 限流迁移到 `flask-limiter`

- [ ] 引入 `flask-limiter`
- [ ] 注册 limiter extension(配置入口在 `app/settings.py`)
- [ ] 保持 decorator API 形态不变, 内部改用 limiter
- [ ] 验收: 登录与改密限流路径返回 429, header 对齐

### Phase 3: 校验迁移到 `pydantic`

- [ ] 引入 `pydantic`
- [ ] 迁移 instance write payload 校验
- [ ] 迁移 credentials/users/tags 写路径校验
- [ ] `DataValidator` 收敛为兼容层(仅保留 MultiDict -> dict 清洗)

### Phase 4: 清洗策略决策(`bleach` 去留)

- [ ] 明确是否允许有限 HTML(字段清单 + allowlist)
- [ ] 若不需要, 移除 `bleach` 并替换手写 XSS 清洗策略
- [ ] 若需要, 统一 `bleach.clean` 策略并补测试

## 变更记录

- 2026-01-03: 初始化 plan/progress 文档, 尚未开始落地改动.
