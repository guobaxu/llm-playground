#!/usr/bin/env python3
"""
开发脚本 - 使用uv管理项目
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """运行命令并返回退出码"""
    print(f"运行命令: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode


def install():
    """安装依赖"""
    print("安装依赖...")
    return run_command(["uv", "sync"])


def test():
    """运行测试"""
    print("运行测试...")
    return run_command(["uv", "run", "pytest", "tests/", "-v"])


def format_code():
    """格式化代码"""
    print("格式化代码...")
    return run_command(["uv", "run", "black", "llm_playground/", "tests/"])


def lint():
    """代码检查"""
    print("代码检查...")
    return run_command(["uv", "run", "flake8", "llm_playground/", "tests/"])


def type_check():
    """类型检查"""
    print("类型检查...")
    return run_command(["uv", "run", "mypy", "llm_playground/"])


def clean():
    """清理缓存"""
    print("清理缓存...")
    import shutil
    
    # 清理Python缓存
    for pattern in ["**/__pycache__", "**/*.pyc", "**/*.pyo"]:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    
    # 清理pytest缓存
    pytest_cache = Path(".pytest_cache")
    if pytest_cache.exists():
        shutil.rmtree(pytest_cache)
    
    print("缓存清理完成!")


def dev_setup():
    """开发环境设置"""
    print("设置开发环境...")
    steps = [
        ("安装依赖", install),
        ("格式化代码", format_code),
        ("运行测试", test),
    ]
    
    for step_name, step_func in steps:
        print(f"\n--- {step_name} ---")
        if step_func() != 0:
            print(f"[ERROR] {step_name} 失败")
            return 1
        print(f"[OK] {step_name} 成功")
    
    print("\n[SUCCESS] 开发环境设置完成!")
    return 0


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python scripts/dev.py <command>")
        print("可用命令:")
        print("  install    - 安装依赖")
        print("  test       - 运行测试")
        print("  format     - 格式化代码")
        print("  lint       - 代码检查")
        print("  type-check - 类型检查")
        print("  clean      - 清理缓存")
        print("  setup      - 开发环境设置")
        return 1
    
    command = sys.argv[1]
    
    commands = {
        "install": install,
        "test": test,
        "format": format_code,
        "lint": lint,
        "type-check": type_check,
        "clean": clean,
        "setup": dev_setup,
    }
    
    if command not in commands:
        print(f"未知命令: {command}")
        return 1
    
    return commands[command]()


if __name__ == "__main__":
    sys.exit(main())
