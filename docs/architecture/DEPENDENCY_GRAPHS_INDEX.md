# 依赖图索引

本目录包含项目的模块依赖关系可视化图表。

## 可用的依赖图

### 1. 完整依赖图
**文件**: `dependency-graph.svg`

完整的应用模块依赖关系图，包含：
- 3层依赖深度
- 模块聚类显示
- 所有主要模块间的依赖关系

**适用场景**: 全局了解项目架构，识别核心模块

---

### 2. 简化依赖图
**文件**: `dependency-graph-simple.svg`

简化版的依赖关系图，包含：
- 2层依赖深度
- 更清晰的视图
- 核心依赖关系

**适用场景**: 快速了解主要模块关系，新人入门

---

### 3. 循环依赖检测图
**文件**: `dependency-cycles.svg`

专门用于检测循环依赖的图表。

**当前状态**: ✅ 无循环依赖

**适用场景**: 代码审查，重构前检查

---

### 4. 服务层依赖图
**文件**: `services-dependency.svg`

服务层（`app/services/`）内部模块的依赖关系，包含：
- 账户同步服务
- 数据库同步服务
- 聚合服务
- 连接适配器
- 表单服务
- 统计服务

**适用场景**: 理解业务逻辑层的组织结构

---

### 5. 路由层依赖图
**文件**: `routes-dependency.svg`

路由层（`app/routes/`）内部模块的依赖关系，包含：
- 认证路由
- 实例管理路由
- 账户管理路由
- 容量统计路由
- 调度器管理路由

**适用场景**: 理解 API 端点的组织和依赖

---

### 6. 模型层依赖图
**文件**: `models-dependency.svg`

模型层（`app/models/`）内部模块的依赖关系，包含：
- 用户模型
- 实例模型
- 凭证模型
- 统计模型
- 同步模型

**适用场景**: 理解数据模型的关系和外键依赖

---

## 如何查看

### 在浏览器中查看
直接在浏览器中打开 SVG 文件：
```bash
open docs/architecture/dependency-graph.svg
```

### 在 VS Code 中查看
安装 SVG 预览插件后，直接在编辑器中打开 SVG 文件。

### 转换为 PNG
如需转换为 PNG 格式：
```bash
# 使用 ImageMagick
brew install imagemagick
convert docs/architecture/dependency-graph.svg docs/architecture/dependency-graph.png

# 或使用 rsvg-convert
brew install librsvg
rsvg-convert -h 2000 docs/architecture/dependency-graph.svg -o docs/architecture/dependency-graph.png
```

---

## 重新生成

依赖图由 `pydeps` 工具生成。如需重新生成，参考 [MODULE_DEPENDENCY_GRAPH.md](./MODULE_DEPENDENCY_GRAPH.md#依赖可视化工具) 中的命令。

---

## 图表说明

### 节点类型
- **矩形框**: 模块/包
- **箭头**: 依赖关系（A → B 表示 A 依赖 B）
- **聚类**: 虚线框表示同一包下的模块

### 颜色含义
- **蓝色**: 应用内部模块
- **绿色**: 标准库模块
- **红色**: 第三方库模块（如果显示）

### 依赖深度
- **max-bacon=2**: 显示直接依赖和二级依赖
- **max-bacon=3**: 显示到三级依赖

---

## 相关文档

- [模块依赖图详细说明](./MODULE_DEPENDENCY_GRAPH.md)
- [项目结构文档](./PROJECT_STRUCTURE.md)
- [代码质量分析](../reports/clean-code-analysis.md)

---

## 更新记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2025-11-21 | 1.0.0 | 初始生成所有依赖图 |
