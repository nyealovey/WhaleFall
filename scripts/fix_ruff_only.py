from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - Ruff问题修复脚本
专门修复Ruff发现的问题
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, cwd: Path = None) -> tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or Path(__file__).parent.parent, capture_output=True, text=True, timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def main():
    """主函数"""
    logger.info("🔍 泰摸鱼吧 - Ruff问题修复")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 检查是否在项目根目录
    if not (project_root / "pyproject.toml").exists():
        logger.info("❌ 请在项目根目录运行此脚本")
        sys.exit(1)

    # Ruff修复步骤
    steps = [
        # 第一步：自动修复可修复的问题
        ("自动修复Ruff问题", ["uv", "run", "ruff", "check", "--fix", "."]),
        # 第二步：修复导入排序问题
        ("修复导入排序", ["uv", "run", "ruff", "check", "--select", "I001", "--fix", "."]),
        # 第三步：清理空白行
        ("清理空白行", ["uv", "run", "ruff", "check", "--select", "W291,W293", "--fix", "."]),
        # 第四步：清理未使用的导入
        ("清理未使用的导入", ["uv", "run", "ruff", "check", "--select", "F401", "--fix", "."]),
        # 第五步：清理未使用的变量
        ("清理未使用的变量", ["uv", "run", "ruff", "check", "--select", "F841", "--fix", "."]),
        # 第六步：修复简单的代码风格问题
        ("修复代码风格", ["uv", "run", "ruff", "check", "--select", "SIM108,SIM102", "--fix", "."]),
    ]

    success_count = 0
    total_steps = len(steps)

    for step_name, cmd in steps:
        logger.info("\n🔧 {step_name}...")
        returncode, stdout, stderr = run_command(cmd, project_root)

        if returncode == 0:
            logger.info("✅ {step_name} 完成")
            success_count += 1
        else:
            logger.info("❌ {step_name} 失败")
            if stderr:
                logger.info("错误: {stderr[:200]}...")

    print("\n" + "=" * 50)
    logger.info("📊 修复结果: {success_count}/{total_steps} 步骤成功")

    # 检查剩余问题
    logger.info("\n🔍 检查剩余问题...")
    check_cmd = ["uv", "run", "ruff", "check", ".", "--statistics"]
    returncode, stdout, stderr = run_command(check_cmd, project_root)

    if returncode == 0:
        logger.info("🎉 所有Ruff问题已修复！")
    else:
        logger.info("⚠️  仍有Ruff问题需要手动修复")
        logger.info("统计信息: {stdout.strip()}")

        # 显示剩余问题类型
        logger.info("\n📋 剩余问题类型:")
        for line in stdout.split("\n"):
            if (
                "Found" in line
                and "errors" in line
                or line.strip()
                and not line.startswith("[")
                and not line.startswith("Found")
            ):
                logger.info("  - {line.strip()}")

    logger.info("\n💡 建议:")
    logger.info("  - 运行 'make quality' 验证修复结果")
    logger.info("  - 查看详细报告: cat userdata/logs/fix_suggestions.md")


if __name__ == "__main__":
    main()
