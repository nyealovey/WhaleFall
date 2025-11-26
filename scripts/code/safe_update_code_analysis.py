"""维护 docs/reports/code_analysis_report.md 的静态代码分析脚本。

扫描 app 目录统计文件数量与行数，生成 Markdown 表格并写回报告。
"""

import os
import re
from collections import defaultdict
from datetime import datetime

# --- CONFIGURATION ---
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
REPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docs/reports/code_analysis_report.md'))
EXCLUDE_DIRS = [os.path.join(APP_DIR, 'static/vendor')]
FILE_EXTENSIONS = ('.py', '.js', '.html', '.css', '.yaml', '.yml')

# --- ANALYSIS FUNCTIONS ---

def analyze_directory(path, exclude_dirs, extensions):
    """扫描目录并应用排除与扩展名过滤规则。

    Args:
        path: 需要分析的应用目录绝对路径。
        exclude_dirs: 需要忽略的子目录前缀列表。
        extensions: 允许统计的文件扩展名，包含开头的点。

    Returns:
        tuple[dict[str, dict[str, int]], list[dict[str, int]]]:
        第一个元素按扩展名聚合文件数量与行数，第二个元素列出单个文件
        的路径和行数，供后续报告生成使用。
    """
    file_stats = defaultdict(lambda: {'count': 0, 'lines': 0})
    detailed_files = []

    for root, _, files in os.walk(path):
        if any(root.startswith(excluded) for excluded in exclude_dirs):
            continue

        for file in files:
            if not file.endswith(extensions):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
            except (IOError, OSError):
                line_count = 0

            ext = os.path.splitext(file)[1].upper().replace('.', '')
            if ext == "YML": ext = "YAML"

            file_stats[ext]['count'] += 1
            file_stats[ext]['lines'] += line_count
            detailed_files.append({
                'path': os.path.relpath(file_path, APP_DIR),
                'lines': line_count
            })

    return dict(file_stats), detailed_files

def get_directory_breakdown(detailed_files):
    """按子目录聚合文件统计数据。

    Args:
        detailed_files: ``analyze_directory`` 返回的文件信息列表，包含相对
            路径与行数。

    Returns:
        dict[str, dict[str, object]]: 以目录名为键的统计结果，记录文件数、
        行数以及排序后的文件详情。
    """
    breakdown = defaultdict(lambda: {'count': 0, 'lines': 0, 'files': []})
    for file_info in detailed_files:
        dir_name = os.path.dirname(file_info['path'])
        if dir_name == "":
            dir_name = "app 根目录"
        else:
            dir_name = f"app/{dir_name}"

        breakdown[dir_name]['count'] += 1
        breakdown[dir_name]['lines'] += file_info['lines']
        breakdown[dir_name]['files'].append(file_info)

    # Sort files within each directory by line count, descending
    for data in breakdown.values():
        data['files'].sort(key=lambda x: x['lines'], reverse=True)

    return dict(breakdown)

# --- MARKDOWN GENERATION ---

def generate_file_type_table(stats, total_files, total_lines):
    """生成文件类型分布的 Markdown 表格。

    Args:
        stats: 以扩展名为键的统计字典，包含 ``count`` 与 ``lines``。
        total_files: 所有扩展名的文件总数。
        total_lines: 所有扩展名的总行数。

    Returns:
        str: 可直接嵌入报告正文的 Markdown 表格文本。
    """
    table = ["| 文件类型 | 文件数量 | 代码行数 | 占比 |", "|----------|----------|----------|------|"]
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['lines'], reverse=True)

    for ext, data in sorted_stats:
        percentage = (data['lines'] / total_lines * 100) if total_lines > 0 else 0
        table.append(f"| {ext} (.{ext.lower()}) | {data['count']} | {data['lines']:,} | {percentage:.1f}% |")

    table.append(f"| **总计** | **{total_files}** | **{total_lines:,}** | **100%** |")
    return "\n".join(table)

def generate_directory_detail_table(file_list):
    """生成单个目录的文件明细表格。

    Args:
        file_list: 包含 ``path`` 与 ``lines`` 键的文件信息序列。

    Returns:
        str: 可插入目录标题下方的 Markdown 表格片段。
    """
    table = ["| 文件 | 行数 | 功能描述 |", "|------|------|----------|"]
    for file_info in file_list:
        # In a real scenario, you might have a way to get descriptions.
        # For now, we leave it blank.
        table.append(f"| `app/{file_info['path']}` | {file_info['lines']} |          |")
    return "\n".join(table)

