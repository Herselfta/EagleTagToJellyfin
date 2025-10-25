#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境验证脚本
检查运行环境是否满足要求
"""

import sys
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 8):
        print("❌ Python 版本过低，需要 3.8 或更高")
        print(f"   当前版本: {sys.version}")
        return False
    print(f"✅ Python 版本: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import requests
        print(f"✅ requests 已安装 (版本: {requests.__version__})")
        return True
    except ImportError:
        print("❌ requests 未安装")
        print("   请运行: pip install -r v2/requirements.txt")
        return False

def check_config():
    """检查配置文件"""
    config_file = Path(__file__).parent / 'v2' / 'config.json'
    config_example = Path(__file__).parent / 'v2' / 'config.json.example'
    
    if not config_file.exists():
        print("❌ config.json 不存在")
        if config_example.exists():
            print(f"   请复制 {config_example} 为 {config_file}")
            print(f"   然后编辑填入你的配置")
        return False
    
    try:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查必需字段
        if 'eagle' not in config or 'jellyfin' not in config:
            print("❌ config.json 格式不正确")
            return False
        
        if config['jellyfin'].get('api_key') == 'YOUR_API_KEY_HERE':
            print("⚠️  config.json 中的 API Key 尚未配置")
            return False
        
        print("✅ config.json 已配置")
        return True
        
    except Exception as e:
        print(f"❌ config.json 解析失败: {e}")
        return False

def check_modules():
    """检查项目模块"""
    v2_dir = Path(__file__).parent / 'v2'
    modules = [
        'eagle_reader.py',
        'jellyfin_client.py', 
        'movie_nfo_updater.py',
        'nfo_writer.py',
        'sync_v2_simple.py'
    ]
    
    all_ok = True
    for module in modules:
        if (v2_dir / module).exists():
            print(f"✅ {module}")
        else:
            print(f"❌ {module} 不存在")
            all_ok = False
    
    return all_ok

def main():
    """主函数"""
    print("=" * 60)
    print("EagleTagToJellyfin 环境验证")
    print("=" * 60)
    print()
    
    checks = [
        ("Python 版本", check_python_version),
        ("依赖库", check_dependencies),
        ("配置文件", check_config),
        ("项目模块", check_modules),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n检查 {name}:")
        print("-" * 40)
        results.append(check_func())
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ 所有检查通过！可以开始使用了。")
        print()
        print("快速开始:")
        print("  python main.py sync --dry-run  # 测试运行")
        print("  python main.py sync            # 正式同步")
        return 0
    else:
        print("❌ 部分检查未通过，请先解决上述问题。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
