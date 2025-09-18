#!/usr/bin/env python3
"""
泰摸鱼吧 - 批量修复脚本
批量修复常见的代码质量问题
"""

import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, cwd: Path = None) -> tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or Path(__file__).parent.parent, capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def fix_logging_f_strings(file_path: Path) -> bool:
    """修复logging中的f-string问题"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 查找并替换logging中的f-string
        patterns = [
            # logger.info("message {var}")
            (r'(\w+)\.(info|debug|warning|error|critical)\(f"([^"]*)"\)', r'\1.\2("\3")'),
            # logger.info("message {var}")
            (r"(\w+)\.(info|debug|warning|error|critical)\(f\'([^\']*)\'\)", r'\1.\2("\3")'),
        ]

        original_content = content
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception:
        logger.info("修复 {file_path} 时出错: {e}")
        return False


def fix_print_statements(file_path: Path) -> bool:
    """修复print语句，替换为适当的日志记录"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 检查是否已经有logger导入
        has_logger_import = "from app.utils.structlog_config import get_system_logger" in content

        # 查找print语句
        print_pattern = r"print\(([^)]+)\)"
        matches = re.findall(print_pattern, content)

        if not matches:
            return False

        # 如果文件没有logger导入，添加导入
        if not has_logger_import and "print(" in content:
            # 在文件开头添加导入
            import_line = "from app.utils.structlog_config import get_system_logger\n\nlogger = get_system_logger()\n"

            # 找到第一个import语句的位置
            import_match = re.search(r"^import |^from ", content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.start()
                content = content[:insert_pos] + import_line + content[insert_pos:]
            else:
                # 如果没有import语句，在文件开头添加
                content = import_line + content

        # 替换print语句
        def replace_print(match):
            print_content = match.group(1)
            return f"get_system_logger().info({print_content})"

        content = re.sub(print_pattern, replace_print, content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        logger.info("修复 {file_path} 时出错: {e}")
        return False


def fix_trailing_whitespace(file_path: Path) -> bool:
    """修复行尾空白字符"""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        modified = False
        for i, line in enumerate(lines):
            if line.rstrip() != line.rstrip(" \t"):
                lines[i] = line.rstrip() + "\n"
                modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        return False
    except Exception:
        logger.info("修复 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    logger.info("🔧 泰摸鱼吧 - 批量修复脚本")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 检查是否在项目根目录
    if not (project_root / "pyproject.toml").exists():
        logger.info("❌ 请在项目根目录运行此脚本")
        sys.exit(1)

    # 获取所有Python文件
    python_files = list(project_root.rglob("*.py"))
    # 排除一些目录
    excluded_dirs = {"migrations", "userdata", "venv", ".venv", "__pycache__", ".git"}
    python_files = [f for f in python_files if not any(d in f.parts for d in excluded_dirs)]

    logger.info("📁 找到 {len(python_files)} 个Python文件")

    # 修复统计
    fixes = {
        "logging_f_strings": 0,
        "print_statements": 0,
        "trailing_whitespace": 0,
    }

    for file_path in python_files:
        logger.info("🔍 处理: {file_path.relative_to(project_root)}")

        # 修复logging f-string
        if fix_logging_f_strings(file_path):
            fixes["logging_f_strings"] += 1
            logger.info("  ✅ 修复了logging f-string")

        # 修复print语句
        if fix_print_statements(file_path):
            fixes["print_statements"] += 1
            logger.info("  ✅ 修复了print语句")

        # 修复行尾空白
        if fix_trailing_whitespace(file_path):
            fixes["trailing_whitespace"] += 1
            logger.info("  ✅ 修复了行尾空白")

    print("\n" + "=" * 50)
    logger.info("📊 修复统计:")
    logger.info("  - 修复logging f-string: {fixes['logging_f_strings']} 个文件")
    logger.info("  - 修复print语句: {fixes['print_statements']} 个文件")
    logger.info("  - 修复行尾空白: {fixes['trailing_whitespace']} 个文件")

    total_fixes = sum(fixes.values())
    if total_fixes > 0:
        logger.info("\n🎉 总共修复了 {total_fixes} 个文件")
        logger.info("💡 建议运行 'make quality' 验证修复结果")
    else:
        logger.info("\n✅ 没有发现需要修复的问题")


if __name__ == "__main__":
    main()
