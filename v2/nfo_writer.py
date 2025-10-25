#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO文件生成模块
将Eagle标签写入同名NFO文件，格式符合Jellyfin标准
"""

import os
from pathlib import Path
from typing import List
import logging
from xml.etree import ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)


class NFOWriter:
    """NFO文件写入器"""
    
    @staticmethod
    def create_nfo_content(title: str, tags: List[str], date: str = "") -> str:
        """
        创建NFO文件内容
        
        Args:
            title: 视频标题
            tags: 标签列表
            date: 日期（可选）
            
        Returns:
            格式化的XML字符串
        """
        # 创建根元素
        root = ET.Element('movie')
        
        # 添加标题
        title_elem = ET.SubElement(root, 'title')
        title_elem.text = title
        
        # 添加空的plot
        plot_elem = ET.SubElement(root, 'plot')
        plot_elem.text = ""
        
        # 添加评分
        rating_elem = ET.SubElement(root, 'rating')
        rating_elem.text = "0"
        
        # 添加日期（如果提供）
        if date:
            premiered_elem = ET.SubElement(root, 'premiered')
            premiered_elem.text = date
        
        # 添加标签
        for tag in tags:
            tag_elem = ET.SubElement(root, 'tag')
            tag_elem.text = tag
        
        # 转换为格式化的字符串
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='    ', encoding='UTF-8').decode('utf-8')
        
        # 移除空行
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    @staticmethod
    def write_sidecar_nfo(media_file_path: str, tags: List[str], title: str = None) -> bool:
        """
        写入同名NFO文件（sidecar NFO）
        例如: video.mp4 -> video.mp4.nfo
        
        Args:
            media_file_path: 媒体文件路径
            tags: 标签列表
            title: 标题（可选，默认使用文件名）
            
        Returns:
            是否成功
        """
        media_path = Path(media_file_path)
        
        if not media_path.exists():
            logger.error(f"媒体文件不存在: {media_file_path}")
            return False
        
        # 同名NFO文件路径
        nfo_path = Path(str(media_path) + '.nfo')
        
        # 如果没有提供标题，使用文件名（不含扩展名）
        if title is None:
            title = media_path.stem
        
        try:
            # 创建NFO内容
            nfo_content = NFOWriter.create_nfo_content(title, tags)
            
            # 写入文件
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            
            logger.debug(f"已写入同名NFO: {nfo_path}")
            return True
            
        except Exception as e:
            logger.error(f"写入同名NFO失败 {nfo_path}: {e}")
            return False
    
    @staticmethod
    def write_all_sidecar_nfos(media_items: List[dict]) -> tuple:
        """
        为所有媒体文件写入同名NFO
        
        Args:
            media_items: 媒体文件信息列表（来自EagleReader）
            
        Returns:
            (成功数量, 失败数量)
        """
        success_count = 0
        fail_count = 0
        
        for item in media_items:
            file_path = item['file_path']
            tags = item['tags']
            title = item['item_name']
            
            if NFOWriter.write_sidecar_nfo(file_path, tags, title):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"同名NFO写入完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count, fail_count
    
    @staticmethod
    def delete_movie_nfos(library_path: str) -> int:
        """
        删除指定路径下所有的movie.nfo文件
        
        Args:
            library_path: 库路径
            
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        library_path = Path(library_path)
        
        if not library_path.exists():
            logger.error(f"路径不存在: {library_path}")
            return 0
        
        # 递归查找所有movie.nfo文件
        for nfo_file in library_path.rglob('movie.nfo'):
            try:
                nfo_file.unlink()
                deleted_count += 1
                logger.debug(f"已删除: {nfo_file}")
            except Exception as e:
                logger.error(f"删除movie.nfo失败 {nfo_file}: {e}")
        
        logger.info(f"共删除 {deleted_count} 个movie.nfo文件")
        return deleted_count
