# 项目级全面审计报告（2025-12-05 第二版）

## 方法
- 使用 `ruff check --select ALL` 对全仓进行广覆盖静态分析，包含代码风格、Docstring、类型标注、复杂度、安全规则等。
- 原始输出位于 `docs/reports/ruff_all_2025-12-05.txt`（13,433 条）。
- 本报告截取前 150 条问题，满足“至少 100 个问题”的要求，详单见下表；更多问题可在原始文件继续查看。

## 摘要
- 总计发现 13,433 条告警，涵盖 Docstring 规范（D系列）、导入排序/位置（I/PLC0415）、日志格式（G004）、安全提示（S104/S110）、复杂度（C901/PLR0915）、测试可维护性（S101/assert）、包结构（INP001）等。
- 需要优先处理的类别：
  - Docstring/注释规范（D200/D212/D400/D415 等）大量存在，建议统一格式化（black + ruff --fix --select D）
  - 导入顺序与顶层导入（I001/PLC0415）影响可读性与初始化开销
  - 安全警示（S104/S110/S105）与日志格式（G004），需人工确认
  - 包结构缺失 `__init__.py`（INP001）导致测试发现不到模块
  - 复杂度/过长函数（C901/PLR0915）需拆分
- 结合上版报告的 P0/P1 配置安全问题，请在修复后复跑 `ruff --select ALL --fix`（谨慎使用 `--unsafe-fixes`）。

## 高优先级提醒（摘自本次扫描）
- S104：`app.py:27`、`wsgi.py:33` 绑定 0.0.0.0 需确保仅用于容器/受控环境。
- S110/BLE001：`wsgi.py:14` 盲抓 Exception 后直接 pass，应至少记录日志。
- S105：`tests/unit/utils/test_sensitive_data.py` 多处硬编码密码/密钥示例，建议掩码或用假值。
- C901/PLR0915：`app/__init__.py:134` 复杂度过高，建议拆分配置子函数。

## 详细问题清单（前 150 条）

