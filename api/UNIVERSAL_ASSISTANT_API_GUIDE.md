# 通用助手 API 使用指南

## 概述

通用助手API提供了一个支持多模型选择的Dify聊天功能，包括文件上传、会话管理、积分计算和权限控制。

## 功能特性

- 🤖 **多模型支持**: 支持 GLM 4.5、Kimi K2、Gemini 2.5 Pro、Claude 4、Grok 4 等多种模型
- 📁 **文件上传**: 支持图片、音频、文档等多种文件类型
- 💬 **会话管理**: 自动保存会话历史和消息记录
- 💰 **积分系统**: 基于模型和实际使用量进行积分计算
- 🔐 **权限控制**: 根据用户会员等级控制模型访问权限
- 📊 **使用统计**: 详细的积分交易记录和使用数据

## API端点

### 基础URL
```
POST /api/v1/universal-assistant
```

### 1. 发送聊天消息

#### 文本聊天
```bash
curl -X POST "http://localhost:8000/api/v1/universal-assistant/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好，请帮我分析这个图片",
    "model": "gemini25pro",
    "conversation_id": null,
    "files": ["file-id-from-upload"]
  }'
```

#### 文件聊天
```bash
curl -X POST "http://localhost:8000/api/v1/universal-assistant/chat-with-files" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "query=请分析这个图片" \
  -F "model=gemini25pro" \
  -F "conversation_id=" \
  -F "files=@image.jpg"
```

### 2. 文件上传

```bash
curl -X POST "http://localhost:8000/api/v1/universal-assistant/upload-file" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf"
```

响应:
```json
{
  "file_id": "80bdb577-6af8-462a-aa8e-2cca11d3592c",
  "filename": "document.pdf",
  "file_size": 1024000,
  "file_type": "document",
  "content_type": "application/pdf"
}
```

### 3. 获取可用模型

```bash
curl -X GET "http://localhost:8000/api/v1/universal-assistant/models" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

响应:
```json
{
  "models": [
    {
      "id": "glm45",
      "name": "GLM 4.5",
      "description": "智谱清言 GLM 4.5，高效的中文对话模型",
      "capabilities": ["text_generation", "conversation", "function_calling"],
      "supported_file_types": [],
      "max_tokens": 128000,
      "required_tier": "free",
      "input_token_cost": 4,
      "output_token_cost": 8,
      "base_cost": 3,
      "available": true
    },
    {
      "id": "gemini25pro",
      "name": "Gemini 2.5 Pro",
      "description": "Google Gemini 2.5 Pro，支持图片和音频多模态交互",
      "capabilities": ["multimodal", "image_analysis", "audio_processing"],
      "supported_file_types": ["image", "audio"],
      "max_tokens": 128000,
      "required_tier": "plus",
      "input_token_cost": 9,
      "output_token_cost": 70,
      "base_cost": 5,
      "available": false
    }
  ]
}
```

### 4. 获取会话列表

```bash
curl -X GET "http://localhost:8000/api/v1/universal-assistant/conversations?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. 获取会话消息

```bash
curl -X GET "http://localhost:8000/api/v1/universal-assistant/conversations/{conversation_id}/messages" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. 获取积分交易记录

```bash
curl -X GET "http://localhost:8000/api/v1/universal-assistant/point-transactions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 模型配置

### 模型等级和权限

| 模型 | 等级要求 | 基础费用 | 输入Token成本 | 输出Token成本 | 特殊能力 |
|------|----------|----------|---------------|---------------|----------|
| GLM 4.5 | free | 3积分 | 4/1k tokens | 8/1k tokens | 函数调用 |
| Kimi K2 | free | 3积分 | 4/1k tokens | 8/1k tokens | 长上下文 |
| Gemini 2.5 Pro | plus | 5积分 | 9/1k tokens | 70/1k tokens | 多模态 |
| Claude 4 | plus | 5积分 | 15/1k tokens | 75/1k tokens | 高级推理 |
| Grok 4 | plus | 5积分 | 15/1k tokens | 75/1k tokens | 创意写作 |

### 支持的文件类型

#### 图片文件
- 支持模型: Gemini 2.5 Pro, Claude 4, Grok 4
- 格式: JPG, JPEG, PNG, GIF, WEBP, BMP, SVG
- 最大大小: 10MB

#### 音频文件
- 支持模型: Gemini 2.5 Pro
- 格式: MP3, WAV, FLAC, AAC, OGG
- 最大大小: 25MB

