"""
数据归档和压缩管理器

实现聊天历史数据的自动压缩和归档功能，包括：
- 多层级数据归档策略
- 智能压缩算法
- 数据完整性保证
- 快速查询支持
"""

import aiosqlite
import gzip
import json
import pickle
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from nonebot import require
from nonebot.log import logger

# 声明插件依赖
require("nonebot_plugin_localstore")

# 导入 localstore 插件
import nonebot_plugin_localstore as store


class DataArchiveManager:
    """数据归档和压缩管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        # 使用 localstore 获取插件数据目录
        if db_path is None:
            plugin_data_dir = store.get_plugin_data_dir()
            self.db_path = str(plugin_data_dir / "chat_history.db")
            self.archive_dir = plugin_data_dir / "archives"
            self.compressed_dir = plugin_data_dir / "compressed"
        else:
            db_dir = Path(db_path).parent
            self.db_path = db_path
            self.archive_dir = db_dir / "archives"
            self.compressed_dir = db_dir / "compressed"
        
        # 确保目录存在
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.compressed_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置压缩策略
        self.compression_config = {
            # 压缩阈值（天数）
            "archive_after_days": 30,      # 30天后归档
            "compress_after_days": 7,      # 7天后压缩
            
            # 数据量阈值
            "max_daily_records": 10000,    # 单日最大记录数
            "total_size_threshold_mb": 100, # 总大小阈值(MB)
            
            # 压缩比例
            "compression_ratio_target": 0.3,  # 目标压缩比例
            
            # 批处理大小
            "batch_size": 1000,
            
            # 保留策略
            "keep_recent_days": 7,         # 保留最近7天的原始数据
            "keep_compressed_days": 90,    # 保留90天的压缩数据
            "keep_archived_days": 365      # 保留365天的归档数据
        }
        
        self._init_lock = False
    
    async def init_archive_tables(self):
        """初始化归档表结构"""
        if self._init_lock:
            return
        
        self._init_lock = True
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 创建压缩数据表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS compressed_chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date_key TEXT NOT NULL,
                        cluster_name TEXT NOT NULL,
                        world_name TEXT NOT NULL,
                        compressed_data BLOB NOT NULL,
                        original_count INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建归档数据表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS archived_chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        month_key TEXT NOT NULL,
                        cluster_name TEXT NOT NULL,
                        world_name TEXT NOT NULL,
                        archive_file_path TEXT NOT NULL,
                        record_count INTEGER NOT NULL,
                        file_size INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建压缩统计表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS compression_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_type TEXT NOT NULL,
                        date_processed TEXT NOT NULL,
                        records_processed INTEGER NOT NULL,
                        original_size INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        processing_time_ms INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_compressed_date_cluster 
                    ON compressed_chat_history(date_key, cluster_name, world_name)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_archived_month_cluster 
                    ON archived_chat_history(month_key, cluster_name, world_name)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_compression_stats_date 
                    ON compression_stats(date_processed, operation_type)
                ''')
                
                await db.commit()
                
        finally:
            self._init_lock = False
    
    async def analyze_data_size(self) -> Dict[str, Any]:
        """分析数据库大小和数据分布"""
        try:
            await self.init_archive_tables()
            
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # 获取总记录数和文件大小
                cursor = await db.execute('SELECT COUNT(*) FROM chat_history')
                total_records = (await cursor.fetchone())[0]
                
                file_size = 0
                if Path(self.db_path).exists():
                    file_size = Path(self.db_path).stat().st_size
                
                # 按日期分组统计
                cursor = await db.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM chat_history 
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                    LIMIT 30
                ''')
                daily_stats = await cursor.fetchall()
                
                # 按集群/世界分组统计
                cursor = await db.execute('''
                    SELECT cluster_name, world_name, COUNT(*) as count
                    FROM chat_history 
                    GROUP BY cluster_name, world_name
                    ORDER BY count DESC
                ''')
                cluster_stats = await cursor.fetchall()
                
                # 统计可压缩的数据
                cutoff_date = (datetime.now() - timedelta(days=self.compression_config["compress_after_days"])).strftime('%Y-%m-%d')
                cursor = await db.execute('''
                    SELECT COUNT(*) FROM chat_history 
                    WHERE DATE(created_at) < ?
                ''', (cutoff_date,))
                compressible_records = (await cursor.fetchone())[0]
                
                # 统计可归档的数据
                archive_cutoff_date = (datetime.now() - timedelta(days=self.compression_config["archive_after_days"])).strftime('%Y-%m-%d')
                cursor = await db.execute('''
                    SELECT COUNT(*) FROM chat_history 
                    WHERE DATE(created_at) < ?
                ''', (archive_cutoff_date,))
                archivable_records = (await cursor.fetchone())[0]
                
                # 获取已压缩数据统计
                cursor = await db.execute('SELECT COUNT(*), SUM(original_count), SUM(compressed_size) FROM compressed_chat_history')
                compressed_info = await cursor.fetchone()
                
                # 获取已归档数据统计
                cursor = await db.execute('SELECT COUNT(*), SUM(record_count), SUM(file_size) FROM archived_chat_history')
                archived_info = await cursor.fetchone()
                
                stats = {
                    "current_data": {
                        "total_records": total_records,
                        "file_size_bytes": file_size,
                        "file_size_mb": round(file_size / (1024 * 1024), 2)
                    },
                    "daily_distribution": [
                        {"date": row[0], "records": row[1]} for row in daily_stats
                    ],
                    "cluster_distribution": [
                        {"cluster": row[0], "world": row[1], "records": row[2]} for row in cluster_stats
                    ],
                    "compression_opportunities": {
                        "compressible_records": compressible_records,
                        "archivable_records": archivable_records,
                        "estimated_space_saving_mb": round(compressible_records * 0.7 * 200 / (1024 * 1024), 2)  # 估算
                    },
                    "compressed_data": {
                        "compressed_batches": compressed_info[0] or 0,
                        "compressed_records": compressed_info[1] or 0,
                        "compressed_size_bytes": compressed_info[2] or 0
                    },
                    "archived_data": {
                        "archived_batches": archived_info[0] or 0,
                        "archived_records": archived_info[1] or 0,
                        "archived_size_bytes": archived_info[2] or 0
                    }
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ 分析数据大小失败: {e}")
            return {}
    
    async def compress_daily_data(self, target_date: str) -> Dict[str, Any]:
        """压缩指定日期的数据"""
        try:
            start_time = datetime.now()
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取指定日期的数据
                cursor = await db.execute('''
                    SELECT cluster_name, world_name, timestamp, message_type, 
                           player_name, player_id, message_content, raw_message, created_at
                    FROM chat_history 
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at
                ''', (target_date,))
                
                records = await cursor.fetchall()
                
                if not records:
                    return {
                        "success": True,
                        "message": f"没有找到日期 {target_date} 的数据",
                        "records_processed": 0
                    }
                
                # 按集群和世界分组
                grouped_data = {}
                for record in records:
                    cluster_name = record[0]
                    world_name = record[1]
                    key = f"{cluster_name}_{world_name}"
                    
                    if key not in grouped_data:
                        grouped_data[key] = []
                    
                    grouped_data[key].append({
                        "timestamp": record[2],
                        "message_type": record[3],
                        "player_name": record[4],
                        "player_id": record[5],
                        "message_content": record[6],
                        "raw_message": record[7],
                        "created_at": record[8]
                    })
                
                # 逐个压缩每个分组
                total_processed = 0
                total_original_size = 0
                total_compressed_size = 0
                
                for key, group_records in grouped_data.items():
                    cluster_name, world_name = key.split('_', 1)
                    
                    # 序列化数据
                    serialized_data = pickle.dumps(group_records)
                    original_size = len(serialized_data)
                    
                    # 压缩数据（使用zlib获得更好的压缩比）
                    compressed_data = zlib.compress(serialized_data, level=9)
                    compressed_size = len(compressed_data)
                    
                    compression_ratio = compressed_size / original_size if original_size > 0 else 0
                    
                    # 检查是否已存在压缩数据
                    cursor = await db.execute('''
                        SELECT id FROM compressed_chat_history 
                        WHERE date_key = ? AND cluster_name = ? AND world_name = ?
                    ''', (target_date, cluster_name, world_name))
                    
                    existing = await cursor.fetchone()
                    
                    if existing:
                        # 更新现有数据
                        await db.execute('''
                            UPDATE compressed_chat_history 
                            SET compressed_data = ?, original_count = ?, 
                                compressed_size = ?, compression_ratio = ?
                            WHERE id = ?
                        ''', (compressed_data, len(group_records), compressed_size, compression_ratio, existing[0]))
                    else:
                        # 插入新压缩数据
                        await db.execute('''
                            INSERT INTO compressed_chat_history 
                            (date_key, cluster_name, world_name, compressed_data, 
                             original_count, compressed_size, compression_ratio)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (target_date, cluster_name, world_name, compressed_data, 
                              len(group_records), compressed_size, compression_ratio))
                    
                    total_processed += len(group_records)
                    total_original_size += original_size
                    total_compressed_size += compressed_size
                
                # 删除原始数据
                await db.execute('DELETE FROM chat_history WHERE DATE(created_at) = ?', (target_date,))
                
                # 记录压缩统计
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                await db.execute('''
                    INSERT INTO compression_stats 
                    (operation_type, date_processed, records_processed, 
                     original_size, compressed_size, compression_ratio, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('daily_compress', target_date, total_processed, total_original_size, 
                      total_compressed_size, total_compressed_size / total_original_size if total_original_size > 0 else 0,
                      processing_time))
                
                await db.commit()
                
                return {
                    "success": True,
                    "message": f"成功压缩日期 {target_date} 的数据",
                    "records_processed": total_processed,
                    "original_size_mb": round(total_original_size / (1024 * 1024), 2),
                    "compressed_size_mb": round(total_compressed_size / (1024 * 1024), 2),
                    "compression_ratio": round(total_compressed_size / total_original_size if total_original_size > 0 else 0, 3),
                    "space_saved_mb": round((total_original_size - total_compressed_size) / (1024 * 1024), 2),
                    "processing_time_ms": processing_time
                }
                
        except Exception as e:
            logger.error(f"❌ 压缩日期数据失败 {target_date}: {e}")
            return {
                "success": False,
                "message": f"压缩失败: {str(e)}",
                "records_processed": 0
            }
    
    async def archive_monthly_data(self, target_month: str) -> Dict[str, Any]:
        """归档指定月份的压缩数据"""
        try:
            start_time = datetime.now()
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取指定月份的压缩数据
                cursor = await db.execute('''
                    SELECT cluster_name, world_name, compressed_data, original_count
                    FROM compressed_chat_history 
                    WHERE strftime('%Y-%m', date_key) = ?
                    ORDER BY date_key, cluster_name, world_name
                ''', (target_month,))
                
                records = await cursor.fetchall()
                
                if not records:
                    return {
                        "success": True,
                        "message": f"没有找到月份 {target_month} 的压缩数据",
                        "records_processed": 0
                    }
                
                # 按集群和世界分组
                grouped_data = {}
                for record in records:
                    cluster_name = record[0]
                    world_name = record[1]
                    key = f"{cluster_name}_{world_name}"
                    
                    if key not in grouped_data:
                        grouped_data[key] = []
                    
                    # 解压缩数据
                    compressed_data = record[2]
                    decompressed_data = pickle.loads(zlib.decompress(compressed_data))
                    grouped_data[key].extend(decompressed_data)
                
                total_processed = 0
                total_file_size = 0
                
                for key, group_records in grouped_data.items():
                    cluster_name, world_name = key.split('_', 1)
                    
                    # 创建归档文件
                    archive_filename = f"{target_month}_{cluster_name}_{world_name}.json.gz"
                    archive_path = self.archive_dir / archive_filename
                    
                    # 压缩保存到文件
                    with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
                        json.dump(group_records, f, ensure_ascii=False, separators=(',', ':'))
                    
                    file_size = archive_path.stat().st_size
                    
                    # 检查是否已存在归档记录
                    cursor = await db.execute('''
                        SELECT id FROM archived_chat_history 
                        WHERE month_key = ? AND cluster_name = ? AND world_name = ?
                    ''', (target_month, cluster_name, world_name))
                    
                    existing = await cursor.fetchone()
                    
                    if existing:
                        # 更新现有记录
                        await db.execute('''
                            UPDATE archived_chat_history 
                            SET archive_file_path = ?, record_count = ?, file_size = ?
                            WHERE id = ?
                        ''', (str(archive_path), len(group_records), file_size, existing[0]))
                    else:
                        # 插入新归档记录
                        await db.execute('''
                            INSERT INTO archived_chat_history 
                            (month_key, cluster_name, world_name, archive_file_path, 
                             record_count, file_size)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (target_month, cluster_name, world_name, str(archive_path), 
                              len(group_records), file_size))
                    
                    total_processed += len(group_records)
                    total_file_size += file_size
                
                # 删除已归档的压缩数据
                await db.execute('''
                    DELETE FROM compressed_chat_history 
                    WHERE strftime('%Y-%m', date_key) = ?
                ''', (target_month,))
                
                # 记录归档统计
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                await db.execute('''
                    INSERT INTO compression_stats 
                    (operation_type, date_processed, records_processed, 
                     original_size, compressed_size, compression_ratio, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('monthly_archive', target_month, total_processed, 0, 
                      total_file_size, 0, processing_time))
                
                await db.commit()
                
                return {
                    "success": True,
                    "message": f"成功归档月份 {target_month} 的数据",
                    "records_processed": total_processed,
                    "archive_files_created": len(grouped_data),
                    "total_file_size_mb": round(total_file_size / (1024 * 1024), 2),
                    "processing_time_ms": processing_time
                }
                
        except Exception as e:
            logger.error(f"❌ 归档月份数据失败 {target_month}: {e}")
            return {
                "success": False,
                "message": f"归档失败: {str(e)}",
                "records_processed": 0
            }
    
    async def auto_compress_old_data(self) -> Dict[str, Any]:
        """自动压缩旧数据"""
        try:
            await self.init_archive_tables()
            
            # 计算截止日期
            cutoff_date = datetime.now() - timedelta(days=self.compression_config["compress_after_days"])
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取需要压缩的日期列表
                cursor = await db.execute('''
                    SELECT DISTINCT DATE(created_at) as date 
                    FROM chat_history 
                    WHERE DATE(created_at) < ?
                    ORDER BY date
                ''', (cutoff_date.strftime('%Y-%m-%d'),))
                
                dates_to_compress = [row[0] for row in await cursor.fetchall()]
            
            if not dates_to_compress:
                return {
                    "success": True,
                    "message": "没有需要压缩的数据",
                    "dates_processed": []
                }
            
            results = []
            total_records = 0
            total_space_saved = 0
            
            for date in dates_to_compress:
                result = await self.compress_daily_data(date)
                results.append(result)
                
                if result["success"]:
                    total_records += result.get("records_processed", 0)
                    total_space_saved += result.get("space_saved_mb", 0)
            
            return {
                "success": True,
                "message": f"自动压缩完成，处理了 {len(dates_to_compress)} 个日期",
                "dates_processed": dates_to_compress,
                "total_records_processed": total_records,
                "total_space_saved_mb": round(total_space_saved, 2),
                "detailed_results": results
            }
            
        except Exception as e:
            logger.error(f"❌ 自动压缩失败: {e}")
            return {
                "success": False,
                "message": f"自动压缩失败: {str(e)}",
                "dates_processed": []
            }
    
    async def auto_archive_old_compressed_data(self) -> Dict[str, Any]:
        """自动归档旧的压缩数据"""
        try:
            await self.init_archive_tables()
            
            # 计算截止日期
            cutoff_date = datetime.now() - timedelta(days=self.compression_config["archive_after_days"])
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取需要归档的月份列表
                cursor = await db.execute('''
                    SELECT DISTINCT strftime('%Y-%m', date_key) as month_key 
                    FROM compressed_chat_history 
                    WHERE date_key < ?
                    ORDER BY month_key
                ''', (cutoff_date.strftime('%Y-%m-%d'),))
                
                months_to_archive = [row[0] for row in await cursor.fetchall()]
            
            if not months_to_archive:
                return {
                    "success": True,
                    "message": "没有需要归档的压缩数据",
                    "months_processed": []
                }
            
            results = []
            total_records = 0
            total_file_size = 0
            
            for month in months_to_archive:
                result = await self.archive_monthly_data(month)
                results.append(result)
                
                if result["success"]:
                    total_records += result.get("records_processed", 0)
                    total_file_size += result.get("total_file_size_mb", 0)
            
            return {
                "success": True,
                "message": f"自动归档完成，处理了 {len(months_to_archive)} 个月份",
                "months_processed": months_to_archive,
                "total_records_processed": total_records,
                "total_file_size_mb": round(total_file_size, 2),
                "detailed_results": results
            }
            
        except Exception as e:
            logger.error(f"❌ 自动归档失败: {e}")
            return {
                "success": False,
                "message": f"自动归档失败: {str(e)}",
                "months_processed": []
            }
    
    async def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        try:
            await self.init_archive_tables()
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取总体统计
                stats = {}
                
                # 压缩操作统计
                cursor = await db.execute('''
                    SELECT operation_type, COUNT(*) as operations, 
                           SUM(records_processed) as total_records,
                           SUM(original_size) as total_original_size,
                           SUM(compressed_size) as total_compressed_size,
                           AVG(compression_ratio) as avg_compression_ratio,
                           AVG(processing_time_ms) as avg_processing_time
                    FROM compression_stats
                    GROUP BY operation_type
                ''')
                
                operation_stats = {}
                for row in await cursor.fetchall():
                    operation_stats[row[0]] = {
                        "operations": row[1],
                        "total_records": row[2] or 0,
                        "total_original_size_mb": round((row[3] or 0) / (1024 * 1024), 2),
                        "total_compressed_size_mb": round((row[4] or 0) / (1024 * 1024), 2),
                        "avg_compression_ratio": round(row[5] or 0, 3),
                        "avg_processing_time_ms": round(row[6] or 0, 2)
                    }
                
                # 当前压缩数据统计
                cursor = await db.execute('''
                    SELECT COUNT(*) as batches, 
                           SUM(original_count) as total_records,
                           SUM(compressed_size) as total_size,
                           AVG(compression_ratio) as avg_ratio
                    FROM compressed_chat_history
                ''')
                
                compressed_info = await cursor.fetchone()
                
                # 当前归档数据统计
                cursor = await db.execute('''
                    SELECT COUNT(*) as files, 
                           SUM(record_count) as total_records,
                           SUM(file_size) as total_size
                    FROM archived_chat_history
                ''')
                
                archived_info = await cursor.fetchone()
                
                # 最近的压缩活动
                cursor = await db.execute('''
                    SELECT operation_type, date_processed, records_processed,
                           compression_ratio, processing_time_ms, created_at
                    FROM compression_stats
                    ORDER BY created_at DESC
                    LIMIT 10
                ''')
                
                recent_activities = [
                    {
                        "operation": row[0],
                        "date_processed": row[1],
                        "records": row[2],
                        "ratio": round(row[3], 3),
                        "time_ms": row[4],
                        "timestamp": row[5]
                    }
                    for row in await cursor.fetchall()
                ]
                
                stats = {
                    "operation_statistics": operation_stats,
                    "current_compressed": {
                        "batches": compressed_info[0] or 0,
                        "total_records": compressed_info[1] or 0,
                        "total_size_mb": round((compressed_info[2] or 0) / (1024 * 1024), 2),
                        "avg_compression_ratio": round(compressed_info[3] or 0, 3)
                    },
                    "current_archived": {
                        "files": archived_info[0] or 0,
                        "total_records": archived_info[1] or 0,
                        "total_size_mb": round((archived_info[2] or 0) / (1024 * 1024), 2)
                    },
                    "recent_activities": recent_activities,
                    "configuration": self.compression_config
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ 获取压缩统计失败: {e}")
            return {}
    
    async def cleanup_old_archives(self) -> Dict[str, Any]:
        """清理过期的归档文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.compression_config["keep_archived_days"])
            
            cleaned_files = []
            cleaned_size = 0
            
            # 清理归档文件
            for archive_file in self.archive_dir.glob("*.json.gz"):
                if archive_file.stat().st_mtime < cutoff_date.timestamp():
                    file_size = archive_file.stat().st_size
                    archive_file.unlink()
                    cleaned_files.append(str(archive_file))
                    cleaned_size += file_size
            
            # 从数据库中清理记录
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM archived_chat_history 
                    WHERE created_at < ?
                ''', (cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),))
                
                await db.execute('''
                    DELETE FROM compression_stats 
                    WHERE created_at < ?
                ''', (cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),))
                
                await db.commit()
            
            return {
                "success": True,
                "message": f"清理完成，删除了 {len(cleaned_files)} 个归档文件",
                "cleaned_files": cleaned_files,
                "space_freed_mb": round(cleaned_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"❌ 清理归档文件失败: {e}")
            return {
                "success": False,
                "message": f"清理失败: {str(e)}",
                "cleaned_files": []
            }

    async def list_archives(self) -> dict:
        """获取所有可用归档文件的列表"""
        try:
            archives = []
            
            # 从数据库获取归档记录
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT month_key, file_path, record_count, 
                           file_size, created_at
                    FROM archived_chat_history
                    ORDER BY created_at DESC
                ''')
                
                db_archives = await cursor.fetchall()
                
                for row in db_archives:
                    month_key, file_path, record_count, file_size, created_at = row
                    
                    # 检查文件是否存在
                    archive_path = Path(file_path)
                    if archive_path.exists():
                        archives.append({
                            "name": f"archive_{month_key}.json.gz",
                            "month_key": month_key,
                            "file_path": file_path,
                            "records_count": record_count,
                            "size_mb": round(file_size / (1024 * 1024), 2),
                            "created_date": created_at,
                            "type": "archived"
                        })
            
            # 扫描归档目录中的其他文件（防止有文件没在数据库中记录）
            if self.archive_dir.exists():
                for archive_file in self.archive_dir.glob("*.json.gz"):
                    # 检查是否已经在数据库记录中
                    file_path_str = str(archive_file)
                    if not any(a["file_path"] == file_path_str for a in archives):
                        try:
                            stat = archive_file.stat()
                            archives.append({
                                "name": archive_file.name,
                                "month_key": "unknown",
                                "file_path": file_path_str,
                                "records_count": 0,
                                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                                "created_date": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                "type": "file_only"
                            })
                        except Exception as e:
                            logger.warning(f"读取归档文件 {archive_file} 信息失败: {e}")
            
            return {
                "success": True,
                "archives": archives,
                "total_count": len(archives)
            }
            
        except Exception as e:
            logger.error(f"❌ 获取归档列表失败: {e}")
            return {
                "success": False,
                "message": f"获取归档列表失败: {str(e)}",
                "archives": [],
                "total_count": 0
            }


# 创建全局数据归档管理器实例
archive_manager = DataArchiveManager()
