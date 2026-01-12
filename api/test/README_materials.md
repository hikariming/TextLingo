# 文章阅读材料功能测试指南

本文档介绍如何测试新实现的文章阅读材料功能。

## 功能概述

基于您老项目的 MongoDB 端文章阅读模型，我们成功迁移并优化了以下功能：

### 1. 数据模型优化
- **文章库** (`material_libraries`): 管理文章集合
- **文章** (`material_articles`): 可独立存在或属于文章库
- **文章分段** (`material_segments`): 支持语法和词汇解释
- **收藏夹** (`material_collections`): 用户个人收藏管理

### 2. 优化特性
- ✅ 文章可以独立存在，不一定要依赖文章库
- ✅ 文章也可以放在文章库中，便于前端展示和用户使用
- ✅ 支持批量分段创建和自动分段
- ✅ 完整的权限控制（RLS策略）
- ✅ 支持语法和词汇项目的JSON存储

## 测试环境准备

### 1. 安装依赖
```bash
# 安装httpx用于HTTP请求
pip install httpx
```

### 2. 启动API服务
```bash
cd api
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 创建Supabase表
在您的Supabase项目中执行 `doc/material_tables.sql` 中的SQL语句：

```sql
-- 执行 doc/material_tables.sql 中的所有SQL语句
-- 这将创建所有必要的表和RLS策略
```

## 测试方法

### 方法1: Python服务层测试

直接测试服务层逻辑，无需HTTP调用：

```bash
cd api
python test/test_materials.py
```

**测试内容:**
- 用户认证 (使用您的账号: beiming1201@gmail.com)
- 创建文章库
- 获取文章库列表
- 创建文章（属于库的和独立的）
- 获取文章列表
- 创建单个分段
- 批量创建分段
- 获取文章分段列表
- 更新分段

### 方法2: API端点测试

测试完整的HTTP API：

```bash
cd api/test
chmod +x test_materials_api.sh
./test_materials_api.sh
```

**测试内容:**
- 自动登录获取认证令牌
- 完整的CRUD操作测试
- 15个不同的API端点测试
- 自动分段功能测试

## 测试配置

测试使用您提供的账号信息：
- **邮箱**: beiming1201@gmail.com
- **密码**: AAAA123456
- **API地址**: http://localhost:8000/api/v1

## API端点列表

### 文章库管理
- `POST /materials/libraries` - 创建文章库
- `GET /materials/libraries` - 获取文章库列表
- `GET /materials/libraries/{id}` - 获取单个文章库
- `PUT /materials/libraries/{id}` - 更新文章库
- `DELETE /materials/libraries/{id}` - 删除文章库

### 文章管理
- `POST /materials/articles` - 创建文章
- `GET /materials/articles` - 获取文章列表
- `GET /materials/articles/{id}` - 获取单个文章
- `PUT /materials/articles/{id}` - 更新文章
- `DELETE /materials/articles/{id}` - 删除文章

### 分段管理
- `POST /materials/segments` - 创建分段
- `POST /materials/segments/batch` - 批量创建分段
- `GET /materials/articles/{id}/segments` - 获取文章分段
- `PUT /materials/segments/{id}` - 更新分段
- `DELETE /materials/segments/{id}` - 删除分段
- `POST /materials/articles/{id}/auto-segment` - 自动分段

## 数据结构示例

### 文章库创建
```json
{
  "name": "测试文章库",
  "description": "这是一个测试的文章库",
  "library_type": "text",
  "target_language": "zh-CN",
  "explanation_language": "zh-CN",
  "is_public": false
}
```

### 文章创建
```json
{
  "title": "测试文章：日语学习指南",
  "content": "こんにちは。今日は日本語の勉強について話しましょう。",
  "file_type": "text",
  "library_id": "library-uuid-here",
  "target_language": "ja",
  "difficulty_level": "beginner",
  "category": "语言学习",
  "tags": ["日语", "学习", "初级"],
  "is_public": false,
  "description": "这是一篇关于日语学习的测试文章"
}
```

### 分段创建
```json
{
  "article_id": "article-uuid-here",
  "original_text": "こんにちは。今日は日本語の勉強について話しましょう。",
  "translation": "你好。今天我们来谈论日语学习。",
  "reading_text": "こんにちは。きょうは にほんごの べんきょうについて はなしましょう。",
  "is_new_paragraph": true,
  "segment_order": 0,
  "grammar_items": [
    {"name": "について", "explanation": "关于、对于的意思，用来表示话题"},
    {"name": "ましょう", "explanation": "礼貌的邀请或建议形式"}
  ],
  "vocabulary_items": [
    {"word": "今日", "reading": "きょう", "meaning": "今天"},
    {"word": "日本語", "reading": "にほんご", "meaning": "日语"},
    {"word": "勉強", "reading": "べんきょう", "meaning": "学习"}
  ]
}
```

## 权限和安全

- 所有操作都需要用户认证
- 用户只能操作自己的数据
- 支持公开文章的查看
- 使用Supabase RLS进行数据安全控制

## 故障排除

### 常见问题
1. **认证失败**: 确保API服务正常运行，账号密码正确
2. **表不存在**: 确保已在Supabase中执行了建表SQL
3. **权限错误**: 检查RLS策略是否正确设置

### 调试方法
- 查看API日志: `tail -f logs/api.log`
- 检查Supabase表和数据
- 使用Postman或curl手动测试API

## 下一步计划

1. **AI功能集成**: 将文章分段与AI解释功能集成
2. **前端界面**: 开发文章阅读的前端界面
3. **高级功能**: 添加文章收藏、评论、分享等功能
4. **性能优化**: 优化大文章的分段处理

---

## 联系信息

如有问题，请查看API日志或联系开发团队。 