# --- REPORT UPDATE FUNCTION ---

def update_report(report_path, content):
    """将生成的报告内容写回磁盘。

    Args:
        report_path: Markdown 报告文件的绝对路径。
        content: 已渲染完成的 Markdown 字符串。

    Returns:
        None: 通过写文件产生副作用，不返回值。
    """
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"报告已成功更新: {report_path}")
    except IOError as e:
        print(f"错误：无法写入报告文件 {report_path}。错误信息: {e}")

def main():
    """执行分析流程并刷新 Markdown 报告。

    Returns:
        None: 以 CLI 形式运行，仅打印日志并写入文件。
    """
    print("开始分析项目代码...")
    file_stats, detailed_files = analyze_directory(APP_DIR, EXCLUDE_DIRS, FILE_EXTENSIONS)

    total_files = sum(data['count'] for data in file_stats.values())
    total_lines = sum(data['lines'] for data in file_stats.values())

    print("正在读取原始报告...")
    try:
        with open(REPORT_PATH, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except FileNotFoundError:
        print(f"错误: 报告文件未找到 at {REPORT_PATH}")
        return

    # --- Replace Project Overview ---
    overview_section = f"## 项目概览\n- **总文件数**: {total_files}个文件（仅统计代码文件，不包含 `app/static/vendor`）\n- **总代码行数**: {total_lines:,}行（.py/.html/.js/.css/.yaml/.yml）"
    new_content = re.sub(r"## 项目概览\n- \*\*总文件数\*\*:.*?行（.*?）", overview_section, original_content, flags=re.DOTALL)

    # --- Replace File Type Distribution Table ---
    file_type_table = generate_file_type_table(file_stats, total_files, total_lines)
    dist_header = "### 文件类型分布"
    new_content = re.sub(f"({dist_header}\n)(\| 文件类型.*?\|.*?\|\n(?:\|---.*?\|\n)+)(?:\| \*\*总计\*\*.*?\|)",
                         f"\1{file_type_table}", new_content, flags=re.DOTALL)

    # --- Rebuild Directory Breakdown Section ---
    dir_breakdown = get_directory_breakdown(detailed_files)
    
    dir_analysis_start_marker = "## 目录结构分析（app/）"
    quality_analysis_start_marker = "## 代码质量分析"
    
    try:
        dir_analysis_start_index = new_content.index(dir_analysis_start_marker)
        quality_analysis_start_index = new_content.index(quality_analysis_start_marker)
        
        content_before = new_content[:dir_analysis_start_index]
        content_after = new_content[quality_analysis_start_index:]

        new_dir_analysis_section = [dir_analysis_start_marker, ""]
        
        # Manually order some key directories first
        order = ["app 根目录", "app/routes", "app/models", "app/services", "app/utils", "app/static/js", "app/static/css"]
        sorted_dir_keys = [d for d in order if d in dir_breakdown] + [d for d in sorted(dir_breakdown.keys()) if d not in order]

        for i, dir_name in enumerate(sorted_dir_keys, 1):
            data = dir_breakdown[dir_name]
            display_name = dir_name.replace("app/", "").replace("app ", "")
            if display_name == "根目录":
                display_name = "核心应用文件（app 根目录）"
            else:
                display_name = f"{display_name.replace('/', ' ').title()}模块（{dir_name}/）"

            new_dir_analysis_section.append(f"### {i}. {display_name}")
            new_dir_analysis_section.append(f"- **文件数**: {data['count']}个文件")
            new_dir_analysis_section.append(f"- **总行数**: {data['lines']:,} 行")
            new_dir_analysis_section.append("")
            new_dir_analysis_section.append(generate_directory_detail_table(data['files']))
            new_dir_analysis_section.append("")

        final_content = content_before + "\n".join(new_dir_analysis_section) + content_after
        final_content = re.sub(r'\n\n\n+', '\n\n', final_content)
        
        # Add a timestamp before the final appendix
        timestamp = f"\n*报告最后更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        final_content = final_content.replace("## 附录", f"{timestamp}\n## 附录")

        update_report(REPORT_PATH, final_content)

    except ValueError:
        print("错误: 无法在报告中找到预期的标记 '## 目录结构分析（app/）' 或 '## 代码质量分析'。更新中止。")

if __name__ == "__main__":
    main()
