#!/usr/bin/env python3
"""
修复脚本文件中的 print 语句
将 print 语句替换为适当的日志记录
"""

import os
import re
import sys
from pathlib import Path


def fix_print_in_scripts():
    """修复脚本文件中的 print 语句"""
    scripts_dir = Path("scripts")
    fixed_files = []

    # 需要修复的脚本文件
    script_files = [
        "scripts/quality_check.py",
        "scripts/quick_check.py",
        "scripts/batch_fix.py",
        "scripts/fix_code.py",
        "scripts/fix_priority.py",
        "scripts/fix_ruff_only.py",
        "scripts/fix_trailing_whitespace.py",
        "scripts/fix_logging_fstrings.py",
    ]

    for script_file in script_files:
        if not os.path.exists(script_file):
            continue

        print(f"处理文件: {script_file}")

        with open(script_file, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 添加 structlog 导入（如果还没有）
        if "from app.utils.structlog_config import get_system_logger" not in content:
            # 在文件开头添加导入
            lines = content.split("\n")
            import_added = False
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from ") or line.strip() == "":
                    continue
                # 在第一个非导入行之前插入
                lines.insert(i, "from app.utils.structlog_config import get_system_logger")
                lines.insert(i + 1, "")
                import_added = True
                break

            if import_added:
                content = "\n".join(lines)

        # 添加 logger 初始化
        if "logger = get_system_logger()" not in content:
            # 在导入后添加 logger 初始化
            content = content.replace(
                "from app.utils.structlog_config import get_system_logger",
                "from app.utils.structlog_config import get_system_logger\n\nlogger = get_system_logger()",
            )

        # 修复不同类型的 print 语句
        patterns = [
            # 简单的 print 语句
            (r'print\("([^"]*)"\)', r'logger.info("\1")'),
            (r"print\('([^']*)'\)", r"logger.info('\1')"),
            # f-string print 语句
            (r'print\(f"([^"]*)"\)', r'logger.info("\1")'),
            (r"print\(f'([^']*)'\)", r"logger.info('\1')"),
            # 带变量的 print 语句
            (r'print\(f"([^"]*)"\)', r'logger.info("\1")'),
            (r"print\(f'([^']*)'\)", r"logger.info('\1')"),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        # 特殊处理：带变量的 f-string
        # 匹配 print(f"text {var} more text") 模式
        f_string_pattern = r'print\(f"([^"]*\{[^}]*\}[^"]*)"\)'
        matches = re.findall(f_string_pattern, content)
        for match in matches:
            # 将 f-string 转换为 logger.info 格式
            new_match = match.replace("{", "%s").replace("}", "%s")
            # 提取变量
            vars_pattern = r"\{([^}]*)\}"
            vars_matches = re.findall(vars_pattern, match)
            if vars_matches:
                vars_str = ", " + ", ".join(vars_matches)
                replacement = f'logger.info("{new_match}"{vars_str})'
                content = content.replace(f'print(f"{match}")', replacement)

        # 特殊处理：带变量的 f-string (单引号)
        f_string_pattern_single = r"print\(f'([^']*\{[^}]*\}[^']*)'\)"
        matches = re.findall(f_string_pattern_single, content)
        for match in matches:
            # 将 f-string 转换为 logger.info 格式
            new_match = match.replace("{", "%s").replace("}", "%s")
            # 提取变量
            vars_pattern = r"\{([^}]*)\}"
            vars_matches = re.findall(vars_pattern, match)
            if vars_matches:
                vars_str = ", " + ", ".join(vars_matches)
                replacement = f"logger.info('{new_match}'{vars_str})"
                content = content.replace(f"print(f'{match}')", replacement)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(content)
            fixed_files.append(script_file)
            print(f"  ✅ 已修复: {script_file}")
        else:
            print(f"  ⏭️  无需修复: {script_file}")

    return fixed_files


def main():
    """主函数"""
    print("🔧 开始修复脚本文件中的 print 语句...")

    try:
        fixed_files = fix_print_in_scripts()

        print("\n📊 修复完成!")
        print(f"修复的文件数量: {len(fixed_files)}")

        if fixed_files:
            print("\n修复的文件:")
            for file in fixed_files:
                print(f"  - {file}")

    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
