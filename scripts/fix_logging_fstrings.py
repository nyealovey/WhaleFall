from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - 修复 logging f-string 问题
批量修复 logging 中的 f-string 使用
"""

import re
from pathlib import Path


def fix_logging_f_strings(file_path: Path) -> bool:
    """修复文件中的 logging f-string 问题"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复 logger.method(f"message {var}") 格式
        patterns = [
            # logger.info("message {var}")
            (r'(\w+)\.(info|debug|warning|error|critical|exception)\(f"([^"]*)"\)', r'\1.\2("\3")'),
            # logger.info("message {var}")
            (r"(\w+)\.(info|debug|warning|error|critical|exception)\(f\'([^\']*)\'\)", r'\1.\2("\3")'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        # 修复更复杂的 f-string 格式
        # logger.info("message {var} more text")
        complex_pattern = r'(\w+)\.(info|debug|warning|error|critical|exception)\(f"([^"]*\{[^}]*\}[^"]*)"\)'

        def replace_complex(match):
            logger_name = match.group(1)
            method = match.group(2)
            message = match.group(3)

            # 提取变量
            variables = re.findall(r"\{([^}]+)\}", message)
            if not variables:
                return match.group(0)

            # 构建新的格式字符串
            format_message = re.sub(r"\{[^}]+\}", "%s", message)
            args = ", ".join(variables)

            return f'{logger_name}.{method}("{format_message}", {args})'

        content = re.sub(complex_pattern, replace_complex, content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception:
        logger.info("修复 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    logger.info("🔧 泰摸鱼吧 - 修复 logging f-string 问题")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 获取所有Python文件
    python_files = list(project_root.rglob("*.py"))
    # 排除一些目录
    excluded_dirs = {"migrations", "userdata", "venv", ".venv", "__pycache__", ".git"}
    python_files = [f for f in python_files if not any(d in f.parts for d in excluded_dirs)]

    logger.info("📁 找到 {len(python_files)} 个Python文件")

    fixed_files = 0
    for file_path in python_files:
        if fix_logging_f_strings(file_path):
            logger.info("✅ 修复了: {file_path.relative_to(project_root)}")
            fixed_files += 1

    logger.info("\n🎉 总共修复了 {fixed_files} 个文件")
    logger.info("💡 建议运行 'make quality' 验证修复结果")


if __name__ == "__main__":
    main()
