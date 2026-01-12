// 字幕提取模块
// 使用 Gemini 多模态 API 从视频中提取字幕
// 
// 工作流程:
// 1. 使用 FFmpeg 从视频中提取音频 (MP3 格式)
// 2. 将音频文件编码为 base64
// 3. 发送至 Gemini API 进行转录
// 4. 解析转录结果为 ArticleSegment

use crate::types::{ArticleSegment, TranscriptionResult, TranscriptionSegment};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use chrono::Utc;
use reqwest::Client;
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;
use uuid::Uuid;

// API 端点
const OPENROUTER_API_URL: &str = "https://openrouter.ai/api/v1/chat/completions";
const API_302AI_URL: &str = "https://api.302.ai/v1/chat/completions";
const GOOGLE_GEMINI_URL: &str = "https://generativelanguage.googleapis.com/v1beta/models";

/// 从视频中提取字幕的主函数
/// 
/// # 参数
/// - `app`: Tauri 应用句柄
/// - `video_path`: 视频文件路径
/// - `video_id`: 视频 ID (用于生成 segment ID)
/// - `provider`: API 提供商 ("openrouter", "302ai", "google")
/// - `api_key`: API 密钥
/// - `model`: 模型名称
/// 
/// # 返回
/// - 成功: Vec<ArticleSegment> 字幕段落列表
/// - 失败: 错误信息
pub async fn extract_subtitles(
    app: AppHandle,
    video_path: &Path,
    video_id: &str,
    provider: &str,
    api_key: &str,
    model: &str,
) -> Result<Vec<ArticleSegment>, String> {
    println!("[SubtitleExtraction] 开始提取字幕: {:?}", video_path);
    
    // 1. 从视频中提取音频
    let audio_path = extract_audio_from_video(&app, video_path).await?;
    println!("[SubtitleExtraction] 音频提取完成: {:?}", audio_path);
    
    // 2. 调用 Gemini API 进行转录
    let transcription = transcribe_audio_with_gemini(&audio_path, provider, api_key, model).await?;
    println!("[SubtitleExtraction] 转录完成，共 {} 个片段", transcription.segments.len());
    
    // 3. 转换为 ArticleSegment
    let segments = transcription_to_segments(&transcription, video_id);
    
    // 4. 清理临时音频文件
    if let Err(e) = fs::remove_file(&audio_path) {
        println!("[SubtitleExtraction] 清理临时音频文件失败: {}", e);
    }
    
    Ok(segments)
}

/// 使用 FFmpeg 从视频中提取音频
/// 
/// 输出格式: MP3 (Gemini 支持的格式)
/// 输出位置: 与视频同目录，文件名为 {video_name}_audio.mp3
async fn extract_audio_from_video(app: &AppHandle, video_path: &Path) -> Result<PathBuf, String> {
    let video_dir = video_path.parent()
        .ok_or("无法获取视频目录")?;
    
    let video_stem = video_path.file_stem()
        .and_then(|s| s.to_str())
        .ok_or("无法获取视频文件名")?;
    
    let audio_path = video_dir.join(format!("{}_audio.mp3", video_stem));
    let audio_path_str = audio_path.to_str().ok_or("无效的音频文件路径")?;
    let video_path_str = video_path.to_str().ok_or("无效的视频文件路径")?;
    
    // 检查是否已存在音频文件（之前提取过但未清理）
    if audio_path.exists() {
        if let Err(e) = fs::remove_file(&audio_path) {
            println!("[SubtitleExtraction] 清理旧音频文件失败: {}", e);
        }
    }
    
    // 使用 FFmpeg 提取音频
    // 参数说明:
    // -i: 输入文件
    // -vn: 不处理视频流
    // -acodec libmp3lame: 使用 MP3 编码器
    // -ab 128k: 比特率 128kbps (足够语音识别)
    // -ar 16000: 采样率 16kHz (Gemini 推荐)
    // -ac 1: 单声道 (语音识别足够)
    // -y: 覆盖已存在的文件
    let shell = app.shell();
    
    let output = shell
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}。请确保 sidecar 配置正确。", e))?
        .args([
            "-i", video_path_str,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            audio_path_str,
        ])
        .output()
        .await
        .map_err(|e| format!("FFmpeg 执行失败: {}。请确保已安装 FFmpeg。", e))?;
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("FFmpeg 音频提取失败: {}", stderr));
    }
    
    // 验证音频文件已创建
    if !audio_path.exists() {
        return Err("音频文件未生成".to_string());
    }
    
    Ok(audio_path)
}

