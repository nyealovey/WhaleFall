# Obsidian Canvas 生成规范(基于 JSON Canvas Spec 1.0)

> 状态: Draft  
> 负责人: WhaleFall Team  
> 创建: 2026-01-06  
> 更新: 2026-01-06  
> 范围: 任何生成用于 Obsidian Vault 的 `.canvas` 文件的代码/脚本/导出功能  
> 关联: https://jsoncanvas.org/spec/1.0/; docs/standards/halfwidth-character-standards.md

## 目的

- 统一 `.canvas` 文件的输出结构, 避免不同生成器导致的渲染差异与 diff 噪音.
- 尽量贴近 Obsidian 的序列化风格, 减少"生成器输出"与"Obsidian 打开-保存"之间的格式化 diff.
- 明确必须字段, 默认值, 与可选字段的使用边界, 降低跨应用兼容风险.

## 适用范围

- 适用: 生成供 Obsidian Canvas 打开的 `.canvas` 文件(底层格式为 JSON Canvas Spec 1.0).
- 不适用: 解析/渲染逻辑(读取 `.canvas` 的容错策略应另立文档).

## 规则(MUST/SHOULD/MAY)

### 1) 顶层结构

- MUST: 顶层为 JSON object.
- MUST: 顶层包含 `nodes` 与 `edges` 两个字段, 类型均为 array(可为空 array).
- SHOULD: 顶层不新增非 Spec 字段(例如 `version`, `meta`), 以降低未知消费者的不兼容风险.
- SHOULD: JSON 使用 UTF-8 编码, 不写 BOM, 文件末尾保留 1 个换行.

### 2) Obsidian 约束(生成器约定)

以下为"生成器为了在 Obsidian 中稳定可用"而制定的约束, 不代表 JSON Canvas Spec 的硬性要求.

- MUST: `file`/`background` 字段使用 vault 内的相对路径(从 vault 根开始), 使用 `/` 作为分隔符.
  - 示例: `notes/a.md`, `assets/img.png`
  - MUST NOT: 以 `/` 开头的绝对路径, Windows 盘符路径, 或包含 `..` 段的路径.
- SHOULD: `id` 使用 16 位小写 hex 字符串(`^[0-9a-f]{16}$`), 与 Obsidian 常见导出风格一致.
- SHOULD: 节点坐标与尺寸按网格对齐(例如 20px 步进), 便于手工编辑与对齐.
- SHOULD: 颜色优先使用 preset(`"1"`-`"6"`), 便于 Obsidian 主题适配.
- MUST(WhaleFall): 仓库内生成的 `.canvas` 文件统一放在 `docs/Obsidian/canvas/`.
- SHOULD(WhaleFall): 以 `docs/Obsidian/` 作为 vault 根目录, `.canvas` 内 `file` 路径相对于该目录.

### 3) 通用 Node 规则

所有 node 均为 object, 并包含以下字段:

- MUST: `id`(string), 在同一文件内唯一(参见 "Obsidian 约束" 的推荐格式).
- MUST: `type`(string), 取值仅允许 `text`/`file`/`link`/`group`.
- MUST: `x`/`y`/`width`/`height`(integer), 单位为像素.
- SHOULD: `width`/`height` > 0.
- MAY: `color`(canvasColor string), 见 "颜色" 章节.

关于 z-index:

- MUST: `nodes` array 的顺序表示 z-index 升序. array 越靠后, 显示层级越高.
- SHOULD: 若无明确 z-index 概念, 建议默认排序: `group` 在前, 其余 node 在后; 同一层级内按 `id` 稳定排序, 降低 diff 噪音.

### 4) Text node

- MUST: `type: "text"`.
- MUST: `text`(string), 内容为纯文本, 允许 Markdown 语法.

### 5) File node

- MUST: `type: "file"`.
- MUST: `file`(string), 指向 vault 内文件的相对路径.
- MAY: `subpath`(string), 必须以 `#` 开头, 用于链接到标题或块.
  - 说明(Obsidian): heading 形如 `#Heading`, block 形如 `#^block-id`.

### 6) Link node

- MUST: `type: "link"`.
- MUST: `url`(string).

