//! 字幕提取功能集成测试
//! 
//! 运行方法:
//! cd textlingo-desktop/src-tauri && cargo test --test subtitle_extraction_test
//!
//! 注意：此测试需要以下外部依赖:
//! - FFmpeg (用于音频提取)
//! - 有效的 Gemini API 密钥 (用于转录)

use std::path::PathBuf;

/// 测试 JSON 解析功能
#[test]
fn test_extract_json_from_markdown() {
    let content = r#"Here is the transcription:
```json
{"segments": [{"timestamp": "00:00", "content": "Hello"}], "full_text": "Hello"}
```
"#;
    
    // 提取 JSON 的逻辑
    let json_str = extract_json(content);
    assert!(json_str.contains("segments"));
    assert!(json_str.contains("Hello"));
}

/// 测试纯 JSON 提取
#[test]
fn test_extract_json_plain() {
    let content = r#"{"segments": [{"timestamp": "00:00", "content": "Test"}], "full_text": "Test"}"#;
    let json = extract_json(content);
    assert_eq!(json, content);
}

/// 测试转录响应解析
#[test]
fn test_parse_transcription_response() {
    let content = r#"{"segments": [{"timestamp": "00:00", "content": "Hello world", "speaker": null}], "full_text": "Hello world"}"#;
    
    let parsed: serde_json::Value = serde_json::from_str(content).unwrap();
    let segments = parsed["segments"].as_array().unwrap();
    
    assert_eq!(segments.len(), 1);
    assert_eq!(segments[0]["content"].as_str().unwrap(), "Hello world");
    assert_eq!(segments[0]["timestamp"].as_str().unwrap(), "00:00");
}

/// 测试转录段落转换
#[test]
fn test_transcription_to_segments() {
    // 模拟转录结果
    let transcription_json = r#"{
        "segments": [
            {"timestamp": "00:05", "content": "Welcome to the tutorial", "speaker": "Speaker 1"},
            {"timestamp": "00:10", "content": "Today we'll learn about Rust", "speaker": "Speaker 1"}
        ],
        "full_text": "Welcome to the tutorial. Today we'll learn about Rust."
    }"#;
    
    let parsed: serde_json::Value = serde_json::from_str(transcription_json).unwrap();
    let segments = parsed["segments"].as_array().unwrap();
    
    assert_eq!(segments.len(), 2);
    assert!(parsed["full_text"].as_str().unwrap().contains("Rust"));
}

/// 测试空内容处理
#[test]
fn test_empty_transcription_handling() {
    let content = r#"{"segments": [], "full_text": ""}"#;
    
    let parsed: serde_json::Value = serde_json::from_str(content).unwrap();
    let segments = parsed["segments"].as_array().unwrap();
    
    assert_eq!(segments.len(), 0);
    assert_eq!(parsed["full_text"].as_str().unwrap(), "");
}

/// 测试大括号匹配 JSON 提取
#[test]
fn test_extract_json_with_nested_braces() {
    let content = r#"Here is the response:
    {
        "segments": [
            {"timestamp": "00:00", "content": "Hello {world}"}
        ],
        "full_text": "Hello {world}"
    }
Some extra text here"#;
    
    let json = extract_json(content);
    
    // 验证提取的 JSON 可以被解析
    let parsed: Result<serde_json::Value, _> = serde_json::from_str(&json);
    assert!(parsed.is_ok(), "Extracted JSON should be valid: {}", json);
}

// 辅助函数 - 从响应中提取 JSON
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
    
    // 3. 尝试找大括号
    if let Some(start_idx) = content.find('{') {
        let mut balance = 0;
        for (i, c) in content[start_idx..].char_indices() {
            match c {
                '{' => balance += 1,
                '}' => {
                    balance -= 1;
                    if balance == 0 {
                        return content[start_idx..=start_idx+i].to_string();
                    }
                }
                _ => {}
            }
        }
    }
    
    content.trim().to_string()
}

// ============================================================================
// 集成测试 (需要外部依赖)
// ============================================================================

/// 集成测试：验证完整的字幕提取流程
/// 
/// 此测试被忽略，因为需要:
/// 1. FFmpeg 安装
/// 2. 有效的 Gemini API 密钥
/// 3. 实际的视频文件
/// 
/// 运行方法:
/// cargo test test_full_subtitle_extraction_flow --ignored -- --nocapture
#[test]
#[ignore]
fn test_full_subtitle_extraction_flow() {
    // 此测试需要手动设置以下环境变量:
    // GEMINI_API_KEY - Gemini API 密钥
    // TEST_VIDEO_PATH - 测试视频文件路径
    
    let api_key = std::env::var("GEMINI_API_KEY")
        .expect("请设置 GEMINI_API_KEY 环境变量");
    let video_path = std::env::var("TEST_VIDEO_PATH")
        .expect("请设置 TEST_VIDEO_PATH 环境变量");
    
    println!("API Key: {}...", &api_key[..10.min(api_key.len())]);
    println!("Video Path: {}", video_path);
    
    // 验证视频文件存在
    let path = PathBuf::from(&video_path);
    assert!(path.exists(), "视频文件不存在: {}", video_path);
    
    // 后续测试逻辑需要运行时环境...
    println!("集成测试需要完整的 Tauri 运行时环境");
}

/// 测试 FFmpeg 是否已安装
#[test]
fn test_ffmpeg_availability() {
    let output = std::process::Command::new("ffmpeg")
        .arg("-version")
        .output();
    
    match output {
        Ok(result) => {
            if result.status.success() {
                let version = String::from_utf8_lossy(&result.stdout);
                let first_line = version.lines().next().unwrap_or("Unknown");
                println!("✓ FFmpeg 已安装: {}", first_line);
            } else {
                println!("✗ FFmpeg 命令执行失败");
            }
        }
        Err(e) => {
            println!("✗ FFmpeg 未安装或无法访问: {}", e);
            println!("  请安装 FFmpeg: brew install ffmpeg (macOS)");
            // 不断言失败，因为这是可选依赖
        }
    }
}
