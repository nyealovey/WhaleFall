#!/usr/bin/env python3
"""
修复剩余的 print 语句
"""

import os
import re


def fix_final_prints():
    """修复剩余的 print 语句"""
    # 需要修复的文件
    files_to_fix = [
        "tests/integration/test_database.py",
        "tests/integration/test_api_logging.py",
        "tests/integration/test_all_admin_pages.py",
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            continue

        print(f"处理文件: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复分隔线 print 语句
        # print("=" * 50) -> logger.debug("=" * 50)
        content = re.sub(r'print\("=" \* \d+\)', r'logger.debug("=" * 50)', content)
        content = re.sub(r"print\('=' \* \d+\)", r"logger.debug('=' * 50)", content)

        # 修复其他简单的 print 语句
        content = re.sub(r'print\("([^"]*)"\)', r'logger.debug("\1")', content)
        content = re.sub(r"print\('([^']*)'\)", r"logger.debug('\1')", content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            fixed_count += 1
            print(f"  ✅ 已修复: {file_path}")
        else:
            print(f"  ⏭️  无需修复: {file_path}")

    return fixed_count


def main():
    """主函数"""
    print("🔧 开始修复剩余的 print 语句...")

    try:
        fixed_count = fix_final_prints()
        print(f"\n📊 修复完成! 修复了 {fixed_count} 个文件")

    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")


if __name__ == "__main__":
    main()