/// 使用 Gemini API 转录音频
/// 
/// 支持的 API 提供商:
/// - openrouter: OpenRouter API (使用 input_audio 格式)
/// - 302ai: 302.AI API (兼容 OpenAI 格式)
/// - google: Google Gemini 直接 API
async fn transcribe_audio_with_gemini(
    audio_path: &Path,
    provider: &str,
    api_key: &str,
    model: &str,
) -> Result<TranscriptionResult, String> {
    // 读取并编码音频文件
    let audio_bytes = fs::read(audio_path)
        .map_err(|e| format!("读取音频文件失败: {}", e))?;
    
    let audio_base64 = BASE64.encode(&audio_bytes);
    let audio_size_mb = audio_bytes.len() as f64 / 1024.0 / 1024.0;
    println!("[SubtitleExtraction] 音频文件大小: {:.2} MB", audio_size_mb);
    
    // 检查文件大小 (Gemini 限制约 20MB for inline data)
    if audio_size_mb > 20.0 {
        return Err("音频文件过大 (>20MB)，请尝试更短的视频".to_string());
    }
    
    // 转录提示词 - 强调按句子断句
    let transcription_prompt = r#"请将这段音频转录为文字，并严格按照以下 JSON 格式返回。

要求：
1. **按句子断句**：每个 segment 只包含一个完整的句子，不要将多个句子合并成一段。
2. 句子的划分依据：遇到句号、问号、感叹号等句末标点，或自然的语音停顿时，应断开为新的 segment。
3. 每个句子的长度通常在 5-30 个字左右，不要超过 50 个字。
4. 每个 segment 必须包含 start (开始时间) 和 end (结束时间) 字段，格式为 MM:SS。
5. start 和 end 字段是必须的，不能缺失。
6. 内容保持原文语言，不要翻译。

返回格式示例：
{
  "segments": [
    {
      "start": "00:00",
      "end": "00:03",
      "content": "大家好，欢迎收看今天的节目。",
      "speaker": null
    },
    {
      "start": "00:03",
      "end": "00:06",
      "content": "今天我们来讨论一个重要的话题。",
      "speaker": null
    }
  ],
  "full_text": "完整的转录文本..."
}

注意：每个 segment 只包含一句话，不要合并多个句子！
"#;

    let client = Client::new();
    
    // 根据提供商选择不同的 API 格式
    let response = match provider {
        "google" | "google-ai-studio" => {
            // Google Gemini 直接 API
            let url = format!(
                "{}/{}:generateContent?key={}",
                GOOGLE_GEMINI_URL, model.strip_prefix("models/").unwrap_or(model), api_key
            );
            
            let request_body = json!({
                "contents": [{
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/mp3",
                                "data": audio_base64
                            }
                        },
                        {
                            "text": transcription_prompt
                        }
                    ]
                }],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            });
            
            client
                .post(&url)
                .header("Content-Type", "application/json")
                .json(&request_body)
                .send()
                .await
                .map_err(|e| format!("API 请求失败: {}", e))?
        }
        _ => {
            // OpenRouter / 302.AI (OpenAI 兼容格式)
            let api_url = match provider {
                "openrouter" => OPENROUTER_API_URL,
                "302ai" => API_302AI_URL,
                _ => API_302AI_URL,
            };
            
            // 使用 OpenAI 兼容的 input_audio 格式
            let request_body = json!({
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "mp3"
                            }
                        },
                        {
                            "type": "text",
                            "text": transcription_prompt
                        }
                    ]
                }],
                "temperature": 0.1
            });
            
            client
                .post(api_url)
                .header("Authorization", format!("Bearer {}", api_key))
                .header("Content-Type", "application/json")
                .json(&request_body)
                .send()
                .await
                .map_err(|e| format!("API 请求失败: {}", e))?
        }
    };
    
    if !response.status().is_success() {
        let error_text = response.text().await.unwrap_or_default();
        return Err(format!("API 错误: {}", error_text));
    }
    
    let response_json: Value = response
        .json()
        .await
        .map_err(|e| format!("解析响应失败: {}", e))?;
    
    // 提取响应内容
    let content = if provider == "google" || provider == "google-ai-studio" {
        // Google API 响应格式
        response_json["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .unwrap_or("")
            .to_string()
    } else {
        // OpenAI 兼容格式
        response_json["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or("")
            .to_string()
    };
    
    // 解析转录结果
    parse_transcription_response(&content)
}

/// 解析转录 API 响应
fn parse_transcription_response(content: &str) -> Result<TranscriptionResult, String> {
    // 尝试提取 JSON
    let json_str = extract_json(content);
    
    // 解析 JSON
    let parsed: Value = serde_json::from_str(&json_str)
        .map_err(|e| format!("JSON 解析失败: {}. \n提取的JSON: {}\n原始响应: {}", e, json_str, content))?;
    
    // 提取 segments
    let segments = parsed["segments"]
        .as_array()
        .ok_or("响应中没有 segments 字段")?
        .iter()
        .filter_map(|seg| {
            // 支持 "start"/"end" 或旧格式 "timestamp"
            let start_str = seg["start"].as_str().or(seg["timestamp"].as_str())?;
            let end_str = seg["end"].as_str().unwrap_or(start_str);
            
            let start_time = parse_time_str(start_str);
            let end_time = parse_time_str(end_str);
            
            Some(TranscriptionSegment {
                speaker: seg["speaker"].as_str().map(|s| s.to_string()),
                // timestamp removed as per user request
                content: seg["content"].as_str()?.to_string(),
                start_time: Some(start_time),
                end_time: Some(end_time),
            })
        })
        .collect();
    
    let full_text = parsed["full_text"]
        .as_str()
        .unwrap_or("")
        .to_string();
    
    Ok(TranscriptionResult {
        segments,
        full_text,
    })
}

/// 将 MM:SS 或 HH:MM:SS 格式字符串解析为秒数
fn parse_time_str(time_str: &str) -> f64 {
    let parts: Vec<&str> = time_str.split(':').collect();
    if parts.len() == 2 {
        let min: f64 = parts[0].parse().unwrap_or(0.0);
        let sec: f64 = parts[1].parse().unwrap_or(0.0);
        min * 60.0 + sec
    } else if parts.len() == 3 {
         let h: f64 = parts[0].parse().unwrap_or(0.0);
         let m: f64 = parts[1].parse().unwrap_or(0.0);
         let s: f64 = parts[2].parse().unwrap_or(0.0);
         h * 3600.0 + m * 60.0 + s
    } else {
        0.0
    }
}

/// 从响应中提取 JSON 字符串
fn extract_json(content: &str) -> String {
    // 1. 尝试找 markdown 代码块
    if let Some(start) = content.find("```json") {
        if let Some(end) = content[start..].rfind("```") {
            if end > 7 {
                return content[start+7..start+end].trim().to_string();
            }
        }
    }
    
    // 2. 尝试找通用代码块
    if let Some(start) = content.find("```") {
        if let Some(end_offset) = content[start+3..].find("```") {
            let end = start + 3 + end_offset;
            return content[start+3..end].trim().to_string();
        }
    }
    
    // 3. 尝试找大括号 (Generic find first '{' and last '}')
    if let Some(start) = content.find('{') {
        if let Some(end) = content.rfind('}') {
            if end > start {
                return content[start..=end].to_string();
            }
        }
    }
    
    content.trim().to_string()
}

/// 将转录结果转换为 ArticleSegment
fn transcription_to_segments(
    transcription: &TranscriptionResult,
    article_id: &str,
) -> Vec<ArticleSegment> {
    transcription.segments
        .iter()
        .enumerate()
        .map(|(i, seg)| {
            ArticleSegment {
                id: Uuid::new_v4().to_string(),
                article_id: article_id.to_string(),
                order: i as i32,
                text: seg.content.clone(),
                reading_text: None,
                translation: None,
                explanation: None,
                start_time: seg.start_time,
                end_time: seg.end_time,
                created_at: Utc::now().to_rfc3339(),
                is_new_paragraph: true,
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_extract_json_from_markdown() {
        let content = r#"Here is the transcription:
```json
{"segments": [{"timestamp": "00:00", "content": "Hello"}], "full_text": "Hello"}
```
"#;
        let json = extract_json(content);
        assert!(json.contains("segments"));
    }
    
    #[test]
    fn test_extract_json_plain() {
        let content = r#"{"segments": [{"start": "00:00", "content": "Test"}], "full_text": "Test"}"#;
        let json = extract_json(content);
        assert_eq!(json, content);
    }
    
    #[test]
    fn test_parse_transcription_response() {
        // Test with new format (start/end)
        let content = r#"{"segments": [{"start": "00:00", "end": "00:05", "content": "Hello world", "speaker": null}], "full_text": "Hello world"}"#;
        let result = parse_transcription_response(content).unwrap();
        assert_eq!(result.segments.len(), 1);
        assert_eq!(result.segments[0].content, "Hello world");
        assert_eq!(result.segments[0].start_time, Some(0.0));
        assert_eq!(result.segments[0].end_time, Some(5.0));
    }

    #[test]
    fn test_parse_time_str() {
        assert_eq!(parse_time_str("00:00"), 0.0);
        assert_eq!(parse_time_str("00:05"), 5.0);
        assert_eq!(parse_time_str("01:00"), 60.0);
        assert_eq!(parse_time_str("01:02:03"), 3723.0);
    }
}
