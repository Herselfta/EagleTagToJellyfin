#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eagle到Jellyfin标签同步 - V2简化版（自动化版本）
直接修改movie.nfo文件添加标签，自动检测标签删除并使用合适的刷新顺序

工作流程:
1. 读取Eagle库中的所有媒体文件和标签
2. 如果检测到标签删除：先让Jellyfin执行ReplaceAllMetadata（重建NFO）
3. 然后写入标签到movie.nfo（覆盖Jellyfin刚重建的NFO）
4. 最后再刷新一次，让Jellyfin读取我们写入的标签
5. 这样就避免了"标签被Jellyfin后续重建NFO时抹掉"的问题

作者: Copilot
日期: 2025-10-25
版本: 2.2（调整刷新顺序）
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
import argparse

# 导入自定义模块
from eagle_reader import EagleReader
from movie_nfo_updater import MovieNFOUpdater
from jellyfin_client import JellyfinClient


def setup_logging(log_file: str = 'sync_v2.log', level: str = 'INFO'):
    """配置日志系统"""
    log_path = Path(__file__).parent / log_file
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def load_config(config_file: str = 'config.json') -> dict:
    """加载配置文件"""
    config_path = Path(__file__).parent / config_file
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def sync_tags_v2(config: dict, logger: logging.Logger, dry_run: bool = False):
    """
    执行标签同步 - V2自动化版本
    自动检测标签删除并选择合适的刷新模式
    
    Args:
        config: 配置字典
        logger: 日志记录器
        dry_run: 是否模拟运行
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("Eagle到Jellyfin标签同步 - V2自动化版")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"模式: {'模拟运行' if dry_run else '正式运行'}")
    logger.info("=" * 60)
    
    try:
        # 步骤1: 读取Eagle库
        logger.info("\n[步骤 1/4] 读取Eagle库...")
        eagle_library = config['eagle']['library_path']
        reader = EagleReader(eagle_library)
        media_items = reader.read_all_media_files()
        
        if not media_items:
            logger.warning("未找到任何媒体文件，同步终止")
            return
        
        logger.info(f"找到 {len(media_items)} 个媒体文件")
        
        # 统计
        items_with_tags = [item for item in media_items if item['tags']]
        total_tags = sum(len(item['tags']) for item in media_items)
        
        logger.info(f"其中 {len(items_with_tags)} 个文件有标签，共 {total_tags} 个标签")
        
        if dry_run:
            logger.info("\n[模拟运行] 有标签的文件示例:")
            for i, item in enumerate(items_with_tags[:5]):
                logger.info(f"  {i+1}. {item['file_name']}: {item['tags']}")
            if len(items_with_tags) > 5:
                logger.info(f"  ... 还有 {len(items_with_tags)-5} 个文件有标签")
            return
        
        # 步骤2: 连接Jellyfin
        logger.info("\n[步骤 2/5] 连接Jellyfin...")
        jellyfin_config = config['jellyfin']
        client = JellyfinClient(
            jellyfin_config['url'],
            jellyfin_config['api_key'],
            jellyfin_config['library_id']
        )
        
        if not client.test_connection():
            logger.error("无法连接到Jellyfin服务器")
            return
        
        # 步骤3: 先让Jellyfin刷新（如果有标签删除，使用ReplaceAllMetadata）
        logger.info("\n[步骤 3/5] 检测是否需要预刷新...")
        
        # 先快速检测是否有标签删除（不实际更新NFO）
        has_deletions = False
        for item in media_items:
            folder_path = Path(item['folder_path'])
            movie_nfo = folder_path / 'movie.nfo'
            if movie_nfo.exists():
                current_tags = set(item['tags'])
                existing_tags = MovieNFOUpdater.get_existing_tags(str(movie_nfo))
                if existing_tags - current_tags:  # 有要删除的标签
                    has_deletions = True
                    break
        
        if has_deletions:
            logger.info("✓ 检测到标签删除，先执行 ReplaceAllMetadata 刷新...")
            logger.info("  （这会让Jellyfin重建NFO，但我们稍后会重新写入标签）")
            if not client.refresh_library_replace_all_metadata():
                logger.error("ReplaceAllMetadata刷新失败")
                return
            logger.info("\n等待预刷新完成（包含额外等待时间确保NFO稳定）...")
            # 等待刷新完成，额外5秒确保NFO真正写入完成
            client.wait_for_refresh_complete(check_interval=10, max_wait=900, extra_wait=5)
            
            # 验证NFO是否真的被重建（检查几个样本）
            logger.info("\n验证NFO是否已重建...")
            sample_items = [item for item in media_items if item.get('tags')][:5]
            nfo_rebuilt_count = 0
            for item in sample_items:
                folder_path = Path(item['folder_path'])
                movie_nfo = folder_path / 'movie.nfo'
                if movie_nfo.exists():
                    existing_tags = MovieNFOUpdater.get_existing_tags(str(movie_nfo))
                    if not existing_tags:  # NFO存在但没有标签，说明被重建了
                        nfo_rebuilt_count += 1
            
            if nfo_rebuilt_count > 0:
                logger.info(f"✓ 验证通过：检查了 {len(sample_items)} 个样本，{nfo_rebuilt_count} 个NFO已被重建（无标签）")
            else:
                logger.warning(f"⚠ 警告：样本NFO中仍有标签，可能刷新未完全完成。继续执行但可能需要二次同步。")
        else:
            logger.info("✓ 无标签删除，跳过预刷新")
        
        # 步骤4: 现在写入标签到movie.nfo
        logger.info("\n[步骤 4/5] 修改movie.nfo文件，写入标签...")
        success, fail, skip, changed, _, _ = MovieNFOUpdater.batch_update_movie_nfos(media_items)
        logger.info(f"Movie.nfo更新完成: 成功 {success} 个, 失败 {fail} 个, "
                   f"跳过 {skip} 个, 变更 {changed} 个")
        
        if success == 0 and changed == 0:
            logger.warning("没有任何文件需要更新，同步终止")
            return
        
        # 步骤5: 最后再刷新一次，让Jellyfin读取我们写入的标签
        logger.info("\n[步骤 5/5] 触发最终刷新，读取标签...")
        if not client.refresh_library_search_missing_metadata():
            logger.warning("标准刷新失败，尝试使用 ReplaceAllMetadata 模式")
            if not client.refresh_library_replace_all_metadata():
                logger.error("刷新失败")
                return
        
        # 等待刷新完成
        logger.info("\n等待最终刷新完成...")
        client.wait_for_refresh_complete(check_interval=5, max_wait=600, extra_wait=3)
        
        # 完成
        elapsed_time = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("✓ 同步完成!")
        logger.info(f"  总耗时: {elapsed_time:.2f} 秒")
        logger.info(f"  成功更新: {success} 个文件")
        logger.info(f"  标签变更: {changed} 个文件")
        logger.info(f"  策略: {'预刷新清除 + 写入标签 + 最终刷新' if has_deletions else '直接写入 + 刷新'}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断同步")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n同步过程中发生错误: {e}", exc_info=True)
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Eagle到Jellyfin标签同步工具 V2 - 自动化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python sync_v2_simple.py              # 标准同步（自动检测标签删除）
  python sync_v2_simple.py --dry-run    # 模拟运行
  python sync_v2_simple.py --log-level DEBUG  # 详细日志

说明:
  V2.2 版本通过调整刷新顺序解决标签持久化问题：
  - 无标签删除：直接写入标签 → 刷新
  - 有标签删除：先刷新（重建NFO）→ 写入标签 → 再刷新
  这样确保标签不会被Jellyfin后续重建NFO时抹掉，完全自动化！
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟运行，不实际修改文件'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别（默认: INFO）'
    )
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging(level=args.log_level)
    
    # 加载配置
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)
    
    # 执行同步
    sync_tags_v2(config, logger, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
