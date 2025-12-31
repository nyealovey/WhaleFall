# Virtualization Inventory Design

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: virtualization inventory, asset ledger, agentless host probe
> 关联: docs/architecture/domain-first-api-restructure.md, docs/standards/halfwidth-character-standards.md

## 1. 背景与问题

WhaleFall 当前的核心聚合根是数据库实例 `Instance`, 并围绕它组织凭据, 标签, 同步会话, 台账与统计等能力. 现有同步链路已经沉淀了可复用的模式:

- 工厂 + 适配器: 例如 `ConnectionFactory` 依据 `db_type` 选择连接实现, 账户同步也有 adapter factory.
- 同步会话 + 记录: `SyncSession` + `SyncInstanceRecord` 提供了统一的可观测与审计入口.
- 按天采集 + 幂等 upsert: 容量统计以 `collected_date(中国时区)` 做日粒度, 同日重跑用 upsert 覆盖, 并永久保留历史.

新的需求是新增 "虚拟机/物理机台账" 与 "同步采集" 能力, 并支持:

- 多来源: VMware, Hyper-V, 后续 Aliyun.
- 物理机: agentless, 直连, 最低权限.
- 自动关联: 数据库实例与资产通过 IP/hostname 自动匹配, 允许人工纠错.
- hostname 可被用户覆盖为主 hostname, 覆盖前的值需要保留为 alias.
- 迁移/重复: VM 迁移后可能出现重复资产记录, 仅手动合并, 合并后不能丢失任何历史数据.

## 2. 目标 / 非目标

### 2.1 目标

- 引入独立的 "Asset" 台账域, 与数据库实例域并列, 通过弱关联表连接.
- 形成可插拔的采集框架: 平台侧 inventory 与机器侧 probe 解耦, 便于新增 VMware/Hyper-V/Aliyun.
- 每日采集 A 口径规格并永久保留: CPU 核数, 内存总量, 磁盘总量, 多 IP, OS, 平台信息.
- Agentless 最低权限采集: SSH/WinRM 白名单只读, 失败降级为单资产失败, 不影响整场会话.
- 自动关联数据库实例: 以管理 IP 为主锚点, hostname(含 alias) 为辅助锚点.
- 手动合并资产: 合并后数据与历史不丢失, 查询默认只展示 canonical 资产.

### 2.2 非目标

- 不在 v1 强制实现跳板机/代理(堡垒机)链路.
- 不在 v1 强制实现 CPU/内存/磁盘使用率, 仅做规格(A 口径).
- 不自动合并资产记录, 只提供判重与手动合并入口.
- 不要求先打通全部平台, v1 可以先做 import + host probe, 再接入 VMware/Hyper-V.

## 3. 已确认决策

1) 两套并列域: `Instance`(数据库实例) 与 `Asset`(物理机/虚拟机) 分开建模, 通过关联表连接.

2) `asset_id` 系统生成(例如 UUID), 不从 hostname/IP 派生.

3) 自动匹配为主: 以 IP 为主锚点, 允许 hostname 可覆盖为主 hostname, 且覆盖前值保留为 alias.

4) 仅手动合并: 不自动合并, 合并后不丢失任何历史数据.

5) 每日采集并永久保留: CPU/内存/磁盘总量/IP/OS 等按天快照保存.

6) Agentless 且最低权限: 直连 SSH/WinRM, 无 sudo/管理员权限依赖, 失败降级.

7) 管理 IP 全局唯一: 可用于导入幂等与实例自动关联的主锚点.

## 4. 核心抽象与分层

本方案拆成两条采集链路, 统一汇入同一套落库与可观测体系:

1) Platform inventory: 平台侧只读列清单, 输出 VM 元数据与平台标识符.
2) Host probe: 机器侧 agentless 补齐/校验 OS 与 IP, 并采集规格(A 口径).

两条链路最终都输出同一份 RawAsset 结构, 并进入固定流水线:

```text
Collect (platform/import/probe)
  -> Normalize (canonical + aliases + identifiers)
  -> Persist (assets + daily_specs + daily_ips + observations)
  -> Link (instances <-> assets)
  -> Observe (sync sessions + target records + unified logs)
```

## 5. 数据模型草案

### 5.1 Assets (台账主表)

`assets`

