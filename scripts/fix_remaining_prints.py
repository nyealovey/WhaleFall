#!/usr/bin/env python3
"""
修复剩余的 print 语句
"""

import os
import re


def fix_remaining_prints():
    """修复剩余的 print 语句"""
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

    fixed_count = 0

    for script_file in script_files:
        if not os.path.exists(script_file):
            continue

        print(f"处理文件: {script_file}")

        with open(script_file, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 添加 logger 导入和初始化（如果还没有）
        if "from app.utils.structlog_config import get_system_logger" not in content:
            # 在文件开头添加导入
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from ") or line.strip() == "":
                    continue
                # 在第一个非导入行之前插入
                lines.insert(i, "from app.utils.structlog_config import get_system_logger")
                lines.insert(i + 1, "")
                lines.insert(i + 2, "logger = get_system_logger()")
                lines.insert(i + 3, "")
                break
            content = "\n".join(lines)

        # 简单的 print 替换
        # 替换 print("text") 为 logger.info("text")
        content = re.sub(r'print\("([^"]*)"\)', r'logger.info("\1")', content)
        content = re.sub(r"print\('([^']*)'\)", r"logger.info('\1')", content)

        # 替换 print(f"text") 为 logger.info("text")
        content = re.sub(r'print\(f"([^"]*)"\)', r'logger.info("\1")', content)
        content = re.sub(r"print\(f'([^']*)'\)", r"logger.info('\1')", content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(content)
            fixed_count += 1
            print(f"  ✅ 已修复: {script_file}")
        else:
            print(f"  ⏭️  无需修复: {script_file}")

    return fixed_count


def main():
    """主函数"""
    print("🔧 开始修复剩余的 print 语句...")

    try:
        fixed_count = fix_remaining_prints()
        print(f"\n📊 修复完成! 修复了 {fixed_count} 个文件")

    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")


if __name__ == "__main__":
    main()
