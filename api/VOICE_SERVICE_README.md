# 语音服务 (Voice Service)

基于Minimax API的文本转语音服务，支持多种语言和声音选项。

## 配置

在 `.env` 文件中添加以下配置：

```bash
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_GROUPID=your_minimax_group_id_here
```

## API 接口

### 1. 获取可用声音列表

```
GET /api/v1/voice/voices
```

返回所有可用的声音选项，包括中文、英文和日文声音。

**响应示例：**
```json
{
  "chinese_voices": [
    {
      "id": "Chinese (Mandarin)_Radio_Host",
      "name": "中文广播主持人",
      "language": "zh-CN",
      "gender": "neutral"
    }
  ],
  "english_voices": [...],
  "japanese_voices": [...]
}
```

### 2. 文本转语音 (流式响应)

```
POST /api/v1/voice/text-to-speech
```

将文本转换为语音并返回音频流。

**请求参数：**
```json
{
  "text": "要转换的文本",
  "voice_id": "Chinese (Mandarin)_Radio_Host",
  "speed": 0.8,
  "pitch": 0,
  "volume": 1.0,
  "sample_rate": 32000,
  "bitrate": 128000,
  "audio_format": "mp3"
}
```

**参数说明：**
- `text`: 要转换的文本 (必需，1-5000字符)
- `voice_id`: 声音ID (可选，默认为中文广播主持人)
- `speed`: 语速 (可选，0.1-2.0，默认0.8)
- `pitch`: 音调 (可选，-1.0-1.0，默认0)
- `volume`: 音量 (可选，0.1-2.0，默认1.0)
- `sample_rate`: 采样率 (可选，默认32000)
- `bitrate`: 比特率 (可选，默认128000)
- `audio_format`: 音频格式 (可选，默认mp3)

**响应：**
直接返回音频文件流，MIME类型为 `audio/mpeg`

### 3. 文本转语音 (JSON响应)

```
POST /api/v1/voice/text-to-speech-url
```

将文本转换为语音并返回结果信息。

**请求参数：** 同上

**响应示例：**
```json
{
  "success": true,
  "message": "语音转换成功",
  "audio_url": null
}
```

### 4. 测试语音服务配置

```
GET /api/v1/voice/voices/test
```

检查Minimax API配置是否正确。

**响应示例：**
```json
{
  "success": true,
  "message": "语音服务配置检查完成",
  "details": {
    "has_api_key": true,
    "has_group_id": true,
    "service_url": "https://api.minimax.chat/v1/t2a_v2"
  }
}
```

## 测试

### 1. 服务测试

```bash
cd api
python test_voice_service.py
```

### 2. API测试

```bash
cd api
# 设置认证令牌 (可选)
export API_TOKEN="your_jwt_token_here"
python test_voice_api.py
```

## 使用示例

### cURL 示例

```bash
# 获取声音列表
curl -X GET "http://localhost:8000/api/v1/voice/voices" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 文本转语音
curl -X POST "http://localhost:8000/api/v1/voice/text-to-speech" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是一个测试。",
    "voice_id": "Chinese (Mandarin)_Radio_Host",
    "speed": 0.8
  }' \
  --output test_audio.mp3
```

### Python 示例

```python
import requests

# 配置
base_url = "http://localhost:8000"
token = "your_jwt_token_here"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 文本转语音
response = requests.post(
    f"{base_url}/api/v1/voice/text-to-speech",
    headers=headers,
    json={
        "text": "你好，这是一个测试。",
        "voice_id": "Chinese (Mandarin)_Radio_Host",
        "speed": 0.8
    }
)

if response.status_code == 200:
    with open("output.mp3", "wb") as f:
        f.write(response.content)
    print("音频文件已保存")
```

## 注意事项

1. 所有API都需要JWT认证
2. 文本长度限制为1-5000字符
3. API调用可能会有频率限制，具体取决于Minimax API的配额
4. 请确保正确配置了 `MINIMAX_API_KEY` 和 `MINIMAX_GROUPID`
5. 生成的音频文件为MP3格式，适合在网页和移动应用中播放

## 错误处理

常见错误及解决方案：

1. **401 Unauthorized**: 检查JWT token是否有效
2. **500 Internal Server Error**: 检查Minimax API配置是否正确
3. **语音转换失败**: 检查文本内容和参数是否合法
4. **网络超时**: 检查网络连接和Minimax API服务状态 