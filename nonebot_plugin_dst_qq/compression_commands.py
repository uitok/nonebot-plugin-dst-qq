"""
数据压缩和归档管理命令

提供完整的数据压缩和归档功能，包括：
- 数据大小分析
- 自动压缩管理
- 归档文件管理
- 压缩统计查看
"""

from nonebot import on_command
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from datetime import datetime, timedelta

from .data_archive_manager import archive_manager


# 数据分析命令
data_analysis_cmd = on_command(
    "数据分析", aliases={"dataanalysis", "数据大小", "数据统计"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 压缩命令
compress_data_cmd = on_command(
    "压缩数据", aliases={"compress", "数据压缩"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 归档命令
archive_data_cmd = on_command(
    "归档数据", aliases={"archive", "数据归档"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 自动压缩命令
auto_compress_cmd = on_command(
    "自动压缩", aliases={"autocompress", "批量压缩"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 自动归档命令
auto_archive_cmd = on_command(
    "自动归档", aliases={"autoarchive", "批量归档"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 压缩统计命令
compression_stats_cmd = on_command(
    "压缩统计", aliases={"compressionstats", "压缩状态"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 清理归档命令
cleanup_archives_cmd = on_command(
    "清理归档", aliases={"cleanuparchives", "归档清理"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 查看归档命令
view_archives_cmd = on_command(
    "查看归档", aliases={"listarchives", "归档列表"}, 
    permission=SUPERUSER, priority=1, block=True
)

# 数据维护命令
data_maintenance_cmd = on_command(
    "数据维护", aliases={"maintenance", "数据整理"}, 
    permission=SUPERUSER, priority=1, block=True
)


@data_analysis_cmd.handle()
async def handle_data_analysis(bot: Bot, event: Event):
    """数据大小和分布分析"""
    try:
        await bot.send(event, "🔍 正在分析数据库大小和分布...")
        
        stats = await archive_manager.analyze_data_size()
        
        if not stats:
            await bot.send(event, "❌ 分析失败，请检查数据库连接")
            return
        
        response = "📊 数据库分析报告\n\n"
        
        # 当前数据统计
        current = stats.get("current_data", {})
        response += "📈 当前数据状态:\n"
        response += f"  📝 总记录数: {current.get('total_records', 0):,}\n"
        response += f"  💾 文件大小: {current.get('file_size_mb', 0)} MB\n"
        response += f"  📁 存储路径: ~/.local/share/nonebot2/data/\n\n"
        
        # 数据分布
        daily_dist = stats.get("daily_distribution", [])[:10]
        if daily_dist:
            response += "📅 最近10天数据分布:\n"
            for item in daily_dist:
                response += f"  {item['date']}: {item['records']:,} 条\n"
            response += "\n"
        
        # 集群分布
        cluster_dist = stats.get("cluster_distribution", [])[:5]
        if cluster_dist:
            response += "🎮 集群数据分布 (前5名):\n"
            for item in cluster_dist:
                response += f"  {item['cluster']}/{item['world']}: {item['records']:,} 条\n"
            response += "\n"
        
        # 压缩机会分析
        compression = stats.get("compression_opportunities", {})
        response += "⚡ 压缩优化分析:\n"
        response += f"  🗜️ 可压缩记录: {compression.get('compressible_records', 0):,} 条\n"
        response += f"  📦 可归档记录: {compression.get('archivable_records', 0):,} 条\n"
        response += f"  💰 预计节省空间: {compression.get('estimated_space_saving_mb', 0)} MB\n\n"
        
        # 已压缩数据
        compressed = stats.get("compressed_data", {})
        if compressed.get("compressed_batches", 0) > 0:
            response += "🗜️ 已压缩数据:\n"
            response += f"  📦 压缩批次: {compressed['compressed_batches']}\n"
            response += f"  📝 压缩记录: {compressed['compressed_records']:,} 条\n"
            response += f"  💾 压缩大小: {compressed['compressed_size_bytes'] / (1024*1024):.2f} MB\n\n"
        
        # 已归档数据
        archived = stats.get("archived_data", {})
        if archived.get("archived_batches", 0) > 0:
            response += "📁 已归档数据:\n"
            response += f"  📦 归档批次: {archived['archived_batches']}\n"
            response += f"  📝 归档记录: {archived['archived_records']:,} 条\n"
            response += f"  💾 归档大小: {archived['archived_size_bytes'] / (1024*1024):.2f} MB\n\n"
        
        # 优化建议
        total_records = current.get('total_records', 0)
        if total_records > 50000:
            response += "💡 优化建议:\n"
            response += "  🔧 建议执行自动压缩以释放空间\n"
            response += "  📦 建议定期归档旧数据\n"
            response += "  ⚙️ 可调整压缩策略以获得更好效果\n"
        elif compression.get('compressible_records', 0) > 1000:
            response += "💡 优化建议:\n"
            response += "  🔧 可以执行数据压缩以节省空间\n"
        else:
            response += "✅ 数据库状态良好，暂无需优化\n"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 数据分析失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@compress_data_cmd.handle()
async def handle_compress_data(bot: Bot, event: Event):
    """手动压缩指定日期数据"""
    try:
        # 获取命令参数
        message_text = str(event.get_message()).strip()
        args = message_text.split()
        
        if len(args) < 2:
            await bot.send(event, "💡 用法: 压缩数据 <日期>\n例如: 压缩数据 2024-01-15")
            return
        
        target_date = args[1]
        
        # 验证日期格式
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            await bot.send(event, "❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return
        
        await bot.send(event, f"🗜️ 正在压缩 {target_date} 的数据...")
        
        result = await archive_manager.compress_daily_data(target_date)
        
        if result["success"]:
            response = f"✅ 数据压缩完成!\n\n"
            response += f"📅 处理日期: {target_date}\n"
            response += f"📝 处理记录: {result['records_processed']:,} 条\n"
            response += f"📦 原始大小: {result['original_size_mb']} MB\n"
            response += f"🗜️ 压缩大小: {result['compressed_size_mb']} MB\n"
            response += f"📊 压缩比例: {result['compression_ratio']:.1%}\n"
            response += f"💰 节省空间: {result['space_saved_mb']} MB\n"
            response += f"⏱️ 处理时间: {result['processing_time_ms']} ms"
        else:
            response = f"❌ 压缩失败: {result['message']}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 数据压缩失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@archive_data_cmd.handle()
async def handle_archive_data(bot: Bot, event: Event):
    """手动归档指定月份数据"""
    try:
        # 获取命令参数
        message_text = str(event.get_message()).strip()
        args = message_text.split()
        
        if len(args) < 2:
            await bot.send(event, "💡 用法: 归档数据 <月份>\n例如: 归档数据 2024-01")
            return
        
        target_month = args[1]
        
        # 验证月份格式
        try:
            datetime.strptime(target_month + "-01", "%Y-%m-%d")
        except ValueError:
            await bot.send(event, "❌ 月份格式错误，请使用 YYYY-MM 格式")
            return
        
        await bot.send(event, f"📦 正在归档 {target_month} 的数据...")
        
        result = await archive_manager.archive_monthly_data(target_month)
        
        if result["success"]:
            response = f"✅ 数据归档完成!\n\n"
            response += f"📅 归档月份: {target_month}\n"
            response += f"📝 归档记录: {result['records_processed']:,} 条\n"
            response += f"📁 创建文件: {result['archive_files_created']} 个\n"
            response += f"💾 文件大小: {result['total_file_size_mb']} MB\n"
            response += f"⏱️ 处理时间: {result['processing_time_ms']} ms\n"
            response += f"📂 存储路径: ~/.local/share/nonebot2/data/.../archives/"
        else:
            response = f"❌ 归档失败: {result['message']}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 数据归档失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@auto_compress_cmd.handle()
async def handle_auto_compress(bot: Bot, event: Event):
    """自动压缩所有旧数据"""
    try:
        await bot.send(event, "🤖 正在执行自动压缩，请稍候...")
        
        result = await archive_manager.auto_compress_old_data()
        
        if result["success"]:
            response = f"✅ 自动压缩完成!\n\n"
            response += f"📅 处理日期: {len(result['dates_processed'])} 天\n"
            response += f"📝 总处理记录: {result['total_records_processed']:,} 条\n"
            response += f"💰 节省空间: {result['total_space_saved_mb']} MB\n\n"
            
            # 显示处理的日期列表（最多显示10个）
            dates_shown = result['dates_processed'][:10]
            if dates_shown:
                response += "📋 处理日期列表:\n"
                for date in dates_shown:
                    response += f"  ✓ {date}\n"
                
                if len(result['dates_processed']) > 10:
                    response += f"  ... 和其他 {len(result['dates_processed']) - 10} 天\n"
            
            if result['total_records_processed'] == 0:
                response = "ℹ️ 没有需要压缩的数据"
        else:
            response = f"❌ 自动压缩失败: {result['message']}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 自动压缩失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@auto_archive_cmd.handle()
async def handle_auto_archive(bot: Bot, event: Event):
    """自动归档所有旧压缩数据"""
    try:
        await bot.send(event, "🤖 正在执行自动归档，请稍候...")
        
        result = await archive_manager.auto_archive_old_compressed_data()
        
        if result["success"]:
            response = f"✅ 自动归档完成!\n\n"
            response += f"📅 处理月份: {len(result['months_processed'])} 个\n"
            response += f"📝 总归档记录: {result['total_records_processed']:,} 条\n"
            response += f"💾 文件总大小: {result['total_file_size_mb']} MB\n\n"
            
            # 显示处理的月份列表
            if result['months_processed']:
                response += "📋 归档月份列表:\n"
                for month in result['months_processed']:
                    response += f"  📦 {month}\n"
            
            if result['total_records_processed'] == 0:
                response = "ℹ️ 没有需要归档的压缩数据"
        else:
            response = f"❌ 自动归档失败: {result['message']}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 自动归档失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@compression_stats_cmd.handle()
async def handle_compression_stats(bot: Bot, event: Event):
    """查看压缩统计信息"""
    try:
        stats = await archive_manager.get_compression_stats()
        
        if not stats:
            await bot.send(event, "❌ 获取统计信息失败")
            return
        
        response = "📈 压缩系统统计报告\n\n"
        
        # 操作统计
        operation_stats = stats.get("operation_statistics", {})
        if operation_stats:
            response += "🔧 操作统计:\n"
            for op_type, op_data in operation_stats.items():
                response += f"  📊 {op_type}:\n"
                response += f"    操作次数: {op_data['operations']}\n"
                response += f"    处理记录: {op_data['total_records']:,} 条\n"
                response += f"    原始大小: {op_data['total_original_size_mb']} MB\n"
                response += f"    压缩大小: {op_data['total_compressed_size_mb']} MB\n"
                response += f"    平均压缩率: {op_data['avg_compression_ratio']:.1%}\n"
                response += f"    平均处理时间: {op_data['avg_processing_time_ms']:.1f} ms\n\n"
        
        # 当前压缩数据
        compressed = stats.get("current_compressed", {})
        response += "🗜️ 当前压缩数据:\n"
        response += f"  📦 压缩批次: {compressed.get('batches', 0)}\n"
        response += f"  📝 压缩记录: {compressed.get('total_records', 0):,} 条\n"
        response += f"  💾 压缩大小: {compressed.get('total_size_mb', 0)} MB\n"
        response += f"  📊 平均压缩率: {compressed.get('avg_compression_ratio', 0):.1%}\n\n"
        
        # 当前归档数据
        archived = stats.get("current_archived", {})
        response += "📁 当前归档数据:\n"
        response += f"  📦 归档文件: {archived.get('files', 0)} 个\n"
        response += f"  📝 归档记录: {archived.get('total_records', 0):,} 条\n"
        response += f"  💾 归档大小: {archived.get('total_size_mb', 0)} MB\n\n"
        
        # 最近活动
        recent = stats.get("recent_activities", [])[:5]
        if recent:
            response += "📋 最近活动 (最近5次):\n"
            for activity in recent:
                response += f"  🕒 {activity['timestamp'][:16]}\n"
                response += f"    操作: {activity['operation']} ({activity['date_processed']})\n"
                response += f"    记录: {activity['records']:,} 条\n"
                response += f"    压缩率: {activity['ratio']:.1%}\n"
                response += f"    耗时: {activity['time_ms']} ms\n\n"
        
        # 配置信息
        config = stats.get("configuration", {})
        response += "⚙️ 当前配置:\n"
        response += f"  🕐 压缩阈值: {config.get('compress_after_days', 7)} 天\n"
        response += f"  📦 归档阈值: {config.get('archive_after_days', 30)} 天\n"
        response += f"  🗑️ 保留压缩数据: {config.get('keep_compressed_days', 90)} 天\n"
        response += f"  🗑️ 保留归档数据: {config.get('keep_archived_days', 365)} 天"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 获取压缩统计失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@cleanup_archives_cmd.handle()
async def handle_cleanup_archives(bot: Bot, event: Event):
    """清理过期归档文件"""
    try:
        await bot.send(event, "🧹 正在清理过期归档文件...")
        
        result = await archive_manager.cleanup_old_archives()
        
        if result["success"]:
            response = f"✅ 归档清理完成!\n\n"
            response += f"🗑️ 删除文件: {len(result['cleaned_files'])} 个\n"
            response += f"💰 释放空间: {result['space_freed_mb']} MB\n\n"
            
            # 显示删除的文件（最多显示10个）
            files_shown = result['cleaned_files'][:10]
            if files_shown:
                response += "📋 已删除文件:\n"
                for file_path in files_shown:
                    file_name = file_path.split('/')[-1]
                    response += f"  🗑️ {file_name}\n"
                
                if len(result['cleaned_files']) > 10:
                    response += f"  ... 和其他 {len(result['cleaned_files']) - 10} 个文件\n"
            
            if len(result['cleaned_files']) == 0:
                response = "ℹ️ 没有需要清理的过期归档文件"
        else:
            response = f"❌ 清理失败: {result['message']}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 清理归档失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@view_archives_cmd.handle()
async def handle_view_archives(bot: Bot, event: Event):
    """查看可用的归档文件列表"""
    try:
        archives_info = await archive_manager.list_archives()
        
        if not archives_info["archives"]:
            await bot.send(event, "📦 当前没有可用的归档文件")
            return
        
        response = f"📦 归档文件列表 (共 {len(archives_info['archives'])} 个):\n\n"
        
        # 按日期排序显示归档
        sorted_archives = sorted(archives_info["archives"], 
                               key=lambda x: x.get("created_date", ""), 
                               reverse=True)
        
        for archive in sorted_archives[:20]:  # 只显示最近20个
            name = archive.get("name", "未知")
            size = archive.get("size_mb", 0)
            date = archive.get("created_date", "未知")
            records = archive.get("records_count", 0)
            
            response += f"📁 {name}\n"
            response += f"   📅 创建时间: {date}\n"
            response += f"   📊 记录数量: {records:,} 条\n"
            response += f"   💾 文件大小: {size:.2f} MB\n\n"
        
        if len(archives_info["archives"]) > 20:
            response += f"... 还有 {len(archives_info['archives']) - 20} 个更早的归档文件\n"
        
        # 添加总统计
        total_size = sum(a.get("size_mb", 0) for a in archives_info["archives"])
        total_records = sum(a.get("records_count", 0) for a in archives_info["archives"])
        
        response += f"\n📊 总统计:\n"
        response += f"💾 总大小: {total_size:.2f} MB\n"
        response += f"📝 总记录: {total_records:,} 条\n"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 查看归档列表失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)


@data_maintenance_cmd.handle()
async def handle_data_maintenance(bot: Bot, event: Event):
    """执行完整的数据维护流程"""
    try:
        await bot.send(event, "🔧 开始执行数据维护流程...\n这可能需要几分钟时间")
        
        maintenance_results = []
        
        # 1. 自动压缩
        await bot.send(event, "1️⃣ 执行自动压缩...")
        compress_result = await archive_manager.auto_compress_old_data()
        maintenance_results.append(("压缩", compress_result))
        
        # 2. 自动归档
        await bot.send(event, "2️⃣ 执行自动归档...")
        archive_result = await archive_manager.auto_archive_old_compressed_data()
        maintenance_results.append(("归档", archive_result))
        
        # 3. 清理过期归档
        await bot.send(event, "3️⃣ 清理过期文件...")
        cleanup_result = await archive_manager.cleanup_old_archives()
        maintenance_results.append(("清理", cleanup_result))
        
        # 汇总结果
        response = "✅ 数据维护完成!\n\n"
        response += "📋 维护结果汇总:\n\n"
        
        total_records = 0
        total_space_saved = 0
        
        for operation, result in maintenance_results:
            if result["success"]:
                response += f"✅ {operation}操作: 成功\n"
                
                if operation == "压缩":
                    records = result.get('total_records_processed', 0)
                    space = result.get('total_space_saved_mb', 0)
                    response += f"  📝 处理记录: {records:,} 条\n"
                    response += f"  💰 节省空间: {space} MB\n"
                    total_records += records
                    total_space_saved += space
                    
                elif operation == "归档":
                    records = result.get('total_records_processed', 0)
                    files = result.get('total_file_size_mb', 0)
                    response += f"  📝 归档记录: {records:,} 条\n"
                    response += f"  💾 文件大小: {files} MB\n"
                    
                elif operation == "清理":
                    files = len(result.get('cleaned_files', []))
                    space = result.get('space_freed_mb', 0)
                    response += f"  🗑️ 删除文件: {files} 个\n"
                    response += f"  💰 释放空间: {space} MB\n"
                    total_space_saved += space
                
                response += "\n"
            else:
                response += f"❌ {operation}操作: 失败 - {result.get('message', '未知错误')}\n\n"
        
        response += f"🎯 维护汇总:\n"
        response += f"  📝 总处理记录: {total_records:,} 条\n"
        response += f"  💰 总节省空间: {total_space_saved:.2f} MB\n"
        
        # 建议下次维护时间
        next_maintenance = datetime.now() + timedelta(days=7)
        response += f"  📅 建议下次维护: {next_maintenance.strftime('%Y-%m-%d')}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 数据维护失败: {str(e)}"
        logger.error(error_msg)
        await bot.send(event, error_msg)