- `id` (asset_id): PK, UUID 或自增.
- `asset_type`: `vm | physical`.
- `platform_type`: `vmware | hyperv | aliyun | import | unknown`.
- `hostname`: 主 hostname, 可被用户覆盖.
- `mgmt_ip`: 首选管理 IP(可选), 作为便捷查询字段. 历史 IP 在 daily 表与 identifiers 中保留.
- `os_family`, `os_version`: 可选, 可由采集写入或用户覆盖.
- `custom_fields`: JSONB, 存放用户自定义字段.
- `merged_into_asset_id`: nullable, 指向 canonical 资产. 被合并资产默认不在列表展示.
- `created_at`, `updated_at`, `deleted_at`.

说明:

- "主 hostname 覆盖" 的落点是直接写 `assets.hostname`.
- 覆盖前/采集到的旧值进入 `asset_aliases`, 以满足追溯与后续匹配.

### 5.2 Aliases (不丢失的可匹配字段池)

`asset_aliases`

- `id`: PK
- `asset_id`
- `kind`: `hostname | fqdn | other`
- `value`
- `source`: `user | platform | probe | import`
- `created_at`

约束建议:

- `unique(asset_id, kind, value)` 防重复.

### 5.3 Identifiers (稳定标识符池)

`asset_identifiers`

- `id`: PK
- `asset_id`
- `kind`: `ip | mac | vmware_uuid | hyperv_guid | aliyun_instance_id | import_key | other`
- `value`
- `first_seen_at`, `last_seen_at`

约束建议:

- `index(kind, value)` 支持快速命中.
- `unique(asset_id, kind, value)` 防重复.

### 5.4 Daily Specs (每日规格快照, A 口径)

`asset_daily_specs`

- `id`: PK
- `asset_id`
- `collected_date`: date (China date)
- `collected_at`: datetime (UTC)
- `cpu_cores`: int
- `memory_bytes`: bigint
- `disk_total_bytes`: bigint
- `os_family`, `os_version` (可选)
- `platform_type` (冗余, 便于查询)

约束建议:

- `unique(asset_id, collected_date)` + upsert, 同日幂等覆盖.

### 5.5 Daily IPs (每日 IP 快照)

`asset_daily_ips`

- `id`: PK
- `asset_id`
- `collected_date`: date
- `collected_at`: datetime
- `ip`: inet/string

约束建议:

- `unique(asset_id, collected_date, ip)` + upsert.

### 5.6 Observations (原始证据链)

`asset_observations`

- `id`: PK
- `asset_id`
- `source_type`: `platform | probe | import`
- `source_id`: platform_id 或 import_job_id 等
- `observed_at`
- `payload`: JSONB (原始响应/导入行/命令输出摘要)

用途:

- 合并不丢失: 即使后续字段被覆盖或冲突, 仍可回溯原始输入.
- 问题定位: 记录权限不足, 超时, 命令缺失等降级原因.

### 5.7 Instance <-> Asset Links (弱关联)

`instance_asset_links`

- `id`: PK
- `instance_id`
- `asset_id`
- `link_type`: `auto | manual`
- `match_status`: `candidate | confirmed | rejected`
- `confidence`: 0-100
- `matched_by_rule`: `mgmt_ip | ip_identifier | hostname | alias | other`
- `created_at`, `updated_at`

### 5.8 Merge Events (手动合并审计)

`asset_merge_events`

- `id`: PK
- `merged_from_asset_id`
- `merged_into_asset_id`
- `merged_by_user_id`
- `merged_at`
- `notes` (可选)

合并策略建议(v1):

- 不迁移历史行, 仅将 `assets.merged_into_asset_id` 指向 canonical.
- 列表默认只展示 canonical 资产.
- 查询某 canonical 资产的历史时, 需要把其 merged children 的 daily 表 union 进来, 且不删除任何历史行.

## 6. 适配器与工厂

### 6.1 PlatformCollector

接口草案:

- `test_connection()`
- `list_assets(collected_at, collected_date) -> list[RawAsset]`

RawAsset 最小契约:

- `platform_type`
- `asset_type`
- `identifiers[]` (kind,value)
- `hostname` (observed)
- `ips[]` (observed)
- `specs` (cpu_cores, memory_bytes, disk_total_bytes)
- `os` (optional)
- `host_hints` (optional, 例如 vmware 宿主机线索)

Factory:

- `PlatformCollectorFactory.get(platform_type) -> PlatformCollector`

### 6.2 HostProbe (agentless)

接口草案:

