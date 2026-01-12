# Dify 通用助手 API 文档

## 概述

Dify 通用助手 API 提供了一个统一的接口来访问多种 AI 模型，支持流式对话、会话管理、文件上传和积分系统。用户可以根据自己的等级选择不同的模型进行对话。

### 基础信息

- **API 版本**: v1
- **基础路径**: `/api/v1/universal-assistant`
- **认证方式**: Bearer Token (JWT)
- **响应格式**: JSON / Server-Sent Events (SSE)

## 认证

所有 API 请求都需要在 Header 中包含有效的 JWT token：

```
Authorization: Bearer <your_jwt_token>
```

## API 端点

### 1. 获取可用模型列表

获取当前用户可以使用的 AI 模型列表。

**请求**
```http
GET /api/v1/universal-assistant/models
Authorization: Bearer <token>
```

**响应**
```json
{
  "models": [
    {
      "id": "glm45",
      "name": "GLM-4.5",
      "input_token_cost": 0.5,
      "output_token_cost": 2.0,
      "base_cost": 3,
      "required_tier": "free",
      "max_tokens": 8192,
      "supports_function_calling": true,
      "rate_limit_per_minute": 20,
      "is_active": true,
      "supported_file_types": ["image", "document"],
      "capabilities": ["文本生成", "代码生成", "分析推理"],
      "description": "智谱最新大模型，平衡性能与成本"
    }
  ]
}
```

### 2. 发起聊天对话

创建新对话或继续现有对话。支持流式响应。

**请求**
```http
POST /api/v1/universal-assistant/chat
Authorization: Bearer <token>
Content-Type: application/json
```

**请求体**
```json
{
  "query": "你好，请介绍一下你自己",
  "model": "glm45",
  "conversation_id": "optional_conversation_id",
  "files": []
}
```

**参数说明**
- `query`: 用户输入的问题或对话内容
- `model`: 选择的模型 ID（必须在可用模型列表中）
- `conversation_id`: 可选，用于继续现有对话
- `files`: 可选，文件 ID 列表

**流式响应 (Server-Sent Events)**

响应格式为 `data: {json}` 的流式数据：

```
data: {"event": "workflow_started", "conversation_id": "xxx", "message_id": "xxx", ...}

data: {"event": "message", "answer": "你好！我是一个AI助手...", "conversation_id": "xxx", "message_id": "xxx"}

data: {"event": "message", "answer": "我可以帮助你...", "conversation_id": "xxx", "message_id": "xxx"}

data: {"event": "message_end", "conversation_id": "xxx", "message_id": "xxx", "metadata": {"usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60, "total_price": "0.001"}}}
```

**事件类型说明**
- `workflow_started`: 工作流开始
- `message`: 消息内容片段
- `message_end`: 消息结束，包含使用统计信息
- `error`: 错误信息

### 3. 获取会话列表

获取当前用户的所有对话会话。

**请求**
```http
GET /api/v1/universal-assistant/conversations?limit=20&offset=0
Authorization: Bearer <token>
```

**参数**
- `limit`: 每页数量，默认 20
- `offset`: 偏移量，默认 0

**响应**
```json
{
  "conversations": [
    {
      "id": "acdbb083-64d5-4380-8be2-56cf9ece9e98",
      "title": "与glm45的对话 07-30 22:23",
      "model": "glm45",
      "created_at": "2025-07-30T22:23:40.048053+00:00",
      "updated_at": "2025-07-30T14:23:47.830255+00:00"
    }
  ]
}
```

### 4. 获取会话消息历史

获取指定会话的消息历史记录。

**请求**
```http
GET /api/v1/universal-assistant/conversations/{conversation_id}/messages?limit=20&offset=0
Authorization: Bearer <token>
```

**参数**
- `conversation_id`: 会话 ID
- `limit`: 每页数量，默认 20
- `offset`: 偏移量，默认 0

**响应**
```json
{
  "messages": [
    {
      "id": "eafeadb7-d79a-401c-af24-fe14add466f7",
      "conversation_id": "acdbb083-64d5-4380-8be2-56cf9ece9e98",
      "role": "user",
      "content": "你好！请简单介绍一下你自己",
      "input_tokens": 0,
      "output_tokens": 0,
      "total_tokens": 0,
      "points_consumed": 0,
      "created_at": "2025-07-30T22:23:41.201858+00:00"
    },
    {
      "id": "bf2d8c43-e1a5-4f6b-9c8d-7f3e2a1b5c9d",
      "conversation_id": "acdbb083-64d5-4380-8be2-56cf9ece9e98",
      "role": "assistant",
      "content": "你好！我是一个AI助手...",
      "input_tokens": 15,
      "output_tokens": 120,
      "total_tokens": 135,
      "points_consumed": 5,
      "created_at": "2025-07-30T22:23:45.501234+00:00"
    }
  ]
}
```

### 5. 删除会话

删除指定的对话会话。

**请求**
```http
DELETE /api/v1/universal-assistant/conversations/{conversation_id}
Authorization: Bearer <token>
```

**响应**
```json
{
  "result": "success"
}
```

