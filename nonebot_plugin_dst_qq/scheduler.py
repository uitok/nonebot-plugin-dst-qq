"""
定时任务调度器

负责执行定期数据维护任务，包括：
- 自动数据压缩
- 自动数据归档
- 缓存清理
- 系统监控
"""

import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, Optional, Any
from nonebot import require, get_driver
from nonebot import logger
from nonebot import get_bot

# 声明插件依赖
require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler
from .database import chat_history_db, archive_manager
from .cache_manager import cache_manager


class DataMaintenanceScheduler:
    """数据维护调度器"""
    
    def __init__(self):
        self.is_initialized = False
        self.last_maintenance = None
        self.maintenance_stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "total_records_processed": 0,
            "total_space_saved_mb": 0.0
        }
    
    async def init_scheduler(self):
        """初始化定时任务"""
        if self.is_initialized:
            return
        
        try:
            # 每日数据维护任务 - 凌晨2点执行
            scheduler.add_job(
                func=self.daily_maintenance,
                trigger="cron",
                hour=2,
                minute=0,
                id="daily_data_maintenance",
                replace_existing=True
            )
            
            # 每周深度维护任务 - 周日凌晨3点执行
            scheduler.add_job(
                func=self.weekly_maintenance,
                trigger="cron",
                day_of_week=0,  # 周日
                hour=3,
                minute=0,
                id="weekly_data_maintenance",
                replace_existing=True
            )
            
            # 缓存清理任务 - 每6小时执行一次
            scheduler.add_job(
                func=self.cache_maintenance,
                trigger="interval",
                hours=6,
                id="cache_maintenance",
                replace_existing=True
            )
            
            # 系统监控任务 - 每小时检查一次
            scheduler.add_job(
                func=self.system_monitor,
                trigger="interval",
                hours=1,
                id="system_monitor",
                replace_existing=True
            )
            
            self.is_initialized = True
            logger.info("⏰ 数据维护调度器初始化完成")
            logger.info("   📅 每日维护: 凌晨2点")
            logger.info("   📅 每周深度维护: 周日凌晨3点") 
            logger.info("   📅 缓存清理: 每6小时")
            logger.info("   📅 系统监控: 每小时")
            
        except Exception as e:
            logger.error(f"❌ 调度器初始化失败: {e}")
    
    async def daily_maintenance(self):
        """每日维护任务"""
        try:
            logger.info("🌅 开始执行每日数据维护任务...")
            
            # 记录开始时间
            start_time = datetime.now()
            self.maintenance_stats["total_runs"] += 1
            
            # 执行自动压缩
            compress_result = await archive_manager.auto_compress_old_data()
            
            # 如果有超级用户在线，发送通知
            await self._notify_superusers("daily_maintenance", {
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "compress_result": compress_result
            })
            
            # 更新统计
            if compress_result.get("success"):
                self.maintenance_stats["successful_runs"] += 1
                self.maintenance_stats["total_records_processed"] += compress_result.get("total_records_processed", 0)
                self.maintenance_stats["total_space_saved_mb"] += compress_result.get("total_space_saved_mb", 0)
            
            self.last_maintenance = datetime.now()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 每日维护完成，耗时 {processing_time:.1f} 秒")
            
        except Exception as e:
            logger.error(f"❌ 每日维护任务失败: {e}")
    
    async def weekly_maintenance(self):
        """每周深度维护任务"""
        try:
            logger.info("📅 开始执行每周深度维护任务...")
            
            start_time = datetime.now()
            
            # 执行完整维护流程
            maintenance_result = await chat_history_db.auto_maintenance()
            
            # 额外的深度清理
            cache_clear_result = await self._deep_cache_cleanup()
            
            # 发送详细报告
            await self._notify_superusers("weekly_maintenance", {
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "maintenance_result": maintenance_result,
                "cache_result": cache_clear_result,
                "stats": self.maintenance_stats
            })
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 每周维护完成，耗时 {processing_time:.1f} 秒")
            
        except Exception as e:
            logger.error(f"❌ 每周维护任务失败: {e}")
    
    async def cache_maintenance(self):
        """缓存维护任务"""
        try:
            logger.debug("🗄️ 执行缓存维护...")
            
            # 获取缓存统计
            stats_before = cache_manager.get_stats()
            
            # 清理过期文件缓存（但保留内存缓存）
            await cache_manager.cleanup_expired_files()
            
            stats_after = cache_manager.get_stats()
            
            # 如果缓存命中率过低，记录警告
            if stats_after["total_requests"] > 100 and stats_after["hit_rate"] < 0.3:
                logger.warning(f"⚠️ 缓存命中率较低: {stats_after['hit_rate']:.2%}")
            
            logger.debug("✅ 缓存维护完成")
            
        except Exception as e:
            logger.error(f"❌ 缓存维护失败: {e}")
    
    async def system_monitor(self):
        """系统监控任务"""
        try:
            # 检查数据库大小
            db_stats = await chat_history_db.get_database_stats()
            
            # 如果文件大小超过阈值，记录警告
            file_size_mb = db_stats.get("file_size_mb", 0)
            if file_size_mb > 200:
                logger.warning(f"⚠️ 数据库文件较大: {file_size_mb} MB，建议执行维护")
            
            # 检查今日消息量
            messages_24h = db_stats.get("messages_24h", 0)
            if messages_24h > 50000:
                logger.warning(f"⚠️ 24小时内消息量较大: {messages_24h:,} 条")
            
            # 检查缓存状态
            cache_stats = cache_manager.get_stats()
            if cache_stats["memory_cache_size"] > 200:
                logger.info(f"📊 内存缓存使用: {cache_stats['memory_cache_size']}/256")
            
        except Exception as e:
            logger.debug(f"❌ 系统监控失败: {e}")
    
    async def _deep_cache_cleanup(self) -> Dict:
        """深度缓存清理"""
        try:
            # 获取清理前状态
            stats_before = cache_manager.get_stats()
            
            # 清理所有类型的缓存（保留最近的）
            await cache_manager.clear("api")
            await cache_manager.clear("db")
            
            # 等待一小段时间让缓存重新构建核心数据
            await asyncio.sleep(2)
            
            stats_after = cache_manager.get_stats()
            
            return {
                "success": True,
                "cleared_items": stats_before["memory_cache_size"] - stats_after["memory_cache_size"],
                "stats_before": stats_before,
                "stats_after": stats_after
            }
            
        except Exception as e:
            logger.error(f"❌ 深度缓存清理失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _notify_superusers(self, task_type: str, data: dict):
        """通知超级用户维护结果"""
        try:
            bot = get_bot()
            superusers = bot.config.superusers
            
            if not superusers or task_type == "daily_maintenance":
                # 每日维护不发送通知，避免打扰
                return
            
            if task_type == "weekly_maintenance":
                message = self._format_weekly_report(data)
            else:
                message = f"🔧 系统维护通知\n任务: {task_type}\n状态: 完成"
            
            for user_id in superusers:
                try:
                    await bot.send_private_msg(user_id=int(user_id), message=message)
                except Exception:
                    # 发送失败不影响主流程
                    pass
                    
        except Exception as e:
            logger.debug(f"❌ 发送维护通知失败: {e}")
    
    def _format_weekly_report(self, data: dict) -> str:
        """格式化每周报告"""
        maintenance = data.get("maintenance_result", {})
        stats = data.get("stats", self.maintenance_stats)
        
        report = "📊 每周数据维护报告\n\n"
        report += f"🕐 执行时间: {data.get('start_time')}\n\n"
        
        if maintenance.get("success"):
            report += "✅ 维护任务: 成功\n"
            report += f"📝 处理记录: {maintenance.get('total_records_processed', 0):,} 条\n"
            report += f"💰 节省空间: {maintenance.get('total_space_saved_mb', 0):.2f} MB\n\n"
        else:
            report += f"❌ 维护任务: 失败 - {maintenance.get('error', '未知错误')}\n\n"
        
        report += "📈 累计统计:\n"
        report += f"  总执行次数: {stats['total_runs']}\n"
        report += f"  成功次数: {stats['successful_runs']}\n"
        report += f"  成功率: {(stats['successful_runs']/stats['total_runs']*100):.1f}%\n" if stats['total_runs'] > 0 else "  成功率: N/A\n"
        report += f"  累计处理: {stats['total_records_processed']:,} 条\n"
        report += f"  累计节省: {stats['total_space_saved_mb']:.2f} MB"
        
        return report
    
    def get_scheduler_stats(self) -> dict:
        """获取调度器统计"""
        return {
            "is_initialized": self.is_initialized,
            "last_maintenance": self.last_maintenance.isoformat() if self.last_maintenance else None,
            "maintenance_stats": self.maintenance_stats,
            "next_daily_maintenance": self._get_next_run_time("daily_data_maintenance"),
            "next_weekly_maintenance": self._get_next_run_time("weekly_data_maintenance")
        }
    
    def _get_next_run_time(self, job_id: str) -> Optional[str]:
        """获取下次运行时间"""
        try:
            job = scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except:
            pass
        return None


# 创建全局调度器实例
maintenance_scheduler = DataMaintenanceScheduler()


async def init_maintenance_scheduler():
    """初始化维护调度器"""
    await maintenance_scheduler.init_scheduler()


# 导出函数供其他模块使用
__all__ = ["maintenance_scheduler", "init_maintenance_scheduler"]
