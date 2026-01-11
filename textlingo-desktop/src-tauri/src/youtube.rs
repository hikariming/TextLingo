use crate::types::{Article, ArticleSegment};
use chrono::Utc;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;
use uuid::Uuid;

const VIDEOS_DIR: &str = "videos";

#[derive(Debug, Serialize, Deserialize)]
struct YtDlpOutput {
    id: String,
    title: String,
    #[serde(default)]
    ext: String,
}

/// Import a YouTube video: download, extract subs, create Article
/// 字幕下载是可选的，如果失败会继续导入视频（后续可用 TTS 识别）
pub async fn import_youtube_video(app: AppHandle, url: String) -> Result<Article, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?;
    
    let videos_dir = app_data_dir.join(VIDEOS_DIR);
    if !videos_dir.exists() {
        fs::create_dir_all(&videos_dir)
            .map_err(|e| format!("Failed to create videos dir: {}", e))?;
    }

    // 1. Run yt-dlp to download video and subs
    // Output template: videos_dir/%(id)s.%(ext)s
    let output_template = videos_dir.join("%(id)s.%(ext)s");
    let output_template_str = output_template.to_str().ok_or("Invalid output path")?;

    let shell = app.shell();
    
    // 使用 --ignore-errors 让字幕下载失败时继续
    // 使用 --no-warnings 减少警告输出
    // 格式选择器说明:
    // - best[ext=mp4]: 优先选择已合并的 MP4（无需 FFmpeg）
    // - bestvideo+bestaudio: 如果没有合并格式，下载最佳并尝试合并
    // - best: 最后的回退选项
    let output = shell
        .sidecar("yt-dlp")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .args([
            "--no-warnings",              // 忽略警告（如 JS runtime 警告）
            "--ignore-errors",            // 忽略非致命错误（如字幕下载失败）
            "--write-auto-sub",
            "--sub-lang", "en,zh-Hans,zh-Hant", // 首选语言
            "--convert-subs", "srt",
            // 格式优化：
            // 1. best[ext=mp4][vcodec^=avc1]: 最优先 - H.264编码的MP4（macOS兼容性最好，且是预合并的）
            // 2. best[ext=mp4]: 次选 - 任意编码的预合并MP4
            // 3. best: 最后回退
            "-f", "best[ext=mp4][vcodec^=avc1]/best[ext=mp4]/best",
            "--merge-output-format", "mp4", // 如需合并则输出为 MP4
            "-o", output_template_str,
            "--print-json",               // 获取元数据
            "--no-simulate",
            &url,
        ])
        .output()
        .await
        .map_err(|e| format!("Failed to execute yt-dlp: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    
    // 检查是否有 JSON 输出（视频下载成功的标志）
    let json_line = stdout.lines()
        .filter(|l| l.starts_with('{'))
        .last();
    
    // 如果没有 JSON 输出，说明视频下载完全失败
    let json_line = match json_line {
        Some(line) => line,
        None => {
            // 检查 stderr 中是否有更具体的错误信息
            if stderr.contains("Video unavailable") {
                return Err("视频不可用，可能是私有视频或已被删除".to_string());
            } else if stderr.contains("Sign in") {
                return Err("此视频需要登录才能观看".to_string());
            } else if stderr.contains("ffmpeg") || stderr.contains("FFmpeg") {
                return Err("需要安装 FFmpeg 才能下载此视频。请安装后重试。".to_string());
            } else if !output.status.success() {
                return Err(format!("视频下载失败: {}", stderr));
            } else {
                return Err("无法获取视频信息".to_string());
            }
        }
    };
    
    let metadata: YtDlpOutput = serde_json::from_str(json_line)
        .map_err(|e| format!("Failed to parse metadata: {}", e))?;

    let video_id = metadata.id;
    let video_title = metadata.title;
    
    // 查找实际下载的视频文件（可能是 .mp4, .webm 等）
    let video_path = find_video_file(&videos_dir, &video_id)?;
    
    // 2. 查找字幕文件（可选，失败不报错）
    // yt-dlp pattern: {id}.{lang}.srt
    let segments = match find_srt_file(&videos_dir, &video_id) {
        Ok(srt_path) => {
            // 字幕文件存在，解析它
            match parse_srt(&srt_path) {
                Ok(mut segs) => {
                    for segment in &mut segs {
                        segment.article_id = video_id.clone();
                    }
                    segs
                }
                Err(_) => {
                    // 字幕解析失败，返回空列表
                    Vec::new()
                }
            }
        }
        Err(_) => {
            // 没有找到字幕文件，返回空列表（后续可用 TTS 识别）
            Vec::new()
        }
    };

    // 3. 构建内容文本
    let content = if segments.is_empty() {
        // 没有字幕时，使用占位文本
        format!("[视频已导入，字幕待识别] {}", video_title)
    } else {
        segments.iter().map(|s| s.text.clone()).collect::<Vec<_>>().join(" ")
    };

    // 4. Create Article
    let article = Article {
        id: video_id.clone(),
        title: video_title,
        content,
        source_url: Some(url),
        media_path: Some(video_path.to_string_lossy().into_owned()),
        created_at: Utc::now().to_rfc3339(),
        translated: false,
        segments,
    };

    Ok(article)
}

/// 查找实际下载的视频文件（可能是 .mp4, .webm, .mkv 等格式）
fn find_video_file(dir: &Path, video_id: &str) -> Result<PathBuf, String> {
    let video_extensions = ["mp4", "webm", "mkv", "m4a", "avi", "mov"];
    let entries = fs::read_dir(dir).map_err(|e| e.to_string())?;
    
    // 优先查找完整的视频文件（不包含格式代码如 .f398.mp4）
    let mut all_matches: Vec<PathBuf> = Vec::new();
    
    for entry in entries {
        let entry = entry.map_err(|os_err| os_err.to_string())?;
        let path = entry.path();
        if let Some(fname) = path.file_name().and_then(|f| f.to_str()) {
            // 文件名必须以 video_id 开头
            if fname.starts_with(video_id) {
                // 检查是否是视频文件
                for ext in &video_extensions {
                    if fname.ends_with(&format!(".{}", ext)) {
                        all_matches.push(path.clone());
                        break;
                    }
                }
            }
        }
    }
    
    // 优先选择不包含格式代码的文件（如 abc.mp4 优于 abc.f398.mp4）
    all_matches.sort_by(|a, b| {
        let a_name = a.file_name().unwrap_or_default().to_string_lossy();
        let b_name = b.file_name().unwrap_or_default().to_string_lossy();
        let a_has_format_code = a_name.contains(".f") && a_name.chars().filter(|c| *c == '.').count() > 1;
        let b_has_format_code = b_name.contains(".f") && b_name.chars().filter(|c| *c == '.').count() > 1;
        a_has_format_code.cmp(&b_has_format_code)
    });
    
    all_matches.into_iter().next()
        .ok_or_else(|| format!("未找到视频文件: {}", video_id))
}

fn find_srt_file(dir: &Path, video_id: &str) -> Result<PathBuf, String> {
    // Check for common patterns: id.en.srt, id.zh-Hans.srt, etc.
    let entries = fs::read_dir(dir).map_err(|e| e.to_string())?;
    
    for entry in entries {
        let entry = entry.map_err(|os_err| os_err.to_string())?;
        let path = entry.path();
        if let Some(fname) = path.file_name().and_then(|f| f.to_str()) {
            if fname.starts_with(video_id) && fname.ends_with(".srt") {
                return Ok(path);
            }
        }
    }
    
    Err("No subtitle file found".to_string())
}

fn parse_srt(path: &Path) -> Result<Vec<ArticleSegment>, String> {
    let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let mut segments = Vec::new();
    
    // Simple SRT parser
    // Block format:
    // 1
    // 00:00:00,000 --> 00:00:02,000
    // Text line 1
    // Text line 2
    
    let blocks: Vec<&str> = content.split("\n\n").collect();
    let time_regex = Regex::new(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})").unwrap();

    for block in blocks {
        let lines: Vec<&str> = block.lines().collect();
        if lines.len() >= 3 {
             // Line 0: Index
             // Line 1: Timestamp
             // Line 2+: Text
             if let Some(_caps) = time_regex.captures(lines[1]) {
                 // let start = &caps[1];
                 // let end = &caps[2];
                 let text = lines[2..].join(" ");
                 
                 // Clean text (remove HTML tags if any)
                 let text = text.replace("<i>", "").replace("</i>", "").trim().to_string();
                 
                 if !text.is_empty() {
                     segments.push(ArticleSegment {
                         id: Uuid::new_v4().to_string(),
                         article_id: String::new(), // Will be set by caller
                         order: segments.len() as i32,
                         text,
                         reading_text: None,
                         translation: None,
                         explanation: None,
                         created_at: Utc::now().to_rfc3339(),
                         is_new_paragraph: true, // SRT blocks usually separate sentences/phrases
                     });
                 }
             }
        }
    }

    Ok(segments)
}
