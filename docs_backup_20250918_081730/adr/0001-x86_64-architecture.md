# ADR-0001: 使用x86_64架构解决数据库驱动兼容性问题

## 状态
已接受

## 背景
在Apple Silicon Mac (ARM64)上开发时，遇到了以下问题：
1. `pymssql` 在ARM64架构上编译失败
2. `pyodbc` 需要系统ODBC驱动，在Docker中配置复杂
3. `cx-Oracle` 需要Oracle Instant Client，下载和配置困难

## 决策
使用 `arch -x86_64` 命令在Apple Silicon Mac上模拟x86_64架构，通过Docker的 `--platform=linux/amd64` 参数构建x86_64版本的镜像。

## 后果

### 正面影响
- 解决了所有数据库驱动的编译问题
- 保持了完整的功能支持
- 简化了依赖管理
- 提高了开发效率

### 负面影响
- 性能可能略低于原生ARM64
- 镜像大小可能增加
- 需要额外的架构转换

### 风险缓解
- 使用Docker的多架构支持
- 提供ARM64和x86_64两套方案
- 定期测试性能差异

## 实施
1. 创建 `Dockerfile.x86_64` 专门用于x86_64构建
2. 创建 `docker-compose.x86_64.yml` 配置
3. 创建 `requirements-full.txt` 包含所有驱动
4. 提供 `scripts/start_x86_64.sh` 启动脚本

## 相关文档
- `doc/deployment/DATABASE_DRIVERS.md`
- `Dockerfile.x86_64`
- `docker-compose.x86_64.yml`
