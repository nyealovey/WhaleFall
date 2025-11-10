# 账户分类前端 API 模块化重构方案

> 目标：将 `static/js/pages/accounts/account_classification.js` 中零散的 `http.get/post/...` 调用拆分到专用的域 API 模块，配合页面脚本实现关注点分离，降低代码体积并提升可维护性。

## 1. 现状概述

- 所有 API 调用均在页面脚本直接使用全局 `http`（来自 `static/js/common/http-client.js`，旧名 config.js），例如：
  - `/account_classification/api/classifications` 的 CRUD；
  - `/account_classification/api/rules` 相关接口；
  - `/account_classification/api/rules/stats`、`/account_classification/api/auto-classify` 等扩展操作。
- API 调用与 DOM 操作、表单校验混在一个文件内；每次调用都重复写 URL、错误处理。
- 缺乏统一的域模型（如 Rule、Classification），导致字段命名和响应结构只能在页面脚本里硬编码。

## 2. 模块化设计思路

```
static/js/
├── common/
│   └── http-client.js             # 已有，全局 http 实例
└── api/
    ├── accountClassification.js   # 本次新增：封装分类 & 规则相关 API
    └── index.js                   # (可选) 导出所有 API 模块

pages/accounts/
└── account_classification.js       # 页面脚本，import API 模块 & UI 逻辑
```

### 需要创建的模块

| 文件 | 说明 | 覆盖接口示例 |
| --- | --- | --- |
| `static/js/api/accountClassification.js` | 分类 CRUD、列表接口 | `/account_classification/api/classifications` |
| `static/js/api/accountClassificationRules.js`（可与上面合并） | 规则 CRUD、统计、批量操作 | `/account_classification/api/rules`, `/account_classification/api/rules/stats` |
| `static/js/api/accountClassificationAutomation.js` | 自动分类触发、状态查询 | `/account_classification/api/auto-classify` |

根据实际复杂度，可将规则/自动化合并在同一个模块中，但建议保持接口语义清晰。

### `static/js/api/accountClassification.js` 预期结构

```js
import http from '../http'; // 或直接引用全局 http

export const classificationApi = {
  list() { return http.get('/account_classification/api/classifications'); },
  detail(id) { return http.get(`/account_classification/api/classifications/${id}`); },
  create(payload) { return http.post('/account_classification/api/classifications', payload); },
  update(id, payload) { return http.put(`/account_classification/api/classifications/${id}`, payload); },
  remove(id) { return http.delete(`/account_classification/api/classifications/${id}`); },
};

export const ruleApi = {
  list(params) { return http.get('/account_classification/api/rules', { params }); },
  detail(id) { return http.get(`/account_classification/api/rules/${id}`); },
  create(payload) { return http.post('/account_classification/api/rules', payload); },
  update(id, payload) { return http.put(`/account_classification/api/rules/${id}`, payload); },
  remove(id) { return http.delete(`/account_classification/api/rules/${id}`); },
  stats(ruleIds) { return http.get('/account_classification/api/rules/stats', { params: { rule_ids: ruleIds.join(',') } }); },
};

export const automationApi = {
  trigger(payload) { return http.post('/account_classification/api/auto-classify', payload); },
};
```

> 可根据需要扩展参数、封装分页等。

## 3. 页面脚本改造步骤

1. **引入模块**：在 `account_classification.js` 顶部 `import { classificationApi, ruleApi, automationApi } from '../../api/accountClassification';`（若尚未启用 ES modules，可通过 `<script>` 顺序将新文件注入全局，导出到 `window.AccountClassificationAPI`）。
2. **替换直接调用**：将 `http.get('/account_classification/api/classifications')` 改为 `classificationApi.list()`；确保所有 CRUD 调用使用封装函数。
3. **统一错误处理**：模块内捕获特定错误（如 404/409），可以返回结构化结果或者抛出带 message 的错误；页面脚本只负责 UI 提示。
4. **按域划分文件**（可选）：若页面逻辑仍然庞大，可将 rule 表格、classification 表单等 UI 组件拆分到 `pages/accounts/account_classification/` 子目录。

## 4. 兼容策略

- 保留旧的全局 `http`，新模块内部复用，不需要额外打包。
- 对于尚未模块化的页面，以“域 API 模块 + 页面脚本”模式逐页推进。
- 提供 `docs/frontend/api_modules.md` 说明如何新增/维护 API 模块，避免未来又回到散乱状态。

## 5. 预期收益

- 页面脚本体积显著降低，业务逻辑更清晰。
- API 请求逻辑集中，方便统一处理鉴权、错误提示、重试等。
- 为后续引入测试（例如对 API 模块做单元测试）提供基础。

按照此方案落地时，可先创建 API 模块 + 替换调用，确认功能无回归，再考虑后续 UI 组件化等更大范围的重构。***
