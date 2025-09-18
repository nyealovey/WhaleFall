from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
泰摸鱼吧 - 优先级代码修复脚本
按优先级修复代码质量问题，从简单到复杂
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


def fix_step(step_name: str, cmd: list, project_root: Path) -> bool:
    """执行修复步骤"""
    logger.info("\n🔧 {step_name}...")
    returncode, stdout, stderr = run_command(cmd, project_root)

    if returncode == 0:
        logger.info("✅ {step_name} 完成")
        return True
    logger.info("❌ {step_name} 失败")
    if stderr:
        logger.info("错误: {stderr[:200]}...")
    return False


def main():
    """主函数"""
    logger.info("🚀 泰摸鱼吧 - 优先级代码修复")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 检查是否在项目根目录
    if not (project_root / "pyproject.toml").exists():
        logger.info("❌ 请在项目根目录运行此脚本")
        sys.exit(1)

    # 修复步骤（按优先级排序）
    steps = [
        # 第一步：自动修复简单问题
        ("自动修复Ruff问题", ["uv", "run", "ruff", "check", "--fix", "."]),
        # 第二步：格式化代码
        ("Black代码格式化", ["uv", "run", "black", "."]),
        # 第三步：排序导入
        ("isort导入排序", ["uv", "run", "isort", "."]),
        # 第四步：Ruff格式化
        ("Ruff代码格式化", ["uv", "run", "ruff", "format", "."]),
        # 第五步：清理未使用的导入
        ("清理未使用的导入", ["uv", "run", "ruff", "check", "--select", "F401", "--fix", "."]),
        # 第六步：清理空白行
        ("清理空白行问题", ["uv", "run", "ruff", "check", "--select", "W291,W293", "--fix", "."]),
    ]

    success_count = 0
    total_steps = len(steps)

    for step_name, cmd in steps:
        if fix_step(step_name, cmd, project_root):
            success_count += 1

    print("\n" + "=" * 50)
    logger.info("📊 修复结果: {success_count}/{total_steps} 步骤成功")

    if success_count == total_steps:
        logger.info("🎉 所有修复步骤完成！")
        logger.info("\n💡 建议运行 'make quality' 验证修复结果")
    else:
        logger.info("⚠️  部分修复步骤失败，请检查错误信息")
        logger.info("\n💡 可以手动运行失败的步骤:")
        for i, (step_name, cmd) in enumerate(steps):
            if i >= success_count:
                logger.info("  - {step_name}: {' '.join(cmd)}")


if __name__ == "__main__":
    main()
