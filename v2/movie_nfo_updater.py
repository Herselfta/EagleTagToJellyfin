#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO标签更新模块 - 直接修改movie.nfo添加标签
支持标签的增加、删除和修改
"""

import logging
from pathlib import Path
from typing import List, Set, Tuple
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class MovieNFOUpdater:
    """Movie.nfo文件标签更新器"""
    
    @staticmethod
    def get_existing_tags(nfo_path: str) -> Set[str]:
        """
        读取movie.nfo中已有的标签
        
        Args:
            nfo_path: movie.nfo文件路径
            
        Returns:
            标签集合
        """
        nfo_file = Path(nfo_path)
        
        if not nfo_file.exists():
            return set()
        
        try:
            tree = ET.parse(nfo_file)
            root = tree.getroot()
            tags = {tag_elem.text for tag_elem in root.findall('tag') if tag_elem.text}
            return tags
        except Exception as e:
            logger.warning(f"读取现有标签失败 {nfo_path}: {e}")
            return set()
    
    @staticmethod
    def update_movie_nfo_with_tags(nfo_path: str, tags: List[str]) -> bool:
        """
        更新movie.nfo文件，添加或替换标签
        
        Args:
            nfo_path: movie.nfo文件路径
            tags: 要添加的标签列表
            
        Returns:
            是否成功
        """
        nfo_file = Path(nfo_path)
        
        if not nfo_file.exists():
            logger.warning(f"movie.nfo不存在: {nfo_path}")
            return False
        
        try:
            # 解析现有的NFO文件
            tree = ET.parse(nfo_file)
            root = tree.getroot()
            
            # 删除所有现有的标签元素
            for tag_elem in root.findall('tag'):
                root.remove(tag_elem)
            
            # 添加新的标签
            # 找到合适的位置插入标签（通常在title之后）
            title_elem = root.find('title')
            if title_elem is not None:
                insert_pos = list(root).index(title_elem) + 1
            else:
                # 如果没有title元素，插入到plot之后
                plot_elem = root.find('plot')
                if plot_elem is not None:
                    insert_pos = list(root).index(plot_elem) + 1
                else:
                    # 如果都没有，插入到开头
                    insert_pos = 0
            
            # 插入标签元素
            for i, tag in enumerate(tags):
                tag_elem = ET.Element('tag')
                tag_elem.text = tag
                root.insert(insert_pos + i, tag_elem)
            
            # 写回文件
            tree.write(nfo_file, encoding='utf-8', xml_declaration=True)
            logger.debug(f"已更新movie.nfo: {nfo_path}, 添加{len(tags)}个标签")
            return True
            
        except ET.ParseError as e:
            logger.error(f"解析NFO文件失败 {nfo_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"更新movie.nfo失败 {nfo_path}: {e}")
            return False
    
    @staticmethod
    def batch_update_movie_nfos(media_items: List[dict]) -> Tuple[int, int, int, int, bool, List[dict]]:
        """
        批量更新movie.nfo文件
        支持标签的增加、删除和修改
        
        Args:
            media_items: 媒体文件信息列表
            
        Returns:
            (成功数量, 失败数量, 跳过数量, 变更数量, 是否有标签删除, 变更项列表)
        """
        success_count = 0
        fail_count = 0
        skip_count = 0
        changed_count = 0
        has_tag_deletions = False  # 标记是否有任何标签被删除
        changed_items: List[dict] = []  # 记录变更的媒体项（用于后续逐项刷新）
        
        for item in media_items:
            folder_path = Path(item['folder_path'])
            movie_nfo = folder_path / 'movie.nfo'
            current_tags = set(item['tags'])  # Eagle中的当前标签

            # 如果movie.nfo不存在
            if not movie_nfo.exists():
                # 只有有标签时才创建
                if not current_tags:
                    skip_count += 1
                    continue
                    
                try:
                    # 延迟导入以避免循环依赖
                    try:
                        from .nfo_writer import NFOWriter  # type: ignore
                    except Exception:
                        from nfo_writer import NFOWriter  # type: ignore

                    title = item.get('item_name') or Path(item['file_path']).stem
                    base_xml = NFOWriter.create_nfo_content(title=title, tags=list(current_tags))
                    movie_nfo.write_text(base_xml, encoding='utf-8')
                    success_count += 1
                    changed_count += 1
                    changed_items.append({
                        'file_path': item['file_path'],
                        'has_deletion': False
                    })
                    logger.debug(f"已创建movie.nfo并写入{len(current_tags)}个标签: {movie_nfo}")
                    continue
                except Exception as e:
                    logger.error(f"创建movie.nfo失败 {movie_nfo}: {e}")
                    fail_count += 1
                    continue

            # movie.nfo存在：检测标签变更
            existing_tags = MovieNFOUpdater.get_existing_tags(str(movie_nfo))
            
            # 对比标签变化
            added_tags = current_tags - existing_tags
            removed_tags = existing_tags - current_tags
            
            # 如果有标签被删除，设置标志
            if removed_tags:
                has_tag_deletions = True
            
            # 如果没有变化，跳过
            if not added_tags and not removed_tags:
                skip_count += 1
                logger.debug(f"标签无变化，跳过: {item['file_name']}")
                continue
            
            # 记录变更
            if added_tags or removed_tags:
                changed_count += 1
                logger.info(f"检测到标签变更 [{item['file_name']}]: "
                           f"新增{len(added_tags)}个, 删除{len(removed_tags)}个")
                if added_tags:
                    logger.debug(f"  新增: {added_tags}")
                if removed_tags:
                    logger.debug(f"  删除: {removed_tags}")
                changed_items.append({
                    'file_path': item['file_path'],
                    'has_deletion': len(removed_tags) > 0
                })
            
            # 更新NFO（用当前标签完全替换）
            if MovieNFOUpdater.update_movie_nfo_with_tags(str(movie_nfo), list(current_tags)):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"Movie.nfo更新完成: 成功 {success_count}, 失败 {fail_count}, "
                   f"跳过 {skip_count}, 变更 {changed_count}")
        if has_tag_deletions:
            logger.info("本次变更包含标签删除，将对变更条目执行逐项强制刷新（不使用覆盖所有元数据）")
        return success_count, fail_count, skip_count, changed_count, has_tag_deletions, changed_items