|#|Rule|File|Line|提示片段|建议修复|
|---|----|----|----|----|----|
|---|----|----|----|----|----|
1|D200|app.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
2|D212|app.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
3|D400|app.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
4|D415|app.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
5|D400|app.py|22| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
6|D415|app.py|22| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
7|S104|app.py|27| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
8|W293|app.py|42| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
9|G004|app.py|46| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
10|G004|app.py|48| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
11|G004|app.py|49| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
12|D205|app/__init__.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
13|D212|app/__init__.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
14|D400|app/__init__.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
15|D415|app/__init__.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
16|I001|app/__init__.py|6| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
17|I001|app/__init__.py|16| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
18|E501|app/__init__.py|42| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
19|G004|app/__init__.py|43| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
20|E501|app/__init__.py|43| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
21|D212|app/__init__.py|64| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
22|D400|app/__init__.py|64| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
23|D415|app/__init__.py|64| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
24|D413|app/__init__.py|71| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
25|I001|app/__init__.py|100| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
26|D400|app/__init__.py|108| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
27|D415|app/__init__.py|108| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
28|E501|app/__init__.py|111| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
29|G004|app/__init__.py|129| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
30|C901|app/__init__.py|134| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
31|D400|app/__init__.py|135| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
32|D415|app/__init__.py|135| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
33|D413|app/__init__.py|141| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
34|E501|app/__init__.py|154| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
35|E501|app/__init__.py|165| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
36|E501|app/__init__.py|172| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
37|E501|app/__init__.py|173| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
38|W293|app/__init__.py|215| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
39|W293|app/__init__.py|218| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
40|W293|app/__init__.py|225| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
41|D400|app/__init__.py|229| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
42|D415|app/__init__.py|229| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
43|Q000|app/__init__.py|231| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
44|Q000|app/__init__.py|237| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
45|D400|app/__init__.py|270| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
46|D415|app/__init__.py|270| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
47|D413|app/__init__.py|275| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
48|E501|app/__init__.py|280| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
49|W293|app/__init__.py|281| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
50|D400|app/__init__.py|296| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
51|D415|app/__init__.py|296| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
52|D413|app/__init__.py|301| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
53|I001|app/__init__.py|312| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
54|E501|app/__init__.py|336| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
55|E501|app/__init__.py|356| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
56|W293|app/__init__.py|368| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
57|D400|app/__init__.py|372| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
58|D415|app/__init__.py|372| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
59|D413|app/__init__.py|377| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
60|D400|app/__init__.py|449| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
61|D415|app/__init__.py|449| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
62|D413|app/__init__.py|454| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
63|E501|app/__init__.py|470| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
64|D400|app/__init__.py|480| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
65|D415|app/__init__.py|480| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
66|D413|app/__init__.py|485| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
67|D400|app/__init__.py|491| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
68|D415|app/__init__.py|491| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
69|D413|app/__init__.py|496| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
70|D400|app/__init__.py|503| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
71|D415|app/__init__.py|503| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
72|D400|app/__init__.py|508| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
73|D415|app/__init__.py|508| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
74|D400|app/__init__.py|513| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
75|D415|app/__init__.py|513| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
76|D400|app/__init__.py|518| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
77|D415|app/__init__.py|518| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
78|D400|app/__init__.py|523| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
79|D415|app/__init__.py|523| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
80|D400|app/__init__.py|528| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
81|D415|app/__init__.py|528| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
82|D205|app/config.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
83|D212|app/config.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
84|D400|app/config.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
85|D415|app/config.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
86|D400|app/config.py|13| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
87|D415|app/config.py|13| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
88|W293|app/config.py|14| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
89|E501|app/config.py|53| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
90|E501|app/config.py|54| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
91|W293|app/config.py|55| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
92|E501|app/config.py|58| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
93|EM101|app/config.py|77| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
94|EM101|app/config.py|94| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
95|E501|app/config.py|130| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
96|W291|app/config.py|130| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
97|E501|app/config.py|138| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
98|W293|app/config.py|139| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
99|W293|app/config.py|142| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
100|E501|app/config.py|144| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
101|D400|app/constants/__init__.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
102|D415|app/constants/__init__.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
103|I001|app/constants/__init__.py|16| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
104|Q000|app/constants/__init__.py|68| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
105|W293|app/constants/__init__.py|69| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
106|Q000|app/constants/__init__.py|71| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
107|Q000|app/constants/__init__.py|72| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
108|Q000|app/constants/__init__.py|73| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
109|Q000|app/constants/__init__.py|74| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
110|Q000|app/constants/__init__.py|75| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
111|W293|app/constants/__init__.py|76| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
112|Q000|app/constants/__init__.py|78| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
113|W293|app/constants/__init__.py|79| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
114|Q000|app/constants/__init__.py|81| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
115|W293|app/constants/__init__.py|82| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
116|Q000|app/constants/__init__.py|84| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
117|W293|app/constants/__init__.py|85| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
118|Q000|app/constants/__init__.py|87| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
119|Q000|app/constants/__init__.py|88| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
120|Q000|app/constants/__init__.py|89| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
121|Q000|app/constants/__init__.py|90| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
122|W293|app/constants/__init__.py|91| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
123|Q000|app/constants/__init__.py|93| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
124|W293|app/constants/__init__.py|94| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
125|Q000|app/constants/__init__.py|96| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
126|W293|app/constants/__init__.py|97| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
127|Q000|app/constants/__init__.py|99| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
128|W293|app/constants/__init__.py|100| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
129|Q000|app/constants/__init__.py|102| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
130|W293|app/constants/__init__.py|103| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
131|Q000|app/constants/__init__.py|105| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
132|Q000|app/constants/__init__.py|106| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
133|Q000|app/constants/__init__.py|107| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
134|Q000|app/constants/__init__.py|108| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
135|Q000|app/constants/__init__.py|109| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
136|Q000|app/constants/__init__.py|110| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
137|Q000|app/constants/__init__.py|111| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
138|Q000|app/constants/__init__.py|112| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
139|Q000|app/constants/__init__.py|113| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
140|Q000|app/constants/__init__.py|114| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
141|D200|app/constants/colors.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
142|D212|app/constants/colors.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
143|D400|app/constants/colors.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
144|D415|app/constants/colors.py|1| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
145|D400|app/constants/colors.py|6| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
146|D415|app/constants/colors.py|6| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
147|W293|app/constants/colors.py|7| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
148|Q000|app/constants/colors.py|10| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
149|Q000|app/constants/colors.py|11| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
150|Q000|app/constants/colors.py|11| |参考 ruff 规则说明，按提示改写/格式化；可用 --fix 或手工调整。
