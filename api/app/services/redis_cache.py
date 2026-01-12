"""
Redis 缓存服务 - 高性能分布式缓存

提供基于 Redis 的缓存服务，支持：
- 基本 CRUD 操作
- 批量操作和 Pipeline
- 连接管理和错误处理
- 统计监控和健康检查
- 优雅降级和故障恢复
"""

import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from app.core.config import settings


@dataclass
class CacheStats:
    """缓存统计数据"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_operations: int = 0
    total_response_time: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    @property
    def avg_response_time(self) -> float:
        """平均响应时间（毫秒）"""
        return (self.total_response_time / self.total_operations * 1000) if self.total_operations > 0 else 0.0


@dataclass
class RedisCacheConfig:
    """Redis 缓存配置"""
    redis_url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    connection_pool_size: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    default_ttl: int = 300
    max_connections: int = 50
    key_prefix: str = "api"
    
    @classmethod
    def from_settings(cls) -> 'RedisCacheConfig':
        """从设置创建配置"""
        return cls(
            redis_url=getattr(settings, 'redis_url', None),
            host=getattr(settings, 'redis_host', None),
            port=getattr(settings, 'redis_port', None),
            db=getattr(settings, 'redis_db', 0),
            password=getattr(settings, 'redis_password', None),
            ssl=getattr(settings, 'redis_ssl', False),
            connection_pool_size=getattr(settings, 'redis_connection_pool_size', 10),
            socket_timeout=getattr(settings, 'redis_socket_timeout', 5.0),
            socket_connect_timeout=getattr(settings, 'redis_socket_connect_timeout', 5.0),
            max_connections=getattr(settings, 'redis_max_connections', 50),
            default_ttl=getattr(settings, 'cache_default_ttl', 300),
            key_prefix=getattr(settings, 'cache_key_prefix', 'api')
        )


class RedisCache:
    """Redis 缓存服务类"""
    
    def __init__(self, config: Optional[RedisCacheConfig] = None):
        self.config = config or RedisCacheConfig.from_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self.is_available: bool = False
        self.stats = CacheStats()
        self.logger = logging.getLogger(__name__)
        
        # TTL 策略配置
        self.ttl_strategies = {
            'dashboard': 300,      # 5分钟
            'decks': 600,         # 10分钟
            'cards': 1800,        # 30分钟
            'stats': 300,         # 5分钟
            'collection': 3600,   # 1小时
            'default': self.config.default_ttl
        }
        
        # 延迟初始化，避免在模块导入时创建事件循环
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保 Redis 连接已初始化"""
        if self._initialized:
            return
        
        try:
            # 优先使用 Redis URL
            if self.config.redis_url:
                # 使用Redis URL创建连接池
                self.connection_pool = ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    retry_on_timeout=self.config.retry_on_timeout
                )
            else:
                # 使用传统的host/port方式
                pool_kwargs = {
                    'host': self.config.host or 'localhost',
                    'port': self.config.port or 6379,
                    'db': self.config.db,
                    'password': self.config.password,
                    'max_connections': self.config.max_connections,
                    'socket_timeout': self.config.socket_timeout,
                    'socket_connect_timeout': self.config.socket_connect_timeout,
                    'retry_on_timeout': self.config.retry_on_timeout
                }
                
                # 只有在SSL为True时才添加SSL相关参数
                if self.config.ssl:
                    pool_kwargs['ssl'] = True
                    pool_kwargs['ssl_check_hostname'] = False
                
                # 创建连接池
                self.connection_pool = ConnectionPool(**pool_kwargs)
            
            # 创建 Redis 客户端
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # 测试连接
            await self.redis_client.ping()
            self.is_available = True
            self._initialized = True
            
            if self.config.redis_url:
                self.logger.info(f"Redis cache initialized successfully with URL: {self.config.redis_url[:20]}...")
            else:
                self.logger.info(f"Redis cache initialized successfully - {self.config.host}:{self.config.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connection: {e}")
            self.is_available = False
            self._initialized = False
            await self._handle_error("initialize", e)
    
    def _build_key(self, *parts) -> str:
        """构建标准化的缓存键"""
        # 过滤空值并转换为字符串
        clean_parts = [str(part) for part in parts if part is not None]
        key = f"{self.config.key_prefix}:{':'.join(clean_parts)}"
        return key
    
    def _get_ttl(self, category: str = 'default') -> int:
        """获取指定类别的 TTL"""
        return self.ttl_strategies.get(category, self.ttl_strategies['default'])
    
    async def _handle_error(self, operation: str, error: Exception):
        """处理 Redis 错误"""
        self.stats.errors += 1
        self.stats.last_error = str(error)
        self.stats.last_error_time = datetime.now()
        
        error_trace = traceback.format_exc()
        self.logger.error(f"Redis {operation} error: {error}")
        self.logger.debug(f"Redis error traceback: {error_trace}")
        
        # 根据错误类型决定是否重试连接
        if isinstance(error, (redis.ConnectionError, redis.TimeoutError)):
            self.is_available = False
            self.logger.warning(f"Redis connection lost, will attempt to reconnect")
    
    async def _execute_with_stats(self, operation_name: str, operation_func):
        """执行操作并记录统计信息"""
        # 确保连接已初始化
        await self._ensure_initialized()
        
        if not self.is_available:
            self.stats.misses += 1
            return None
        
        start_time = time.time()
        self.stats.total_operations += 1
        
        try:
            result = await operation_func()
            response_time = time.time() - start_time
            self.stats.total_response_time += response_time
            
            if result is not None:
                self.stats.hits += 1
                self.logger.debug(f"Cache {operation_name} HIT in {response_time*1000:.2f}ms")
            else:
                self.stats.misses += 1
                self.logger.debug(f"Cache {operation_name} MISS in {response_time*1000:.2f}ms")
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            self.stats.total_response_time += response_time
            await self._handle_error(operation_name, e)
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_key = self._build_key(key)
        
        async def _get_operation():
            if not self.redis_client:
                return None
            
            raw_value = await self.redis_client.get(cache_key)
            if raw_value is None:
                return None
            
            try:
                return json.loads(raw_value)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to decode cached value for key {cache_key}: {e}")
                # 删除损坏的缓存项
                await self.redis_client.delete(cache_key)
                return None
        
        return await self._execute_with_stats("get", _get_operation)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, category: str = 'default') -> bool:
        """设置缓存值"""
        await self._ensure_initialized()
        
        if not self.is_available or not self.redis_client:
            return False
        
        cache_key = self._build_key(key)
        ttl_seconds = ttl or self._get_ttl(category)
        
        try:
            # 序列化值
            serialized_value = json.dumps(value, default=str)
            
            # 设置缓存
            result = await self.redis_client.setex(cache_key, ttl_seconds, serialized_value)
            
            self.logger.debug(f"Cache SET: {cache_key} (TTL: {ttl_seconds}s)")
            return bool(result)
            
        except Exception as e:
            await self._handle_error("set", e)
            return False
    
    async def delete(self, key: str) -> bool:
        """删除单个缓存键"""
        await self._ensure_initialized()
        
        if not self.is_available or not self.redis_client:
            return False
        
        cache_key = self._build_key(key)
        
        try:
            result = await self.redis_client.delete(cache_key)
            self.logger.debug(f"Cache DELETE: {cache_key}")
            return result > 0
            
        except Exception as e:
            await self._handle_error("delete", e)
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的缓存键"""
        await self._ensure_initialized()
        
        if not self.is_available or not self.redis_client:
            return 0
        
        cache_pattern = self._build_key(pattern)
        
        try:
            # 获取匹配的键
            keys = await self.redis_client.keys(cache_pattern)
            if not keys:
                return 0
            
            # 批量删除
            result = await self.redis_client.delete(*keys)
            self.logger.debug(f"Cache DELETE_PATTERN: {cache_pattern} ({result} keys deleted)")
            return result
            
        except Exception as e:
            await self._handle_error("delete_pattern", e)
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        if not self.is_available or not self.redis_client:
            return False
        
        cache_key = self._build_key(key)
        
        try:
            result = await self.redis_client.exists(cache_key)
            return result > 0
            
        except Exception as e:
            await self._handle_error("exists", e)
            return False
    
    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """批量获取缓存值"""
        if not self.is_available or not self.redis_client or not keys:
            return [None] * len(keys)
        
        cache_keys = [self._build_key(key) for key in keys]
        
        try:
            raw_values = await self.redis_client.mget(cache_keys)
            results = []
            
            for raw_value in raw_values:
                if raw_value is None:
                    results.append(None)
                else:
                    try:
                        results.append(json.loads(raw_value))
                    except json.JSONDecodeError:
                        results.append(None)
            
            self.logger.debug(f"Cache MGET: {len(keys)} keys, {sum(1 for r in results if r is not None)} hits")
            return results
            
        except Exception as e:
            await self._handle_error("mget", e)
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None, category: str = 'default') -> bool:
        """批量设置缓存值"""
        if not self.is_available or not self.redis_client or not mapping:
            return False
        
        ttl_seconds = ttl or self._get_ttl(category)
        
        try:
            # 使用 pipeline 进行批量操作
            pipe = self.redis_client.pipeline()
            
            for key, value in mapping.items():
                cache_key = self._build_key(key)
                serialized_value = json.dumps(value, default=str)
                pipe.setex(cache_key, ttl_seconds, serialized_value)
            
            results = await pipe.execute()
            success_count = sum(1 for result in results if result)
            
            self.logger.debug(f"Cache MSET: {len(mapping)} keys, {success_count} successful (TTL: {ttl_seconds}s)")
            return success_count == len(mapping)
            
        except Exception as e:
            await self._handle_error("mset", e)
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """递增计数器"""
        if not self.is_available or not self.redis_client:
            return None
        
        cache_key = self._build_key(key)
        
        try:
            # 使用 pipeline 确保原子性
            pipe = self.redis_client.pipeline()
            pipe.incrby(cache_key, amount)
            
            if ttl:
                pipe.expire(cache_key, ttl)
            
            results = await pipe.execute()
            new_value = results[0]
            
            self.logger.debug(f"Cache INCREMENT: {cache_key} by {amount} = {new_value}")
            return new_value
            
        except Exception as e:
            await self._handle_error("increment", e)
            return None
    
    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """获取匹配模式的所有键"""
        if not self.is_available or not self.redis_client:
            return []
        
        cache_pattern = self._build_key(pattern)
        
        try:
            keys = await self.redis_client.keys(cache_pattern)
            # 移除前缀，返回原始键名
            prefix_len = len(f"{self.config.key_prefix}:")
            clean_keys = [key[prefix_len:] for key in keys]
            
            self.logger.debug(f"Cache KEYS: pattern {cache_pattern} matched {len(clean_keys)} keys")
            return clean_keys
            
        except Exception as e:
            await self._handle_error("get_keys_by_pattern", e)
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Redis 健康检查"""
        health_info = {
            "status": "unknown",
            "timestamp": int(time.time()),
            "config": {
                "redis_url": self.config.redis_url[:20] + "..." if self.config.redis_url else None,
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db
            },
            "stats": {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "errors": self.stats.errors,
                "hit_rate": round(self.stats.hit_rate, 2),
                "avg_response_time_ms": round(self.stats.avg_response_time, 2),
                "total_operations": self.stats.total_operations
            }
        }
        
        if not self.is_available or not self.redis_client:
            health_info["status"] = "unavailable"
            health_info["error"] = "Redis client not available"
            return health_info
        
        try:
            # 测试连接
            start_time = time.time()
            await self.redis_client.ping()
            ping_time = time.time() - start_time
            
            # 获取 Redis 信息
            info = await self.redis_client.info()
            
            health_info.update({
                "status": "healthy",
                "ping_time_ms": round(ping_time * 1000, 2),
                "redis_info": {
                    "version": info.get("redis_version"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            })
            
            # 计算 Redis 内部命中率
            redis_hits = info.get("keyspace_hits", 0)
            redis_misses = info.get("keyspace_misses", 0)
            if redis_hits + redis_misses > 0:
                health_info["redis_info"]["hit_rate"] = round(redis_hits / (redis_hits + redis_misses) * 100, 2)
            
        except Exception as e:
            health_info["status"] = "unhealthy"
            health_info["error"] = str(e)
            await self._handle_error("health_check", e)
        
        return health_info
    
    async def clear_all(self) -> bool:
        """清除所有缓存（谨慎使用）"""
        if not self.is_available or not self.redis_client:
            return False
        
        try:
            # 只清除带有我们前缀的键
            pattern = f"{self.config.key_prefix}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                result = await self.redis_client.delete(*keys)
                self.logger.warning(f"Cache CLEAR_ALL: {result} keys deleted")
                return result > 0
            
            return True
            
        except Exception as e:
            await self._handle_error("clear_all", e)
            return False
    
    async def close(self):
        """关闭 Redis 连接"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.connection_pool:
                await self.connection_pool.disconnect()
            
            self.is_available = False
            self.logger.info("Redis cache connection closed")
            
        except Exception as e:
            self.logger.error(f"Error closing Redis connection: {e}")


# 创建全局 Redis 缓存实例
redis_cache = RedisCache()