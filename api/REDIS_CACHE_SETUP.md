# Redis 缓存设置指南

## 概述

API 服务现在使用 Redis 作为分布式缓存，替代了原有的内存缓存。这提供了更好的性能、一致性和可扩展性。

## 环境变量配置

在你的 `.env` 文件中添加以下 Redis 配置：

```bash
# Redis 缓存配置
REDIS_HOST=your-redis-host.com
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=your-redis-password
REDIS_SSL=true  # 如果使用 SSL 连接
REDIS_CONNECTION_POOL_SIZE=10
REDIS_SOCKET_TIMEOUT=5.0
REDIS_SOCKET_CONNECT_TIMEOUT=5.0
REDIS_MAX_CONNECTIONS=50

# 缓存配置
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX=api
```

## 测试 Redis 连接

运行测试脚本验证 Redis 连接：

```bash
cd api
python test_redis_cache.py
```

如果连接成功，你会看到：
```
🚀 开始测试 Redis 缓存...
📊 检查 Redis 连接状态...
✅ Redis 连接成功!
🔧 测试基本缓存操作...
✅ 缓存设置成功
✅ 缓存获取成功
...
🎉 Redis 缓存测试完成!
✅ 所有测试通过!
```

## 缓存策略

### TTL 策略
- **Dashboard**: 5分钟 (300秒)
- **Decks**: 10分钟 (600秒)  
- **Cards**: 30分钟 (1800秒)
- **Stats**: 5分钟 (300秒)
- **Collection**: 1小时 (3600秒)

### 缓存键命名规范
```
flashcards:{category}:{user_id}:{specific_key}

示例:
- flashcards:dashboard:123e4567-e89b-12d3-a456-426614174000
- flashcards:decks:123e4567-e89b-12d3-a456-426614174000:page:1:limit:20
- flashcards:cards:123e4567-e89b-12d3-a456-426614174000:deck:456
```

## API 端点

### 性能监控
```
GET /api/v1/flashcards/performance-metrics
```
返回数据库和 Redis 缓存的性能指标。

### 缓存调试
```
GET /api/v1/flashcards/debug/cache
```
查看当前用户的缓存状态和键信息。

### 清除缓存
```
POST /api/v1/flashcards/debug/cache/clear
```
清除当前用户的所有缓存数据。

## 监控和告警

### 关键指标
- **缓存命中率**: 应该 > 70%
- **Redis 响应时间**: 应该 < 50ms
- **错误率**: 应该 < 1%
- **内存使用**: 监控 Redis 内存使用情况

### 健康检查
系统会自动检查 Redis 连接状态，如果 Redis 不可用，会优雅降级到无缓存模式。

## 故障排查

### 1. 连接失败
如果看到 "Redis 连接失败" 错误：
1. 检查环境变量配置
2. 确认 Redis 服务器可访问
3. 验证认证信息
4. 检查网络连接

### 2. 缓存未命中
如果缓存命中率很低：
1. 检查 TTL 设置是否合理
2. 确认缓存键命名是否正确
3. 查看是否有频繁的缓存清理

### 3. 性能问题
如果响应时间过长：
1. 检查 Redis 服务器性能
2. 调整连接池大小
3. 优化缓存策略

## 代码示例

### 使用缓存服务
```python
from app.services.redis_cache import redis_cache

# 设置缓存
await redis_cache.set("my_key", {"data": "value"}, ttl=300, category="dashboard")

# 获取缓存
data = await redis_cache.get("my_key")

# 批量操作
await redis_cache.mset({"key1": "value1", "key2": "value2"}, ttl=600)
values = await redis_cache.mget(["key1", "key2"])

# 删除模式匹配的键
deleted_count = await redis_cache.delete_pattern("user:123:*")
```

### 在 FlashcardService 中使用
```python
# 获取缓存
cached_data = await self._get_cache(cache_key)
if cached_data:
    return cached_data

# 设置缓存
await self._set_cache(cache_key, data, category='dashboard')

# 清除缓存
await self._clear_cache_pattern(f"user:{user_id}:*")
```

## 迁移说明

### 从内存缓存迁移
1. 原有的内存缓存方法已经更新为异步方法
2. 缓存键命名保持兼容
3. 如果 Redis 不可用，系统会自动降级

### 向后兼容性
- 所有 API 端点保持不变
- 响应格式完全一致
- 性能只会更好，不会变差

## 最佳实践

1. **合理设置 TTL**: 根据数据更新频率设置合适的过期时间
2. **监控缓存命中率**: 定期检查缓存效果
3. **使用批量操作**: 对于多个键的操作，使用 mget/mset
4. **及时清理缓存**: 数据更新时及时清理相关缓存
5. **错误处理**: 始终处理缓存操作可能的异常

## 生产环境建议

1. **Redis 集群**: 使用 Redis 集群提高可用性
2. **监控告警**: 设置 Redis 性能监控和告警
3. **备份策略**: 定期备份 Redis 数据
4. **安全配置**: 使用密码认证和 SSL 连接
5. **资源限制**: 设置合适的内存限制和淘汰策略