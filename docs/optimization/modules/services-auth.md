# Module: `services/auth` + `routes/auth` + `templates/auth`

## Simplification Analysis

### Core Purpose

认证模块（登录 / 登出 / 修改密码 / 当前用户信息）：
- Service 层：认证与校验（不返回 Response、不 commit）
- Web 路由层：页面登录/登出/改密入口（复用 Service；输出 HTML/redirect）
- 模板层：登录页/改密页等

### Unnecessary Complexity Found

- `LoginService.build_login_result` 曾仅被 `LoginService.login` 调用一次，属于单次使用的抽象层
  - 已内联到 `app/services/auth/login_service.py:68`
  - 影响：减少跳转与维护点

### Code to Remove

- 已落地：
  - 删除 `LoginService.build_login_result`，将其逻辑内联到 `login()`（保持行为不变：禁用用户报错、写 session、生成 access/refresh token、返回 payload）
- Estimated LOC reduction: ~15 LOC（仅代码净删；本模块当前变更 `git diff` 统计：-27 +12）

### Simplification Recommendations

1. 内联单次使用 helper
   - Current: `login()` → `build_login_result()` 两段跳转
   - Proposed: `login()` 一处完成（认证 + 禁用校验 + 写 session + 生成 JWT + 构造结果）
   - Impact: 更少间接层；阅读更线性；减少维护面

### YAGNI Violations

- 单次使用的 helper 方法通常是“提前抽象”的典型形态：没有复用收益，只增加跳转成本与维护点。

### Final Assessment

Total potential LOC reduction: ~15 LOC（已落地）
Complexity score: Low
Recommended action: 优先删单次抽象；不触碰路由/模板行为