### 7) Group node

- MUST: `type: "group"`.
- MAY: `label`(string).
- MAY: `background`(string), 背景图片路径(同 `file` 的路径约束).
- MAY: `backgroundStyle`(string), 仅允许:
  - `cover`
  - `ratio`
  - `repeat`

### 8) Edge 规则

所有 edge 均为 object, 并包含以下字段:

- MUST: `id`(string), 在同一文件内唯一.
- MUST: `fromNode`(string), 指向已存在的 node `id`.
- MUST: `toNode`(string), 指向已存在的 node `id`.
- MAY: `fromSide`/`toSide`(string), 仅允许 `top`/`right`/`bottom`/`left`.
- MAY: `fromEnd`(string), 仅允许 `none`/`arrow`. Spec 默认值为 `none`, 建议仅在非默认时写入.
- MAY: `toEnd`(string), 仅允许 `none`/`arrow`. Spec 默认值为 `arrow`, 建议仅在非默认时写入.
- MAY: `color`(canvasColor string), 见 "颜色" 章节.
- MAY: `label`(string).

### 9) 颜色(canvasColor)

- MUST: `color` 字段类型为 string.
- MUST: 允许以下两种编码方式:
  - Hex: `"#RRGGBB"`(例如 `"#FF0000"`).
  - Preset: `"1"`-`"6"`(字符串数字).
- SHOULD: 优先使用 preset(`"1"`-`"6"`)以获得更好的主题适配能力; 仅在必须固定色值时使用 hex.

### 10) 输出稳定性(推荐, Obsidian 优先)

- SHOULD: 采用与 Obsidian 导出接近的 JSON 格式, 以减少 Obsidian 重写文件造成的 diff:
  - 顶层 key 顺序: `nodes`, `edges`
  - `nodes`/`edges` 使用 `"<key>":[` 的紧凑写法(无多余空格)
  - array 内容使用 tab 缩进
  - array 内每个 node/edge object 尽量保持单行
- SHOULD: key 顺序与 Obsidian 示例保持一致, 优先把类型字段放在前面(例如 file node: `id`, `type`, `file`, `x`, `y`, `width`, `height`, `color`).
- SHOULD: 默认值不落盘(例如 edge 的 `fromEnd: "none"`, `toEnd: "arrow"`), 仅在非默认时写入.
- MUST: 保证输出为合法 JSON.

## 正反例

### 正例: 最小可用 canvas

```json
{
	"nodes":[
		{"id":"754a8ef995f366bc","type":"text","text":"# Title\n\nHello canvas.","x":0,"y":0,"width":320,"height":120}
	],
	"edges":[]
}
```

### 正例: group + file + link + edge

```json
{
	"nodes":[
		{"id":"754a8ef995f366bc","type":"group","x":-40,"y":-40,"width":920,"height":520,"label":"Group A"},
		{"id":"8132d4d894c80022","type":"file","file":"assets/demo.png","x":0,"y":0,"width":360,"height":240,"color":"6"},
		{"id":"0ba565e7f30e0652","type":"link","url":"https://example.com","x":420,"y":0,"width":420,"height":240}
	],
	"edges":[
		{"id":"6fa11ab87f90b8af","fromNode":"8132d4d894c80022","fromSide":"right","toNode":"0ba565e7f30e0652","toSide":"left","label":"ref"}
	]
}
```

### 反例: `subpath` 未以 `#` 开头(可能导致消费者忽略或报错)

```json
{
	"nodes":[
		{"id":"8132d4d894c80022","type":"file","file":"doc.md","subpath":"Heading","x":0,"y":0,"width":100,"height":100}
	],
	"edges":[]
}
```

## 门禁/检查方式

- JSON 语法检查: `python3 -m json.tool your.canvas > /dev/null`
- 必填字段粗检(示例): `jq -e '.nodes and .edges' your.canvas > /dev/null`
- 非 ASCII 标点自查(示例): 见 `docs/standards/halfwidth-character-standards.md`

## 变更历史

- 2026-01-06: 初版, 基于 JSON Canvas Spec 1.0(2024-03-11).
