#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eagle库标签读取模块
读取Eagle库中的媒体文件和对应的标签信息
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class EagleReader:
    """Eagle库读取器"""
    
    def __init__(self, library_path: str):
        """
        初始化Eagle读取器
        
        Args:
            library_path: Eagle库的根路径
        """
        self.library_path = Path(library_path)
        self.images_path = self.library_path / "images"
        
        if not self.library_path.exists():
            raise FileNotFoundError(f"Eagle库路径不存在: {library_path}")
        
        if not self.images_path.exists():
            raise FileNotFoundError(f"Eagle images路径不存在: {self.images_path}")
    
    def read_all_media_files(self) -> List[Dict]:
        """
        读取所有媒体文件及其标签信息
        
        Returns:
            包含媒体文件信息的字典列表，每个字典包含：
            - file_path: 媒体文件的完整路径
            - file_name: 媒体文件名（不含路径）
            - tags: 标签列表
            - item_name: Eagle中的item名称
        """
        media_items = []
        
        # 遍历所有.info文件夹
        for info_dir in self.images_path.iterdir():
            if not info_dir.is_dir() or not info_dir.name.endswith('.info'):
                continue
            
            # 读取该文件夹中的metadata.json
            metadata_file = info_dir / "metadata.json"
            if not metadata_file.exists():
                logger.warning(f"找不到metadata.json: {metadata_file}")
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # 获取文件信息
                item_name = metadata.get('name', '')
                file_ext = metadata.get('ext', '')
                tags = metadata.get('tags', [])
                
                # 查找实际的媒体文件
                media_file = None
                for file in info_dir.iterdir():
                    if file.is_file() and file.suffix.lower() == f'.{file_ext.lower()}':
                        # 确保不是缩略图
                        if '_thumbnail' not in file.name.lower():
                            media_file = file
                            break
                
                if media_file and media_file.exists():
                    media_items.append({
                        'file_path': str(media_file),
                        'file_name': media_file.name,
                        'tags': tags,
                        'item_name': item_name,
                        'folder_path': str(info_dir)
                    })
                    logger.debug(f"找到媒体文件: {media_file.name}, 标签: {tags}")
                else:
                    logger.warning(f"在 {info_dir.name} 中找不到媒体文件 (ext={file_ext})")
                    
            except json.JSONDecodeError as e:
                logger.error(f"解析metadata.json失败 {metadata_file}: {e}")
            except Exception as e:
                logger.error(f"处理 {info_dir.name} 时出错: {e}")
        
        logger.info(f"共找到 {len(media_items)} 个媒体文件")
        return media_items
    
    def get_media_tags(self, media_path: str) -> List[str]:
        """
        获取指定媒体文件的标签
        
        Args:
            media_path: 媒体文件路径
            
        Returns:
            标签列表
        """
        media_path = Path(media_path)
        if not media_path.exists():
            logger.warning(f"媒体文件不存在: {media_path}")
            return []
        
        # 获取所在的.info文件夹
        info_dir = media_path.parent
        metadata_file = info_dir / "metadata.json"
        
        if not metadata_file.exists():
            logger.warning(f"找不到metadata.json: {metadata_file}")
            return []
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return metadata.get('tags', [])
        except Exception as e:
            logger.error(f"读取标签失败 {metadata_file}: {e}")
            return []
