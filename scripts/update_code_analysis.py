import os
import re
from collections import defaultdict
from datetime import datetime

def analyze_directory(root_dir, excluded_dirs, file_extensions):
    """
    Analyzes a directory to count files and lines of code for specific extensions,
    excluding specified subdirectories.
    """
    stats = {
        'total_files': 0,
        'total_lines': 0,
        'by_ext': defaultdict(lambda: {'count': 0, 'lines': 0}),
        'by_dir': defaultdict(lambda: {
            'total_files': 0,
            'total_lines': 0,
            'files': [],
            'by_ext': defaultdict(lambda: {'count': 0, 'lines': 0})
        })
    }

    abs_excluded_dirs = [os.path.abspath(d) for d in excluded_dirs]

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if os.path.abspath(os.path.join(dirpath, d)) not in abs_excluded_dirs]

        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if not ext:
                base, ext = os.path.splitext(os.path.basename(filename))
            
            normalized_ext = '.yaml' if ext in ['.yaml', '.yml'] else ext

            if normalized_ext in file_extensions:
                filepath = os.path.join(dirpath, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        line_count = len(f.readlines())
                except (IOError, UnicodeDecodeError):
                    continue

                stats['total_files'] += 1
                stats['total_lines'] += line_count
                stats['by_ext'][normalized_ext]['count'] += 1
                stats['by_ext'][normalized_ext]['lines'] += line_count

                rel_path = os.path.relpath(filepath, root_dir)
                path_parts = rel_path.split(os.sep)
                
                if len(path_parts) == 1:
                    dir_key = root_dir
                else:
                    dir_key = os.path.join(root_dir, path_parts[0])

                stats['by_dir'][dir_key]['total_files'] += 1
                stats['by_dir'][dir_key]['total_lines'] += line_count
                stats['by_dir'][dir_key]['files'].append({
                    'path': os.path.relpath(filepath, '.'),
                    'lines': line_count
                })
                stats['by_dir'][dir_key]['by_ext'][normalized_ext]['count'] += 1
                stats['by_dir'][dir_key]['by_ext'][normalized_ext]['lines'] += line_count
    
    return stats

def generate_file_type_table(stats):
    """Generates the markdown table for file type distribution."""
    header = "| 文件类型 | 文件数量 | 代码行数 | 占比 |\n|----------|----------|----------|------|"
    rows = []
    
    sorted_exts = sorted(stats['by_ext'].items(), key=lambda item: item[1]['lines'], reverse=True)

    for ext, data in sorted_exts:
        ext_name = ext.replace('.', '').upper()
        percentage = (data['lines'] / stats['total_lines'] * 100) if stats['total_lines'] > 0 else 0
        rows.append(f"| {ext_name} ({ext}) | {data['count']} | {data['lines']:,} | {percentage:.1f}% |")

    total_row = f"| **总计** | **{stats['total_files']}** | **{stats['total_lines']:,}** | **100%** |"
    
    return "\n".join([header] + rows + [total_row])

def generate_directory_table(dir_stats):
    """Generates a markdown table for a single directory's file breakdown."""
    header = "| 文件 | 行数 | 功能描述 |\n|------|------|----------|"
    rows = []
    
    sorted_files = sorted(dir_stats['files'], key=lambda x: x['lines'], reverse=True)
    
    for file_info in sorted_files:
        rows.append(f"| `{file_info['path']}` | {file_info['lines']} |          |")
        
    return "\n".join([header] + rows)

def update_report(report_path, stats):
    """Updates the code analysis report file with new statistics."""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = re.sub(r"(- \*\*总文件数\*\*:) \d+个文件",
                     f"\1 {stats['total_files']}个文件", content)
    content = re.sub(r"(- \*\*总代码行数\*\*:) [\d,]+行",
                     f"\1 {stats['total_lines']:,}行", content)

    new_file_type_table = generate_file_type_table(stats)
    content = re.sub(r"(### 文件类型分布\n)(?:\|[^\n]+\n)+",
                     f"\1{new_file_type_table}\n", content, flags=re.DOTALL)

    dir_title_map = {
        'app': '### 1. 核心应用文件（app 根目录）',
        'app/routes': '### 2. 路由模块（app/routes/）',
        'app/models': '### 3. 数据模型（app/models/）',
        'app/services': '### 4. 服务层（app/services/）',
        'app/utils': '### 5. 工具类（app/utils/）',
        'app/static': '### 6. 前端资源（app/static/）',
        'app/templates': '### 7. 模板文件（app/templates/）',
        'app/config': '### 8. 配置文件（app/config/）',
        'app/tasks': '### 9. 任务模块（app/tasks/）',
        'app/constants': '### 10. 常量定义（app/constants/）',
        'app/blueprints': '#### 11.1 蓝图（app/blueprints/）',
        'app/middleware': '#### 11.2 中间件（app/middleware/）',
        'app/errors': '#### 11.3 错误处理（app/errors/）',
    }

    for dir_key, dir_data in stats['by_dir'].items():
        if dir_key in dir_title_map:
            title = re.escape(dir_title_map[dir_key])
            
            content = re.sub(fr"({title}\n- \*\*文件数\*\*:) \d+个文件",
                             f"\1 {dir_data['total_files']}个文件", content)
            content = re.sub(fr"({title}\n(?:- .*?\n)*- \*\*总行数\*\*:) [\d,]+ 行",
                             f"\1 {dir_data['total_lines']:,} 行", content)
            
            new_dir_table = generate_directory_table(dir_data)
            pattern = re.compile(fr"({title}\n(?:- .*?\n)*\n)(?:\|[^\n]+\n)+", re.DOTALL)
            content = pattern.sub(f"\1{new_dir_table}\n", content)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = re.sub(r"\*最后更新: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
                     f"*最后更新: {timestamp}",
                     content)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Report updated successfully.")

if __name__ == '__main__':
    ROOT_DIRECTORY = 'app'
    EXCLUDED_DIRECTORIES = ['app/static/vendor']
    FILE_EXTENSIONS = ['.py', '.js', '.html', '.css', '.yaml', '.yml']
    REPORT_PATH = 'docs/reports/code_analysis_report.md'

    print(f"Analyzing directory: {ROOT_DIRECTORY}...")
    analysis_stats = analyze_directory(ROOT_DIRECTORY, EXCLUDED_DIRECTORIES, FILE_EXTENSIONS)
    
    print("Updating report...")
    update_report(REPORT_PATH, analysis_stats)