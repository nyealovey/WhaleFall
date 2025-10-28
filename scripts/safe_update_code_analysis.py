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
    """Analyzes a directory for file and line counts, excluding specified subdirectories."""
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
    """Organizes file data by subdirectory."""
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
    """Generates a markdown table for file type distribution."""
    table = ["| 文件类型 | 文件数量 | 代码行数 | 占比 |", "|----------|----------|----------|------|"]
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['lines'], reverse=True)

    for ext, data in sorted_stats:
        percentage = (data['lines'] / total_lines * 100) if total_lines > 0 else 0
        table.append(f"| {ext} (.{ext.lower()}) | {data['count']} | {data['lines']:,} | {percentage:.1f}% |")

    table.append(f"| **总计** | **{total_files}** | **{total_lines:,}** | **100%** |")
    return "\n".join(table)

def generate_directory_detail_table(file_list):
    """Generates a markdown table for a single directory's file breakdown."""
    table = ["| 文件 | 行数 | 功能描述 |", "|------|------|----------|"]
    for file_info in file_list:
        # In a real scenario, you might have a way to get descriptions.
        # For now, we leave it blank.
        table.append(f"| `app/{file_info['path']}` | {file_info['lines']} |          |")
    return "\n".join(table)

# --- REPORT UPDATE FUNCTION ---

def update_report(report_path, content):
    """Writes new content to the report file."""
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"报告已成功更新: {report_path}")
    except IOError as e:
        print(f"错误：无法写入报告文件 {report_path}。错误信息: {e}")

def main():
    """Main function to run the analysis and update the report."""
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