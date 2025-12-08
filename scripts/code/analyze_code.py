#!/usr/bin/env python3
"""
代码统计分析脚本
用于生成项目代码的详细统计报告
"""

import os
import json
from collections import defaultdict
from datetime import datetime

def count_lines(filepath):
    """统计指定文件的有效行数。

    Args:
        filepath: 需要统计的文件路径，可以是绝对路径或相对路径。

    Returns:
        int: 文件行数；当文件不可读或解码失败时返回 0。

    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except:
        return 0

def analyze_directory(base_dir, exclude_patterns=None):
    """
    分析目录结构和代码统计
    
    Args:
        base_dir: 要分析的基础目录
        exclude_patterns: 要排除的路径模式列表
    
    Returns:
        dict: 包含统计信息的字典

    """
    if exclude_patterns is None:
        exclude_patterns = ["vendor", "__pycache__", ".git", "node_modules"]

    files_by_dir = defaultdict(list)
    total_files = 0
    total_lines = 0
    stats_by_ext = defaultdict(lambda: {"count": 0, "lines": 0})

    # 支持的文件扩展名
    valid_extensions = (".py", ".js", ".css", ".html", ".yaml", ".yml", ".json")

    for root, dirs, files in os.walk(base_dir):
        # 排除指定目录
        if any(pattern in root for pattern in exclude_patterns):
            continue

        for file in files:
            if file.endswith(valid_extensions):
                filepath = os.path.join(root, file)
                lines = count_lines(filepath)
                rel_path = os.path.relpath(filepath, base_dir)
                ext = os.path.splitext(file)[1]

                # 获取目录
                dir_path = os.path.dirname(rel_path) if os.path.dirname(rel_path) else "根目录"

                files_by_dir[dir_path].append({
                    "name": rel_path,
                    "lines": lines,
                    "ext": ext
                })

                total_files += 1
                total_lines += lines
                stats_by_ext[ext]["count"] += 1
                stats_by_ext[ext]["lines"] += lines


    return {
        "files_by_dir": dict(files_by_dir),
        "total_files": total_files,
        "total_lines": total_lines,
        "stats_by_ext": dict(stats_by_ext)
    }

def print_summary(stats):
    """打印汇总统计信息。

    Args:
        stats: ``analyze_directory`` 生成的聚合统计字典。

    Returns:
        None: 仅向标准输出打印结果，不返回值。

    """
    print("=" * 60)
    print("代码统计摘要")
    print("=" * 60)
    print(f"总文件数: {stats['total_files']}")
    print(f"总代码行数: {stats['total_lines']:,}")
    print()

    print("按文件类型统计:")
    print("-" * 60)
    for ext, data in sorted(stats["stats_by_ext"].items(), 
                           key=lambda x: x[1]["lines"], reverse=True):
        percentage = (data["lines"] / stats["total_lines"] * 100) if stats["total_lines"] > 0 else 0
        print(f"{ext:10s} {data['count']:4d} 个文件  {data['lines']:8,} 行  {percentage:5.1f}%")
    print()

def print_top_files(stats, top_n=20):
    """展示行数最多的文件列表。

    Args:
        stats: 包含 ``files_by_dir`` 的聚合统计数据。
        top_n: 需要展示的文件数量，默认 20 个。

    Returns:
        None: 结果打印到标准输出，不返回值。

    """
    all_files = []
    for dir_path, files in stats["files_by_dir"].items():
        for file_info in files:
            all_files.append({
                "path": file_info["name"],
                "lines": file_info["lines"]
            })

    all_files.sort(key=lambda x: x["lines"], reverse=True)

    print(f"代码行数最多的 {top_n} 个文件:")
    print("-" * 60)
    for i, file_info in enumerate(all_files[:top_n], 1):
        print(f"{i:2d}. {file_info['path']:50s} {file_info['lines']:6,} 行")
    print()

def export_to_json(stats, output_file):
    """将统计结果导出为 JSON 文件。

    Args:
        stats: ``analyze_directory`` 返回的统计字典。
        output_file: JSON 输出路径。

    Returns:
        None: 以写文件的方式产生副作用，不返回值。

    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"统计结果已导出到: {output_file}")

def generate_markdown_report(stats, output_file):
    """生成 Markdown 版本的代码统计报告。

    Args:
        stats: ``analyze_directory`` 生成的统计字典。
        output_file: Markdown 报告写入路径。

    Returns:
        None: 结果写入到文件系统，不返回值。

    """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 代码统计报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 总体统计\n\n")
        f.write(f"- 总文件数: {stats['total_files']}\n")
        f.write(f"- 总代码行数: {stats['total_lines']:,}\n\n")

        f.write("## 按文件类型统计\n\n")
        f.write("| 文件类型 | 文件数量 | 代码行数 | 占比 |\n")
        f.write("|----------|----------|----------|------|\n")

        for ext, data in sorted(stats["stats_by_ext"].items(), 
                               key=lambda x: x[1]["lines"], reverse=True):
            percentage = (data["lines"] / stats["total_lines"] * 100) if stats["total_lines"] > 0 else 0
            f.write(f"| {ext} | {data['count']} | {data['lines']:,} | {percentage:.1f}% |\n")

        f.write("\n## 按目录统计\n\n")
        for dir_path in sorted(stats["files_by_dir"].keys()):
            files = stats["files_by_dir"][dir_path]
            total_dir_lines = sum(f["lines"] for f in files)
            f.write(f"### {dir_path}\n\n")
            f.write(f"- 文件数: {len(files)}\n")
            f.write(f"- 总行数: {total_dir_lines:,}\n\n")

            f.write("| 文件 | 行数 |\n")
            f.write("|------|------|\n")
            for file_info in sorted(files, key=lambda x: x["lines"], reverse=True):
                f.write(f"| `{file_info['name']}` | {file_info['lines']} |\n")
            f.write("\n")

    print(f"Markdown报告已生成: {output_file}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="代码统计分析工具")
    parser.add_argument("directory", nargs="?", default="app", 
                       help="要分析的目录 (默认: app)")
    parser.add_argument("--exclude", nargs="+", 
                       default=["vendor", "__pycache__", ".git"],
                       help="要排除的目录模式")
    parser.add_argument("--json", help="导出JSON文件路径")
    parser.add_argument("--markdown", help="导出Markdown报告路径")
    parser.add_argument("--top", type=int, default=20, 
                       help="显示前N个最大文件 (默认: 20)")

    args = parser.parse_args()

    print(f"正在分析目录: {args.directory}")
    print(f"排除模式: {', '.join(args.exclude)}\n")

    # 执行分析
    stats = analyze_directory(args.directory, args.exclude)

    # 打印摘要
    print_summary(stats)

    # 打印最大文件
    print_top_files(stats, args.top)

    # 导出结果
    if args.json:
        export_to_json(stats, args.json)

    if args.markdown:
        generate_markdown_report(stats, args.markdown)
