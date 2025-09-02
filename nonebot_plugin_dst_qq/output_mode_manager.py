"""
消息输出模式管理器
管理用户的消息输出模式（文字/图片）
"""

from typing import Dict, Literal
from enum import Enum
import time
from nonebot import logger

class OutputMode(str, Enum):
    """输出模式枚举"""
    TEXT = "text"      # 文字模式
    IMAGE = "image"    # 图片模式

class OutputModeManager:
    """消息输出模式管理器"""
    
    def __init__(self):
        # 用户模式存储 {user_id: mode}
        self._user_modes: Dict[str, OutputMode] = {}
        # 用户设置时间 {user_id: timestamp}
        self._mode_timestamps: Dict[str, float] = {}
        # 默认模式
        self._default_mode = OutputMode.TEXT
        # 模式过期时间（秒），设为0表示不过期
        self._mode_expire_time = 0
        
        logger.success("消息输出模式管理器初始化完成")
    
    def set_user_mode(self, user_id: str, mode: OutputMode) -> bool:
        """
        设置用户的输出模式
        
        Args:
            user_id: 用户ID
            mode: 输出模式
            
        Returns:
            是否设置成功
        """
        try:
            self._user_modes[user_id] = mode
            self._mode_timestamps[user_id] = time.time()
            
            logger.info(
                f"用户 {user_id} 设置输出模式为: {mode.value}",
                category=LogCategory.SYSTEM,
                extra={
                    "user_id": user_id,
                    "mode": mode.value,
                    "timestamp": self._mode_timestamps[user_id]
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                f"设置用户输出模式失败: {e}",
                category=LogCategory.SYSTEM,
                error=e,
                extra={"user_id": user_id, "mode": mode.value if mode else None}
            )
            return False
    
    def get_user_mode(self, user_id: str) -> OutputMode:
        """
        获取用户的输出模式
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户的输出模式
        """
        # 检查用户是否有设置模式
        if user_id not in self._user_modes:
            return self._default_mode
        
        # 检查模式是否过期
        if self._mode_expire_time > 0:
            current_time = time.time()
            set_time = self._mode_timestamps.get(user_id, 0)
            
            if current_time - set_time > self._mode_expire_time:
                # 模式已过期，清除设置
                self._cleanup_user_mode(user_id)
                logger.info(
                    f"用户 {user_id} 的输出模式已过期，重置为默认模式",
                    category=LogCategory.SYSTEM,
                    extra={"user_id": user_id}
                )
                return self._default_mode
        
        return self._user_modes[user_id]
    
    def _cleanup_user_mode(self, user_id: str):
        """清理用户模式设置"""
        self._user_modes.pop(user_id, None)
        self._mode_timestamps.pop(user_id, None)
    
    def reset_user_mode(self, user_id: str) -> bool:
        """
        重置用户模式为默认模式
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否重置成功
        """
        try:
            self._cleanup_user_mode(user_id)
            logger.info(
                f"用户 {user_id} 输出模式已重置为默认模式",
                category=LogCategory.SYSTEM,
                extra={"user_id": user_id}
            )
            return True
            
        except Exception as e:
            logger.error(
                f"重置用户输出模式失败: {e}",
                category=LogCategory.SYSTEM,
                error=e,
                extra={"user_id": user_id}
            )
            return False
    
    def get_mode_info(self, user_id: str) -> Dict[str, any]:
        """
        获取用户模式详细信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            模式详细信息
        """
        current_mode = self.get_user_mode(user_id)
        set_time = self._mode_timestamps.get(user_id)
        
        info = {
            "user_id": user_id,
            "current_mode": current_mode.value,
            "is_default": current_mode == self._default_mode,
            "set_time": set_time,
        }
        
        if set_time:
            info["set_time_readable"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(set_time))
            info["duration"] = time.time() - set_time
        
        return info
    
    def get_all_users_modes(self) -> Dict[str, Dict[str, any]]:
        """
        获取所有用户的模式信息
        
        Returns:
            所有用户的模式信息
        """
        result = {}
        for user_id in self._user_modes:
            result[user_id] = self.get_mode_info(user_id)
        
        return result
    
    def cleanup_expired_modes(self) -> int:
        """
        清理过期的模式设置
        
        Returns:
            清理的数量
        """
        if self._mode_expire_time <= 0:
            return 0
        
        current_time = time.time()
        expired_users = []
        
        for user_id, set_time in self._mode_timestamps.items():
            if current_time - set_time > self._mode_expire_time:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self._cleanup_user_mode(user_id)
        
        if expired_users:
            logger.info(
                f"清理了 {len(expired_users)} 个过期的输出模式设置",
                category=LogCategory.SYSTEM,
                extra={"expired_count": len(expired_users), "expired_users": expired_users}
            )
        
        return len(expired_users)
    
    def set_default_mode(self, mode: OutputMode):
        """设置默认模式"""
        self._default_mode = mode
        logger.info(
            f"默认输出模式设置为: {mode.value}",
            category=LogCategory.SYSTEM,
            extra={"default_mode": mode.value}
        )
    
    def set_expire_time(self, seconds: int):
        """
        设置模式过期时间
        
        Args:
            seconds: 过期时间（秒），0表示不过期
        """
        self._mode_expire_time = seconds
        logger.info(
            f"输出模式过期时间设置为: {seconds}秒",
            category=LogCategory.SYSTEM,
            extra={"expire_time": seconds}
        )
    
    def get_stats(self) -> Dict[str, any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        text_users = sum(1 for mode in self._user_modes.values() if mode == OutputMode.TEXT)
        image_users = sum(1 for mode in self._user_modes.values() if mode == OutputMode.IMAGE)
        
        return {
            "total_users": len(self._user_modes),
            "text_mode_users": text_users,
            "image_mode_users": image_users,
            "default_mode": self._default_mode.value,
            "expire_time": self._mode_expire_time
        }


# 全局输出模式管理器实例 - 立即创建确保单例
_output_mode_manager: OutputModeManager = OutputModeManager()

def get_output_mode_manager() -> OutputModeManager:
    """获取输出模式管理器实例（单例模式）"""
    global _output_mode_manager
    return _output_mode_manager