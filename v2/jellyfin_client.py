#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jellyfin API客户端模块
处理与Jellyfin服务器的API交互
"""

import requests
import logging
import time
import shutil
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class JellyfinClient:
    """Jellyfin API客户端"""
    
    def __init__(self, server_url: str, api_key: str, library_id: str):
        """
        初始化Jellyfin客户端
        
        Args:
            server_url: Jellyfin服务器URL
            api_key: API密钥
            library_id: 媒体库ID
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.library_id = library_id
        self.headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> bool:
        """
        测试与Jellyfin服务器的连接
        
        Returns:
            连接是否成功
        """
        try:
            url = f"{self.server_url}/System/Info"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                info = response.json()
                logger.info(f"成功连接到Jellyfin服务器: {info.get('ServerName', 'Unknown')}")
                logger.info(f"版本: {info.get('Version', 'Unknown')}")
                return True
            else:
                logger.error(f"连接失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"连接Jellyfin服务器失败: {e}")
            return False
    
    def refresh_library_replace_all_metadata(self) -> bool:
        """
        刷新媒体库 - 覆盖所有元数据
        对应Jellyfin的"Replace All Metadata"选项
        这会让Jellyfin重新读取所有NFO文件并覆盖现有的元数据
        
        Returns:
            是否成功触发刷新
        """
        try:
            # Jellyfin的刷新API
            # ReplaceAllMetadata=true 表示覆盖所有元数据
            url = f"{self.server_url}/Items/{self.library_id}/Refresh"
            params = {
                'Recursive': 'true',
                'MetadataRefreshMode': 'FullRefresh',
                'ImageRefreshMode': 'Default',
                'ReplaceAllMetadata': 'true',
                'ReplaceAllImages': 'false'
            }
            
            logger.info("正在触发Jellyfin刷新: 覆盖所有元数据...")
            response = requests.post(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code in [200, 204]:
                logger.info("成功触发刷新: 覆盖所有元数据")
                return True
            else:
                logger.error(f"刷新失败，状态码: {response.status_code}, 响应: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"触发刷新失败: {e}")
            return False
    
    def refresh_library_search_missing_metadata(self) -> bool:
        """
        刷新媒体库 - 搜索缺少的元数据
        对应Jellyfin的"Search for Missing Metadata"选项
        这会让Jellyfin为没有元数据的项目创建新的元数据文件
        
        Returns:
            是否成功触发刷新
        """
        try:
            # 搜索缺少的元数据
            # ReplaceAllMetadata=false，只为缺少的项目添加元数据
            url = f"{self.server_url}/Items/{self.library_id}/Refresh"
            params = {
                'Recursive': 'true',
                'MetadataRefreshMode': 'Default',
                'ImageRefreshMode': 'Default',
                'ReplaceAllMetadata': 'false',
                'ReplaceAllImages': 'false'
            }
            
            logger.info("正在触发Jellyfin刷新: 搜索缺少的元数据...")
            response = requests.post(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code in [200, 204]:
                logger.info("成功触发刷新: 搜索缺少的元数据")
                return True
            else:
                logger.error(f"刷新失败，状态码: {response.status_code}, 响应: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"触发刷新失败: {e}")
            return False
    
    def wait_for_refresh_complete(self, check_interval: int = 5, max_wait: int = 300, extra_wait: int = 5) -> bool:
        """
        等待刷新任务完成
        
        Args:
            check_interval: 检查间隔（秒）
            max_wait: 最大等待时间（秒）
            extra_wait: 任务队列空闲后的额外等待时间（秒），确保后台操作真正完成
            
        Returns:
            是否在规定时间内完成
        """
        try:
            url = f"{self.server_url}/ScheduledTasks"
            elapsed = 0
            idle_count = 0  # 连续空闲次数
            required_idle_checks = 3  # 需要连续空闲的检查次数
            
            logger.info(f"等待刷新任务完成（最多等待{max_wait}秒）...")
            
            while elapsed < max_wait:
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    tasks = response.json()
                    
                    # 查找刷新任务
                    refresh_tasks = [
                        task for task in tasks
                        if 'Scan' in task.get('Name', '') or 'Refresh' in task.get('Name', '')
                    ]
                    
                    # 检查是否还有运行中的任务
                    running_tasks = [
                        task for task in refresh_tasks
                        if task.get('State') in ['Running', 'Cancelling']
                    ]
                    
                    if not running_tasks:
                        idle_count += 1
                        if idle_count >= required_idle_checks:
                            logger.info(f"刷新任务已完成，额外等待 {extra_wait} 秒确保后台操作完成...")
                            time.sleep(extra_wait)
                            logger.info("✓ 等待完成，NFO文件应该已稳定")
                            return True
                        else:
                            logger.debug(f"任务队列空闲 ({idle_count}/{required_idle_checks})，继续确认...")
                    else:
                        idle_count = 0  # 重置计数
                        logger.debug(f"还有 {len(running_tasks)} 个刷新任务运行中...")
                
                time.sleep(check_interval)
                elapsed += check_interval
            
            logger.warning(f"等待超时（{max_wait}秒），但刷新可能仍在后台进行")
            return False
            
        except Exception as e:
            logger.error(f"检查刷新状态失败: {e}")
            return False
    
    def get_library_info(self) -> Optional[dict]:
        """
        获取媒体库信息
        
        Returns:
            媒体库信息字典，失败返回None
        """
        try:
            url = f"{self.server_url}/Items/{self.library_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取媒体库信息失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取媒体库信息失败: {e}")
            return None

    # === 逐项刷新相关方法（避免破坏性全库覆盖） ===
    def get_item_by_path(self, file_path: str) -> Optional[Dict]:
        """
        通过文件系统路径查找Jellyfin中的媒体项
        """
        try:
            url = f"{self.server_url}/Items/ByPath"
            params = {'Path': file_path}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"按路径查找失败（{resp.status_code}）: {file_path}")
                return None
        except Exception as e:
            logger.error(f"按路径查找出错: {file_path}, {e}")
            return None

    def refresh_item(self, item_id: str, *, replace_all_metadata: bool = False,
                     metadata_refresh_mode: str = 'FullRefresh') -> bool:
        """
        刷新单个媒体项
        注意：replace_all_metadata=False 时会重新解析NFO但不会覆盖手动元数据
        """
        try:
            url = f"{self.server_url}/Items/{item_id}/Refresh"
            params = {
                'Recursive': 'false',
                'MetadataRefreshMode': metadata_refresh_mode,
                'ImageRefreshMode': 'Default',
                'ReplaceAllMetadata': 'true' if replace_all_metadata else 'false',
                'ReplaceAllImages': 'false'
            }
            resp = requests.post(url, headers=self.headers, params=params, timeout=20)
            if resp.status_code in [200, 204]:
                return True
            logger.error(f"刷新单项失败（{resp.status_code}）: {resp.text}")
            return False
        except Exception as e:
            logger.error(f"刷新单项出错: {e}")
            return False

    def refresh_items_by_paths(self, file_paths: List[str], *, per_item_delay: float = 0.25,
                               replace_all_metadata: bool = False,
                               metadata_refresh_mode: str = 'FullRefresh') -> int:
        """
        按路径批量逐项刷新，返回成功数量
        """
        ok = 0
        for p in file_paths:
            item = self.get_item_by_path(p)
            if not item or not item.get('Id'):
                logger.warning(f"未找到媒体项（按路径）: {p}")
                continue
            if self.refresh_item(item['Id'], replace_all_metadata=replace_all_metadata,
                                  metadata_refresh_mode=metadata_refresh_mode):
                ok += 1
            time.sleep(per_item_delay)
        return ok

    def get_metadata_path(self) -> Optional[Path]:
        """
        获取Jellyfin元数据缓存路径
        通过System/Info API获取ProgramDataPath，然后拼接metadata路径
        
        Returns:
            元数据路径，失败返回None
        """
        try:
            url = f"{self.server_url}/System/Info"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                info = response.json()
                program_data = info.get('ProgramDataPath')
                if program_data:
                    metadata_path = Path(program_data) / 'metadata'
                    if metadata_path.exists():
                        logger.info(f"找到Jellyfin元数据路径: {metadata_path}")
                        return metadata_path
                    else:
                        logger.warning(f"元数据路径不存在: {metadata_path}")
                        return None
                else:
                    logger.error("无法从System/Info获取ProgramDataPath")
                    return None
            else:
                logger.error(f"获取系统信息失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取元数据路径失败: {e}")
            return None
    
    def clear_library_metadata_cache(self, backup: bool = True) -> bool:
        """
        清除指定媒体库的元数据缓存
        这将强制Jellyfin重新读取NFO文件，确保标签删除能够同步
        
        Args:
            backup: 是否备份元数据目录
            
        Returns:
            是否成功清除
        """
        try:
            metadata_path = self.get_metadata_path()
            if not metadata_path:
                logger.error("无法获取元数据路径，跳过清除缓存")
                return False
            
            # 查找该媒体库对应的缓存目录
            library_cache = metadata_path / 'library' 
            if not library_cache.exists():
                logger.warning(f"媒体库缓存目录不存在: {library_cache}")
                return False
            
            # 备份（可选）
            if backup:
                backup_path = metadata_path.parent / f'metadata_backup_{int(time.time())}'
                try:
                    shutil.copytree(library_cache, backup_path / 'library')
                    logger.info(f"已备份元数据到: {backup_path}")
                except Exception as e:
                    logger.warning(f"备份元数据失败（继续执行清除）: {e}")
            
            # 清除缓存
            deleted_count = 0
            for item in library_cache.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除缓存项失败 {item}: {e}")
            
            logger.info(f"已清除 {deleted_count} 个元数据缓存项")
            return True
            
        except Exception as e:
            logger.error(f"清除元数据缓存失败: {e}")
            return False
