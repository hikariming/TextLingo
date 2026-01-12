"""
简单的内存速率限制器
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
import threading

class RateLimiter:
    """基于内存的速率限制器"""
    
    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        检查是否允许请求
        
        Args:
            key: 限制的键（如用户ID）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
            
        Returns:
            (是否允许, 剩余请求数)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        with self._lock:
            # 清理过期的请求记录
            self._requests[key] = [
                req_time for req_time in self._requests[key] 
                if req_time > window_start
            ]
            
            # 检查是否超过限制
            current_requests = len(self._requests[key])
            
            if current_requests >= max_requests:
                return False, 0
            
            # 记录当前请求
            self._requests[key].append(current_time)
            remaining = max_requests - current_requests - 1
            
            return True, remaining
    
    def get_reset_time(self, key: str, window_seconds: int) -> int:
        """获取限制重置时间（Unix时间戳）"""
        with self._lock:
            if not self._requests[key]:
                return int(time.time())
            
            oldest_request = min(self._requests[key])
            reset_time = oldest_request + window_seconds
            return int(reset_time)
    
    def clear_user(self, key: str):
        """清除用户的限制记录"""
        with self._lock:
            if key in self._requests:
                del self._requests[key]

# 全局速率限制器实例
rate_limiter = RateLimiter()