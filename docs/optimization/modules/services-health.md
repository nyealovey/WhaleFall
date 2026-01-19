# services/health

## Core Purpose

- 提供基础探活与健康检查能力：ping、basic health、数据库/缓存/系统资源、uptime。

## Unnecessary Complexity Found

- （已落地）`app/services/health/health_checks_service.py:25-28`：
  - 异常元组类型标注为 `BaseException`，但实际枚示的都是 `Exception` 子类。
  - 过宽的类型会误导读者，并引出不必要的“兼容 BaseException”样板倾向。

## Code to Remove

- `app/services/health/health_checks_service.py:25-28`：将异常元组类型收敛为 `Exception`（可删 LOC 估算：~0-3；主要是去除误导与后续样板风险）。

## Simplification Recommendations

1. 异常类型标注与真实捕获集合一致
   - Current: `BaseException` 过宽。
   - Proposed: `Exception` 足够表达“业务/依赖错误”，避免暗示捕获 KeyboardInterrupt 等。

## YAGNI Violations

- 以 `BaseException` 为边界的“防御性捕获”暗示（缺少明确需求）。

## Final Assessment

- 可删 LOC 估算：~0-3（已落地）
- Complexity: Low -> Lower
- Recommended action: Done