- `probe(asset, credential) -> RawAssetProbeResult`

约束:

- 直连, 无跳板机.
- 最低权限, 白名单只读命令/查询.
- 失败降级, 仅影响该资产当日记录.

Linux(SSH) 只读建议:

- CPU: `getconf _NPROCESSORS_ONLN`
- Memory: `/proc/meminfo` 读取 `MemTotal`
- Disk total: `lsblk -b -dn -o SIZE` 求和
- IP list: `ip addr` 解析

Windows(WinRM) 只读建议:

- CIM/WMI: `Win32_Processor`, `Win32_ComputerSystem`, `Win32_LogicalDisk`
- IP: `Get-NetIPAddress`

Factory:

- `HostProbeFactory.get(protocol) -> HostProbe` (ssh, winrm)

## 7. 同步与任务编排

### 7.1 Import (批量导入) 作为一种 platform

导入的本质是 "inventory source", 可实现为一种 `platform_type=import` 的 collector:

- 输入: CSV/Excel.
- 行字段建议: `mgmt_ip`(必填, 全局唯一), `hostname`(必填), `asset_type`, `protocol`(ssh/winrm), `port`, `credential_ref`, `custom_fields`.
- 行处理:
  - 先用 `mgmt_ip` 命中 `assets.mgmt_ip` 或 identifiers(kind=ip, value=mgmt_ip).
  - 命中 1 条则 update, 命中 0 条则 create, 命中 >1 则标记冲突并跳过写入或写入 observation.

### 7.2 Daily inventory

平台侧每日拉取:

- vmware/hyperv/aliyun: `list_assets()` 输出 RawAsset, 进入 normalize + persist.
- import: 仅在用户触发导入时运行.

### 7.3 Daily host probe

机器侧每日 probe:

- 选择范围: 仅对具备 `mgmt_ip + protocol + credential` 的资产执行.
- 输出: specs(A 口径) 与 ips.
- 落库: `asset_daily_specs` 与 `asset_daily_ips` 同日 upsert.

### 7.4 Observability

复用 `SyncSession`, 但将同步记录从 instance 语义提升为 target 语义:

- 新增 `sync_category=asset_inventory`.
- `SyncTargetRecord`(或 `SyncAssetRecord`): 记录每个 asset/platform 的执行状态与 details.

目标:

- 同一套 UI/日志中心可以查看: 哪天哪些资产 probe 失败, 原因是什么.

## 8. 自动关联 Instance <-> Asset

匹配规则(v1):

1) 强匹配: `Instance.host == Asset.mgmt_ip` or `Instance.host in AssetIdentifier(kind=ip)`.
2) 弱匹配: `Instance.name/host` 命中 `Asset.hostname` 或 `AssetAlias(kind=hostname)`.

输出:

- 写 `instance_asset_links` 为 candidate, confidence 由规则给出.
- 多候选时不自动确认, 保留为 candidate 并提示人工确认.

## 9. 兼容性与迁移策略

- 不破坏现有数据库实例域与同步链路, 资产域作为新模块并列落地.
- 标签与凭据需要可复用绑定:
  - 标签: 从 `instance_tags` 演进到通用 `taggings(subject_type, subject_id)` 或新增 `asset_tags`.
  - 凭据: 现有 `Credential(username,password)` 可能不足以覆盖平台 API 形态, 建议扩展为加密 payload(JSONB) 或为不同凭据类型提供附加字段表.

## 10. 风险与对策

- "IP 全局唯一" 假设变化: 若未来出现不唯一, 需要引入 scope(机房/环境)参与匹配与导入幂等.
- "无跳板机" 限制: 若后续需要堡垒机, HostProbe 需要支持 proxy/jump, 但不影响数据模型与 collector 接口.
- 权限不足导致采集空值: 必须确保 UI 与报表能容忍 None, 并在 observation 中可追溯原因.

## 11. 里程碑建议

Phase 0:

- 先落地数据模型 + 导入(import collector) + 日快照落库.
- 先实现 Linux SSH probe (A 口径) + 会话可观测.

Phase 1:

- 补齐 WinRM probe.
- 实现 Instance <-> Asset 自动关联.
- 补齐 hostname 覆盖与 alias 写入.

Phase 2:

- 接入 VMware inventory collector.
- 接入 Hyper-V inventory collector.

Phase 3:

- 接入 Aliyun inventory collector.