### 6. 上传文件到 Dify

上传文件到 Dify 服务，获取文件 ID 用于后续对话。

**请求**
```http
POST /api/v1/universal-assistant/upload-file
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**表单数据**
- `file`: 文件内容
- `user`: 用户 ID

**响应**
```json
{
  "id": "dify_file_id_here",
  "name": "example.png",
  "size": 1024,
  "mime_type": "image/png"
}
```

### 7. 带文件的聊天

支持文件上传的聊天接口。

**请求**
```http
POST /api/v1/universal-assistant/chat-with-files
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**表单数据**
- `query`: 问题内容
- `model`: 模型 ID
- `conversation_id`: 可选，会话 ID
- `files`: 可选，文件

**响应**

与普通聊天接口相同的流式响应格式。

### 8. 获取用户文件列表

获取用户上传的文件列表。

**请求**
```http
GET /api/v1/universal-assistant/files?limit=20&offset=0
Authorization: Bearer <token>
```

**响应**
```json
{
  "files": [
    {
      "id": "file_id_here",
      "dify_file_id": "dify_file_id_here",
      "original_name": "example.png",
      "file_size": 1024,
      "mime_type": "image/png",
      "created_at": "2025-07-30T22:23:41.201858+00:00"
    }
  ]
}
```

### 9. 获取积分交易记录

获取用户的积分消费记录。

**请求**
```http
GET /api/v1/universal-assistant/point-transactions?limit=20&offset=0
Authorization: Bearer <token>
```

**响应**
```json
{
  "transactions": [
    {
      "id": "transaction_id_here",
      "conversation_id": "conversation_id_here",
      "transaction_type": "deduct",
      "points_amount": 5,
      "model_used": "glm45",
      "reason": "聊天消费",
      "created_at": "2025-07-30T22:23:41.201858+00:00"
    }
  ]
}
```

## 支持的模型

| 模型 ID | 模型名称 | 用户等级要求 | 基础积分消费 | 特殊能力 |
|---------|----------|--------------|--------------|----------|
| `glm45` | GLM-4.5 | free | 3 | 文本生成、代码生成 |
| `gemini25pro` | Gemini 2.5 Pro | premium | 8 | 多模态、长文本 |
| `claude4` | Claude 4 | premium | 10 | 高质量文本、推理 |
| `grok4` | Grok-4 | premium | 12 | 实时信息、创意 |
| `gemini25flash` | Gemini 2.5 Flash | free | 2 | 快速响应 |

## 积分系统

### 计费方式

1. **预扣除**: 请求开始时预扣基础积分
2. **后调整**: 根据实际使用量调整积分消费
3. **计算公式**: 
   - 如果 Dify 返回 `total_price`：`积分 = total_price * token_rate_mapping * 1000`
   - 否则：`积分 = input_tokens * input_cost + output_tokens * output_cost`

### 用户等级限制

- **free**: 可使用 glm45、gemini25flash
- **premium**: 可使用所有模型
- **vip**: 可使用所有模型，享受折扣

## 错误处理

### 常见错误码

| HTTP 状态码 | 错误类型 | 说明 |
|-------------|----------|------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 429 | Too Many Requests | 请求频率限制 |
| 500 | Internal Server Error | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 流式响应错误

```
data: {"event": "error", "message": "错误描述"}
```

## 使用示例

### JavaScript 示例

```javascript
// 获取可用模型
async function getModels() {
  const response = await fetch('/api/v1/universal-assistant/models', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// 发起聊天（流式）
async function chat(query, model, conversationId = null) {
  const response = await fetch('/api/v1/universal-assistant/chat', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query,
      model,
      conversation_id: conversationId
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.event === 'message') {
          console.log('收到消息片段:', data.answer);
        } else if (data.event === 'message_end') {
          console.log('对话结束，使用统计:', data.metadata.usage);
        }
      }
    }
  }
}
```

### cURL 示例

```bash
# 获取模型列表
curl -X GET "http://localhost:8000/api/v1/universal-assistant/models" \
  -H "Authorization: Bearer ${TOKEN}"

# 发起聊天
curl -N -X POST "http://localhost:8000/api/v1/universal-assistant/chat" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好，请介绍一下你自己",
    "model": "glm45"
  }'

# 获取会话列表
curl -X GET "http://localhost:8000/api/v1/universal-assistant/conversations" \
  -H "Authorization: Bearer ${TOKEN}"
```

## 注意事项

1. **流式响应**: 聊天接口使用 Server-Sent Events，客户端需要正确处理流式数据
2. **积分消费**: 每次对话都会消费积分，请确保账户有足够余额
3. **会话管理**: 会话 ID 用于维持对话上下文，继续对话时必须提供
4. **文件上传**: 支持的文件类型取决于选择的模型
5. **请求频率**: 不同模型有不同的请求频率限制
6. **Token 过期**: JWT Token 有有效期，过期后需要重新获取

## 版本更新

- **v1.0.0** (2025-07-30): 初始版本发布
  - 支持多模型聊天
  - 流式响应
  - 会话管理
  - 积分系统
  - 文件上传 