#### 文档文件
- 支持模型: 所有模型
- 格式: PDF, DOC, DOCX, TXT, MD
- 最大大小: 20MB

## 流式响应格式

聊天API返回Server-Sent Events格式的流式响应：

```
data: {"event": "message", "message_id": "xxx", "conversation_id": "xxx", "answer": "Hello"}

data: {"event": "message", "message_id": "xxx", "conversation_id": "xxx", "answer": " world"}

data: {"event": "message_end", "message_id": "xxx", "conversation_id": "xxx", "metadata": {"usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "total_price": "0.001"}}}
```

### 事件类型

- `message`: 消息内容块
- `message_end`: 消息结束，包含使用统计
- `workflow_started`: 工作流开始
- `workflow_finished`: 工作流结束
- `node_started`: 节点开始执行
- `node_finished`: 节点执行完成
- `error`: 错误事件

## 积分计算

### 计算方式
1. **优先使用实际价格**: 基于Dify返回的 `total_price` 计算
2. **回退到Token计算**: (prompt_tokens × input_cost + completion_tokens × output_cost) / 1000 + base_cost

### 计算示例
```
输入: 519 tokens, 输出: 1600 tokens, 模型: GLM 4.5
计算: (519 × 4 + 1600 × 8) / 1000 + 3 = 17.88 积分
```

## 错误处理

### 常见错误码

- `400`: 请求参数错误
- `401`: 未授权
- `402`: 积分不足
- `403`: 权限不足（会员等级不够）
- `404`: 资源不存在
- `500`: 服务器内部错误
- `502`: Dify API请求错误
- `504`: 请求超时

### 错误响应示例

```json
{
  "detail": "您的会员等级（free）不足，无法使用模型 Gemini 2.5 Pro，需要 plus 等级"
}
```

## 测试示例

### 1. 基础文本对话

```javascript
// 发送文本消息
const response = await fetch('/api/v1/universal-assistant/chat', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: '你好，介绍一下你自己',
    model: 'glm45'
  })
});

// 处理流式响应
const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = new TextDecoder().decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.event === 'message') {
        console.log('收到消息:', data.answer);
      }
    }
  }
}
```

### 2. 图片分析

```bash
# 1. 先上传图片
curl -X POST "http://localhost:8000/api/v1/universal-assistant/upload-file" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@image.jpg"

# 2. 使用文件ID进行对话
curl -X POST "http://localhost:8000/api/v1/universal-assistant/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "请分析这张图片的内容",
    "model": "gemini25pro",
    "files": ["FILE_ID_FROM_UPLOAD"]
  }'
```

### 3. 继续会话

```bash
# 在已有会话中继续对话
curl -X POST "http://localhost:8000/api/v1/universal-assistant/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "请详细解释刚才的回答",
    "model": "glm45",
    "conversation_id": "CONVERSATION_ID_FROM_PREVIOUS_RESPONSE"
  }'
```

## 数据库表结构

### dify_conversations (会话表)
- `id`: 会话ID
- `user_id`: 用户ID
- `flow_id`: 工作流ID
- `dify_conversation_id`: Dify平台会话ID
- `name`: 会话名称
- `selected_model`: 选择的模型
- `is_archived`: 是否归档

### dify_messages (消息表)
- `id`: 消息ID
- `conversation_id`: 会话ID
- `role`: 角色 (user/assistant)
- `content`: 消息内容
- `selected_model`: 使用的模型
- `usage_data`: 使用统计数据

### dify_files (文件表)
- `id`: 文件ID
- `dify_file_id`: Dify文件ID
- `filename`: 文件名
- `file_type`: 文件类型
- `file_size`: 文件大小

### dify_point_transactions (积分交易表)
- `id`: 交易ID
- `user_id`: 用户ID
- `transaction_type`: 交易类型 (deduct/refund/adjustment)
- `points_amount`: 积分数量
- `model_used`: 使用的模型
- `usage_data`: 使用数据

## 注意事项

1. **权限控制**: 确保用户有足够的会员等级使用高级模型
2. **积分管理**: 预扣积分机制，失败时自动退还
3. **文件大小**: 注意各类型文件的大小限制
4. **并发控制**: API有频率限制，注意控制请求频率
5. **错误重试**: 网络错误时建议实现重试机制
6. **会话管理**: 会话ID可用于继续对话，保持上下文

## 配置要求

### 环境变量
- `DIFY_API_URL`: Dify API地址
- `DIFY_API_TOKEN`: Dify API令牌

### 配置文件
确保 `api/app/config/dify_config.json` 包含通用助手配置和支持的模型列表。 