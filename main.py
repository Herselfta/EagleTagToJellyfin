#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EagleToJellyfin 主入口

用法示例：
  python main.py sync                      # 使用默认 simple 模式（推荐）
  python main.py sync --dry-run            # 模拟运行
  python main.py sync --mode legacy        # 旧流程（仅供兼容）
  python main.py schedule                  # 创建计划任务（调用 v2/setup_task.ps1）
  
说明:
    V2.1 自动化版本会自动检测标签删除并选择合适的刷新模式，无需手动指定参数！
"""

import argparse
import sys
from pathlib import Path
import subprocess

# 将 v2 目录加入路径
ROOT = Path(__file__).parent
V2_DIR = ROOT / 'v2'
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))


def run_sync_simple(extra_args=None) -> int:
    """运行 v2 简化版同步脚本"""
    cmd = [sys.executable, str(V2_DIR / 'sync_v2_simple.py')]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd)
    return proc.returncode


def run_sync_legacy(extra_args=None) -> int:
    """运行 v2 旧流程（包含同名NFO与两段刷新）"""
    # 兼容：保留 v2/sync.py，可选择使用
    cmd = [sys.executable, str(V2_DIR / 'sync.py')]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd)
    return proc.returncode


def run_schedule() -> int:
    """调用 PowerShell 创建计划任务"""
    ps1 = V2_DIR / 'setup_task.ps1'
    if not ps1.exists():
        print(f"找不到脚本: {ps1}")
        return 1
    # 使用 PowerShell 执行脚本
    cmd = [
        'pwsh',
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', str(ps1)
    ]
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(description='EagleToJellyfin 主入口')
    sub = parser.add_subparsers(dest='command', required=True)

    p_sync = sub.add_parser('sync', help='执行标签同步')
    p_sync.add_argument('--mode', choices=['simple', 'legacy'], default='simple', help='同步模式（默认simple）')
    p_sync.add_argument('--dry-run', action='store_true', help='模拟运行')
    p_sync.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    sub.add_parser('schedule', help='创建计划任务')

    args, unknown = parser.parse_known_args()

    if args.command == 'sync':
        extra = []
        if args.dry_run:
            extra.append('--dry-run')
        if args.log_level:
            extra.extend(['--log-level', args.log_level])
        if args.mode == 'simple':
            return run_sync_simple(extra)
        else:
            return run_sync_legacy(extra)

    if args.command == 'schedule':
        return run_schedule()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
