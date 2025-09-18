#!/usr/bin/env python3
"""
修复测试文件中的 print 语句
将 print 语句替换为适当的日志记录或保留用于测试调试
"""

import re
from pathlib import Path


def fix_test_prints():
    """修复测试文件中的 print 语句"""
    tests_dir = Path("tests")
    fixed_count = 0

    # 遍历所有测试文件
    for test_file in tests_dir.rglob("*.py"):
        if test_file.name.startswith("__"):
            continue

        print(f"处理文件: {test_file}")

        with open(test_file, encoding="utf-8") as f:
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

        # 修复不同类型的 print 语句
        # 1. 简单的 print 语句 - 替换为 logger.debug
        content = re.sub(r'print\("([^"]*)"\)', r'logger.debug("\1")', content)
        content = re.sub(r"print\('([^']*)'\)", r"logger.debug('\1')", content)

        # 2. f-string print 语句 - 替换为 logger.debug
        content = re.sub(r'print\(f"([^"]*)"\)', r'logger.debug("\1")', content)
        content = re.sub(r"print\(f'([^']*)'\)", r"logger.debug('\1')", content)

        # 3. 特殊处理：带变量的 f-string
        # 匹配 print(f"text {var} more text") 模式
        f_string_pattern = r'print\(f"([^"]*\{[^}]*\}[^"]*)"\)'
        matches = re.findall(f_string_pattern, content)
        for match in matches:
            # 将 f-string 转换为 logger.debug 格式
            new_match = match.replace("{", "%s").replace("}", "%s")
            # 提取变量
            vars_pattern = r"\{([^}]*)\}"
            vars_matches = re.findall(vars_pattern, match)
            if vars_matches:
                vars_str = ", " + ", ".join(vars_matches)
                replacement = f'logger.debug("{new_match}"{vars_str})'
                content = content.replace(f'print(f"{match}")', replacement)

        # 4. 特殊处理：带变量的 f-string (单引号)
        f_string_pattern_single = r"print\(f'([^']*\{[^}]*\}[^']*)'\)"
        matches = re.findall(f_string_pattern_single, content)
        for match in matches:
            # 将 f-string 转换为 logger.debug 格式
            new_match = match.replace("{", "%s").replace("}", "%s")
            # 提取变量
            vars_pattern = r"\{([^}]*)\}"
            vars_matches = re.findall(vars_pattern, match)
            if vars_matches:
                vars_str = ", " + ", ".join(vars_matches)
                replacement = f"logger.debug('{new_match}'{vars_str})"
                content = content.replace(f"print(f'{match}')", replacement)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)
            fixed_count += 1
            print(f"  ✅ 已修复: {test_file}")
        else:
            print(f"  ⏭️  无需修复: {test_file}")

    return fixed_count


def main():
    """主函数"""
    print("🔧 开始修复测试文件中的 print 语句...")

    try:
        fixed_count = fix_test_prints()
        print(f"\n📊 修复完成! 修复了 {fixed_count} 个文件")

    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")


if __name__ == "__main__":
    main()
