// 字幕提取模块
// 使用 Gemini 多模态 API 从视频中提取字幕
//
// 工作流程:
// 1. 使用 FFmpeg 从视频中提取音频 (MP3 格式)
// 2. 将音频文件编码为 base64
// 3. 发送至 Gemini API 进行转录
// 4. 解析转录结果为 ArticleSegment

use crate::ai_service::AIService;
use crate::types::{
    ArticleSegment, ChatContent, ChatMessage, ChatRequest, ContentPart, TranscriptionResult,
    TranscriptionSegment, VideoUrl,
};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use chrono::Utc;
use reqwest::Client;
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::AppHandle;
use tauri::Emitter;
use tauri_plugin_shell::ShellExt;
use uuid::Uuid;

// API 端点
const OPENAI_API_URL: &str = "https://api.openai.com/v1/chat/completions";
const OPENROUTER_API_URL: &str = "https://openrouter.ai/api/v1/chat/completions";
const API_302AI_URL: &str = "https://api.302.ai/v1/chat/completions";
const MOONSHOT_API_URL: &str = "https://api.moonshot.cn/v1/chat/completions";
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
    base_url: Option<&str>,
    event_id: &str,
) -> Result<Vec<ArticleSegment>, String> {
    println!("[SubtitleExtraction] 开始提取字幕: {:?}", video_path);

    // 发送开始事件
    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({ "phase": "start", "message": "开始提取字幕..." }),
    );

    // 1. 获取视频时长
    let duration = get_video_duration(&app, video_path).await?;
    println!(
        "[SubtitleExtraction] 视频时长: {:.1} 秒 ({:.1} 分钟)",
        duration,
        duration / 60.0
    );

    // 分片提取阈值：10分钟
    const CHUNK_THRESHOLD_SECONDS: f64 = 10.0 * 60.0;

    // Kimi K2.5 视频理解模式
    if provider == "moonshot" && model.contains("k2.5") {
        println!("[SubtitleExtraction] 检测到 Kimi K2.5 模型，启用视频理解模式");
        let _ = app.emit(&format!("subtitle-extraction-progress://{}", event_id), 
            serde_json::json!({ "phase": "processing", "message": "正在使用 Kimi 视频理解模式..." }));

        return extract_subtitles_with_kimi(app, video_path, video_id, api_key, model, event_id)
            .await;
    }

    if duration > CHUNK_THRESHOLD_SECONDS {
        println!("[SubtitleExtraction] 视频超过5分钟，启用分片提取模式");
        let _ = app.emit(
            &format!("subtitle-extraction-progress://{}", event_id),
            serde_json::json!({ "phase": "chunked", "message": "视频较长，启用分片提取模式..." }),
        );
        return extract_subtitles_chunked(
            app,
            video_path,
            video_id,
            provider,
            api_key,
            model,
            base_url,
            duration,
            event_id,
        )
        .await;
    }

    // 原有逻辑：短视频直接提取
    println!("[SubtitleExtraction] 视频较短，使用标准提取模式");
    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({ "phase": "audio", "message": "提取音频中..." }),
    );

    // 2. 从视频中提取完整音频
    let audio_path = extract_audio_from_video(&app, video_path).await?;
    println!("[SubtitleExtraction] 音频提取完成: {:?}", audio_path);

    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({ "phase": "transcribe", "message": "转录音频中..." }),
    );

    // 3. 调用 Gemini API 进行转录
    let transcription =
        transcribe_audio_with_gemini(&audio_path, provider, api_key, model, base_url).await?;
    println!(
        "[SubtitleExtraction] 转录完成，共 {} 个片段",
        transcription.segments.len()
    );

    // 4. 转换为 ArticleSegment
    let segments = transcription_to_segments(&transcription, video_id);

    // 5. 清理临时音频文件
    if let Err(e) = fs::remove_file(&audio_path) {
        println!("[SubtitleExtraction] 清理临时音频文件失败: {}", e);
    }

    let _ = app.emit(&format!("subtitle-extraction-progress://{}", event_id), 
        serde_json::json!({ "phase": "done", "message": "字幕提取完成！", "count": segments.len() }));

    Ok(segments)
}

/// 获取视频时长（秒）
///
/// 使用 FFmpeg 获取视频的精确时长（通过解析 stderr 输出）
async fn get_video_duration(app: &AppHandle, video_path: &Path) -> Result<f64, String> {
    let video_path_str = video_path.to_str().ok_or("无效的视频文件路径")?;
    let shell = app.shell();

    // 使用 FFmpeg 获取时长
    // 运行 FFmpeg 但不产生输出，从 stderr 解析时长信息
    // FFmpeg 会在 stderr 中输出类似 "Duration: 00:25:30.50" 的信息
    let output = shell
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}。请确保 sidecar 配置正确。", e))?
        .args(["-i", video_path_str, "-f", "null", "-"])
        .output()
        .await
        .map_err(|e| format!("FFmpeg 执行失败: {}。请确保已安装 FFmpeg。", e))?;

    // FFmpeg 即使成功也会返回非0状态码（因为我们没有真正输出）
    // 所以我们直接解析 stderr
    let stderr = String::from_utf8_lossy(&output.stderr);

    // 查找 Duration 行，格式: "Duration: HH:MM:SS.ms"
    for line in stderr.lines() {
        if line.contains("Duration:") {
            // 示例: "  Duration: 00:25:30.50, start: 0.000000, bitrate: 1234 kb/s"
            if let Some(duration_part) = line.split("Duration:").nth(1) {
                if let Some(time_str) = duration_part.split(',').next() {
                    let time_str = time_str.trim();
                    // 解析 HH:MM:SS.ms 格式
                    return parse_ffmpeg_duration(time_str);
                }
            }
        }
    }

    Err(format!(
        "无法从 FFmpeg 输出中解析视频时长。stderr: {}",
        stderr.chars().take(500).collect::<String>()
    ))
}

/// 解析 FFmpeg 时长格式 (HH:MM:SS.ms) 为秒
fn parse_ffmpeg_duration(time_str: &str) -> Result<f64, String> {
    let parts: Vec<&str> = time_str.split(':').collect();
    if parts.len() != 3 {
        return Err(format!("无效的时长格式: {}", time_str));
    }

    let hours: f64 = parts[0]
        .parse()
        .map_err(|_| format!("无法解析小时: {}", parts[0]))?;
    let minutes: f64 = parts[1]
        .parse()
        .map_err(|_| format!("无法解析分钟: {}", parts[1]))?;
    let seconds: f64 = parts[2]
        .parse()
        .map_err(|_| format!("无法解析秒: {}", parts[2]))?;

    Ok(hours * 3600.0 + minutes * 60.0 + seconds)
}

/// 分片音频提取结果
#[derive(Debug)]
struct ChunkTranscriptionResult {
    /// 转录得到的字幕片段（已调整时间轴）
    segments: Vec<TranscriptionSegment>,
    /// 第一个字幕的开始时间（调整后）
    #[allow(dead_code)]
    first_segment_start: Option<f64>,
    /// 最后一个字幕的结束时间（调整后）
    last_segment_end: Option<f64>,
    /// 时间轴偏移量
    #[allow(dead_code)]
    time_offset: f64,
}

/// 使用 FFmpeg 从视频中提取指定时间段的音频
///
/// # 参数
/// - `app`: Tauri 应用句柄
/// - `video_path`: 视频文件路径
/// - `start_time`: 起始时间（秒）
/// - `duration`: 提取时长（秒）
/// - `suffix`: 输出文件后缀（用于区分不同片段）
async fn extract_audio_segment(
    app: &AppHandle,
    video_path: &Path,
    start_time: f64,
    duration: f64,
    suffix: &str,
) -> Result<PathBuf, String> {
    let video_dir = video_path.parent().ok_or("无法获取视频目录")?;

    let video_stem = video_path
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or("无法获取视频文件名")?;

    let audio_path = video_dir.join(format!("{}_audio_{}.mp3", video_stem, suffix));
    let audio_path_str = audio_path.to_str().ok_or("无效的音频文件路径")?;
    let video_path_str = video_path.to_str().ok_or("无效的视频文件路径")?;

    // 清理旧文件
    if audio_path.exists() {
        if let Err(e) = fs::remove_file(&audio_path) {
            println!("[SubtitleExtraction] 清理旧音频片段文件失败: {}", e);
        }
    }

    let shell = app.shell();

    // FFmpeg 参数说明:
    // -ss: 起始时间（放在 -i 前面可以快速定位）
    // -t: 提取时长
    // -ar 44100: 保持44.1kHz采样率以保留语音细节
    // -ab 192k: 192kbps比特率兼顾质量和API文件大小限制
    let output = shell
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}。请确保 sidecar 配置正确。", e))?
        .args([
            "-ss",
            &format!("{:.2}", start_time),
            "-i",
            video_path_str,
            "-t",
            &format!("{:.2}", duration),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ab",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-y",
            audio_path_str,
        ])
        .output()
        .await
        .map_err(|e| format!("FFmpeg 执行失败: {}。请确保已安装 FFmpeg。", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("FFmpeg 音频片段提取失败: {}", stderr));
    }

    if !audio_path.exists() {
        return Err("音频片段文件未生成".to_string());
    }

    Ok(audio_path)
}

/// 提取并转录单个音频片段
///
/// 此函数提取指定时间段的音频，发送至 API 转录，并调整时间轴
async fn extract_and_transcribe_segment(
    app: AppHandle,
    video_path: PathBuf,
    start_time: f64,
    duration: f64,
    suffix: String,
    provider: String,
    api_key: String,
    model: String,
    base_url: Option<String>,
) -> Result<ChunkTranscriptionResult, String> {
    println!(
        "[SubtitleExtraction] 提取片段: start={:.1}s, duration={:.1}s, suffix={}",
        start_time, duration, suffix
    );

    // 1. 提取音频片段
    let audio_path =
        extract_audio_segment(&app, &video_path, start_time, duration, &suffix).await?;

    // 2. 转录音频
    let transcription =
        transcribe_audio_with_gemini(
            &audio_path,
            &provider,
            &api_key,
            &model,
            base_url.as_deref(),
        )
        .await?;

    // 3. 清理临时音频文件
    if let Err(e) = fs::remove_file(&audio_path) {
        println!("[SubtitleExtraction] 清理临时音频片段失败: {}", e);
    }

    // 4. 调整时间轴（加上偏移量）
    let segments: Vec<TranscriptionSegment> = transcription
        .segments
        .into_iter()
        .map(|mut seg| {
            if let Some(st) = seg.start_time {
                seg.start_time = Some(st + start_time);
            }
            if let Some(et) = seg.end_time {
                seg.end_time = Some(et + start_time);
            }
            seg
        })
        .collect();

    // 5. 获取边界时间
    let first_segment_start = segments.first().and_then(|s| s.start_time);
    let last_segment_end = segments.last().and_then(|s| s.end_time);

    println!(
        "[SubtitleExtraction] 片段 {} 转录完成: {} 个字幕, 时间范围 {:?} - {:?}",
        suffix,
        segments.len(),
        first_segment_start,
        last_segment_end
    );

    Ok(ChunkTranscriptionResult {
        segments,
        first_segment_start,
        last_segment_end,
        time_offset: start_time,
    })
}

/// 分片提取长视频字幕（顺序线性分片策略）
///
/// # 算法说明
/// 1. 将音频按固定步长（10分钟）顺序切片，相邻片段有30秒重叠
/// 2. 每两个相邻片段并发提取，逐步向前推进
/// 3. 合并所有片段后，通过模糊匹配去重消除overlap区域的重复字幕
async fn extract_subtitles_chunked(
    app: AppHandle,
    video_path: &Path,
    video_id: &str,
    provider: &str,
    api_key: &str,
    model: &str,
    base_url: Option<&str>,
    total_duration: f64,
    event_id: &str,
) -> Result<Vec<ArticleSegment>, String> {
    const CHUNK_DURATION: f64 = 10.0 * 60.0; // 每片10分钟
    const OVERLAP: f64 = 30.0; // 30秒重叠
    let step = CHUNK_DURATION - OVERLAP; // 实际步进 = 9分30秒

    // 计算所有片段的起始时间
    let mut chunk_starts: Vec<f64> = Vec::new();
    let mut pos = 0.0;
    while pos < total_duration {
        chunk_starts.push(pos);
        pos += step;
    }
    let total_chunks = chunk_starts.len() as i32;
    let mut completed_chunks = 0;

    println!(
        "[SubtitleExtraction] 顺序分片: 共 {} 个片段, 每片 {:.0}s, 重叠 {:.0}s, 步进 {:.0}s",
        total_chunks, CHUNK_DURATION, OVERLAP, step
    );

    let mut all_segments: Vec<TranscriptionSegment> = Vec::new();

    // 两两并发提取
    let mut i = 0;
    while i < chunk_starts.len() {
        // 计算本轮要提取的片段（最多2个并发）
        let start1 = chunk_starts[i];
        let dur1 = (total_duration - start1).min(CHUNK_DURATION);

        if i + 1 < chunk_starts.len() {
            // 并发提取两个片段
            let start2 = chunk_starts[i + 1];
            let dur2 = (total_duration - start2).min(CHUNK_DURATION);

            let _ = app.emit(
                &format!("subtitle-extraction-progress://{}", event_id),
                serde_json::json!({
                    "phase": "chunk",
                    "message": format!("提取片段 {}-{}/{}", i+1, i+2, total_chunks),
                    "current": completed_chunks,
                    "total": total_chunks
                }),
            );

            let (r1, r2) = tokio::join!(
                extract_and_transcribe_segment(
                    app.clone(),
                    video_path.to_path_buf(),
                    start1,
                    dur1,
                    format!("chunk_{}", i),
                    provider.to_string(),
                    api_key.to_string(),
                    model.to_string(),
                    base_url.map(str::to_string),
                ),
                extract_and_transcribe_segment(
                    app.clone(),
                    video_path.to_path_buf(),
                    start2,
                    dur2,
                    format!("chunk_{}", i + 1),
                    provider.to_string(),
                    api_key.to_string(),
                    model.to_string(),
                    base_url.map(str::to_string),
                )
            );

            all_segments.extend(r1?.segments);
            all_segments.extend(r2?.segments);
            completed_chunks += 2;
            i += 2;
        } else {
            // 奇数片段，单独提取
            let _ = app.emit(
                &format!("subtitle-extraction-progress://{}", event_id),
                serde_json::json!({
                    "phase": "chunk",
                    "message": format!("提取片段 {}/{}", i+1, total_chunks),
                    "current": completed_chunks,
                    "total": total_chunks
                }),
            );

            let r = extract_and_transcribe_segment(
                app.clone(),
                video_path.to_path_buf(),
                start1,
                dur1,
                format!("chunk_{}", i),
                provider.to_string(),
                api_key.to_string(),
                model.to_string(),
                base_url.map(str::to_string),
            )
            .await?;

            all_segments.extend(r.segments);
            completed_chunks += 1;
            i += 1;
        }

        let _ = app.emit(&format!("subtitle-extraction-progress://{}", event_id),
            serde_json::json!({
                "phase": "chunk",
                "message": format!("已完成 {}/{} 片段", completed_chunks.min(total_chunks), total_chunks),
                "current": completed_chunks.min(total_chunks),
                "total": total_chunks
            }));
    }

    // === 合并、排序、去重 ===
    println!(
        "[SubtitleExtraction] === 合并排序去重: {} 个原始字幕 ===",
        all_segments.len()
    );
    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({
            "phase": "merge",
            "message": "合并排序去重中..."
        }),
    );

    // 过滤掉没有时间戳的字幕
    all_segments.retain(|s| s.start_time.is_some() && s.end_time.is_some());

    // 按时间排序
    all_segments.sort_by(|a, b| {
        let a_time = a.start_time.unwrap_or(0.0);
        let b_time = b.start_time.unwrap_or(0.0);
        a_time
            .partial_cmp(&b_time)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    // 去重：移除时间重叠且内容相似的字幕
    let deduped_segments = deduplicate_segments(all_segments);

    println!(
        "[SubtitleExtraction] 分片提取完成，共 {} 个字幕片段",
        deduped_segments.len()
    );

    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({
            "phase": "done",
            "message": "字幕提取完成！",
            "count": deduped_segments.len()
        }),
    );

    // 转换为 ArticleSegment
    let result = TranscriptionResult {
        segments: deduped_segments,
        full_text: String::new(),
    };

    Ok(transcription_to_segments(&result, video_id))
}

/// 计算两个字符串的相似度 (基于最长公共子序列, 0.0-1.0)
fn text_similarity(a: &str, b: &str) -> f64 {
    let a = a.trim();
    let b = b.trim();
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    if a == b {
        return 1.0;
    }

    let a_chars: Vec<char> = a.chars().collect();
    let b_chars: Vec<char> = b.chars().collect();
    let m = a_chars.len();
    let n = b_chars.len();

    // LCS 用两行滚动数组节省内存
    let mut prev = vec![0u32; n + 1];
    let mut curr = vec![0u32; n + 1];

    for i in 1..=m {
        for j in 1..=n {
            if a_chars[i - 1] == b_chars[j - 1] {
                curr[j] = prev[j - 1] + 1;
            } else {
                curr[j] = prev[j].max(curr[j - 1]);
            }
        }
        std::mem::swap(&mut prev, &mut curr);
        curr.iter_mut().for_each(|x| *x = 0);
    }

    let lcs_len = prev[n] as f64;
    let max_len = m.max(n) as f64;
    lcs_len / max_len
}

/// 去除重复的字幕片段
///
/// 判断标准（针对分片overlap区域优化）：
/// 1. 时间接近（起始时间差 < 15秒）
/// 2. 内容相似度 > 60%（基于 LCS）
///
/// 当检测到重复时，保留已有的（更早进入结果集的）版本
fn deduplicate_segments(segments: Vec<TranscriptionSegment>) -> Vec<TranscriptionSegment> {
    if segments.is_empty() {
        return segments;
    }

    let mut result: Vec<TranscriptionSegment> = Vec::new();

    for seg in segments {
        let seg_start = seg.start_time.unwrap_or(0.0);

        let is_duplicate = result.iter().any(|existing| {
            let ex_start = existing.start_time.unwrap_or(0.0);

            // 快速排除：起始时间差超过15秒不可能是同一句
            if (seg_start - ex_start).abs() > 15.0 {
                return false;
            }

            // 计算时间重叠
            let seg_end = seg.end_time.unwrap_or(seg_start);
            let ex_end = existing.end_time.unwrap_or(ex_start);
            let overlap_start = seg_start.max(ex_start);
            let overlap_end = seg_end.min(ex_end);
            let overlap_duration = (overlap_end - overlap_start).max(0.0);
            let seg_duration = (seg_end - seg_start).max(0.1);
            let overlap_ratio = overlap_duration / seg_duration;

            // 条件1: 时间重叠 > 30% 且内容相似度 > 60%
            if overlap_ratio > 0.3 {
                let sim = text_similarity(&seg.content, &existing.content);
                if sim > 0.6 {
                    return true;
                }
            }

            // 条件2: 起始时间非常接近（< 5秒）且内容高度相似
            if (seg_start - ex_start).abs() < 5.0 {
                let sim = text_similarity(&seg.content, &existing.content);
                if sim > 0.5 {
                    return true;
                }
            }

            false
        });

        if !is_duplicate {
            result.push(seg);
        }
    }

    result
}

/// 使用 FFmpeg 从视频中提取音频
///
/// 输出格式: MP3 (Gemini 支持的格式)
/// 输出位置: 与视频同目录，文件名为 {video_name}_audio.mp3
async fn extract_audio_from_video(app: &AppHandle, video_path: &Path) -> Result<PathBuf, String> {
    let video_dir = video_path.parent().ok_or("无法获取视频目录")?;

    let video_stem = video_path
        .file_stem()
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
    // -ab 192k: 192kbps 保留语音细节
    // -ar 44100: 44.1kHz 采样率保留完整频率信息
    // -ac 1: 单声道
    // -y: 覆盖已存在的文件
    let shell = app.shell();

    let output = shell
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}。请确保 sidecar 配置正确。", e))?
        .args([
            "-i",
            video_path_str,
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ab",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "1",
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

/// 使用 Kimi K2.5 模型提取字幕 (视频理解 - 使用 Base64 内嵌视频)
async fn extract_subtitles_with_kimi(
    app: AppHandle,
    video_path: &Path,
    video_id: &str,
    api_key: &str,
    model: &str,
    event_id: &str,
) -> Result<Vec<ArticleSegment>, String> {
    // 1. 压缩视频 (至 480p, CRF 28 以减小体积，便于 Base64 编码)
    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({ "phase": "compress", "message": "正在优化视频体积..." }),
    );

    let compressed_path = compress_video_for_upload(&app, video_path).await?;
    println!("[SubtitleExtraction] 视频压缩完成: {:?}", compressed_path);

    // 2. 读取压缩后的视频并 Base64 编码
    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({ "phase": "encode", "message": "正在编码视频数据..." }),
    );

    let video_bytes = fs::read(&compressed_path).map_err(|e| format!("读取压缩视频失败: {}", e))?;

    let video_size_mb = video_bytes.len() as f64 / 1024.0 / 1024.0;
    println!(
        "[SubtitleExtraction] 压缩后视频大小: {:.2} MB",
        video_size_mb
    );

    // 获取视频扩展名用于 MIME 类型
    let ext = compressed_path
        .extension()
        .and_then(|s| s.to_str())
        .unwrap_or("mp4")
        .to_lowercase();

    // 构建 data URL: data:video/{ext};base64,{base64_data}
    let video_base64 = BASE64.encode(&video_bytes);
    let video_data_url = format!("data:video/{};base64,{}", ext, video_base64);

    // 清理本地压缩文件
    if let Err(e) = fs::remove_file(&compressed_path) {
        println!("[SubtitleExtraction] 警告: 清理临时视频文件失败: {}", e);
    }

    // 3. 发送转录请求
    let _ = app.emit(
        &format!("subtitle-extraction-progress://{}", event_id),
        serde_json::json!({ "phase": "analyze", "message": "Kimi 正在分析视频生成字幕..." }),
    );

    let prompt = r#"请分析视频中的语音内容，并生成带时间轴的字幕。
严格按照以下 JSON 格式返回结果：
{
  "segments": [
    {
      "start": "MM:SS",
      "end": "MM:SS",
      "content": "字幕内容"
    }
  ],
  "full_text": "全文内容"
}
要求：
1. 精确对应语音时间。
2. 按句子或短语断句。
3. 保持原语言，不要翻译。
4. 忽略背景音和无意义语气词。
"#;

    let ai_service = AIService::new(
        api_key.to_string(),
        "moonshot".to_string(),
        model.to_string(),
    );

    let chat_request = ChatRequest {
        model: model.to_string(),
        messages: vec![ChatMessage {
            role: "user".to_string(),
            content: ChatContent::Parts(vec![
                ContentPart {
                    part_type: "video_url".to_string(),
                    text: None,
                    image_url: None,
                    file_data: None,
                    video_url: Some(VideoUrl {
                        url: video_data_url, // 使用 Base64 data URL
                    }),
                },
                ContentPart {
                    part_type: "text".to_string(),
                    text: Some(prompt.to_string()),
                    image_url: None,
                    file_data: None,
                    video_url: None,
                },
            ]),
        }],
        temperature: Some(1.0), // Kimi 要求 temperature=1
    };

    let response = match ai_service.chat(chat_request).await {
        Ok(res) => res,
        Err(e) => return Err(format!("Kimi 分析失败: {}", e)),
    };

    // 4. 解析结果
    let transcription = parse_transcription_response(&response.content)?;

    // 5. 转换为 ArticleSegment
    let segments = transcription_to_segments(&transcription, video_id);

    let _ = app.emit(&format!("subtitle-extraction-progress://{}", event_id), 
        serde_json::json!({ "phase": "done", "message": "字幕提取完成！", "count": segments.len() }));

    Ok(segments)
}

/// 压缩视频以便上传
/// 目标: 480p, CRF 28, Preset veryfast
async fn compress_video_for_upload(app: &AppHandle, video_path: &Path) -> Result<PathBuf, String> {
    let video_dir = video_path.parent().ok_or("无效的视频目录")?;
    let video_stem = video_path
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or("无效的文件名")?;
    let output_path = video_dir.join(format!("{}_compressed.mp4", video_stem));

    if output_path.exists() {
        let _ = fs::remove_file(&output_path);
    }

    let shell = app.shell();

    let output = shell
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}", e))?
        .args([
            "-i",
            video_path.to_str().unwrap(),
            "-vf",
            "scale=-2:480", // Scale to 480p height, width auto
            "-c:v",
            "libx264",
            "-crf",
            "28", // Lower quality for smaller size
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ac",
            "1", // Mono audio
            "-y",
            output_path.to_str().unwrap(),
        ])
        .output()
        .await
        .map_err(|e| format!("FFmpeg 压缩失败: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("FFmpeg 压缩错误: {}", stderr));
    }

    if !output_path.exists() {
        return Err("压缩后的视频文件未生成".to_string());
    }

    Ok(output_path)
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
    base_url: Option<&str>,
) -> Result<TranscriptionResult, String> {
    const MAX_RETRIES: u32 = 3;
    let mut retry_count = 0;

    loop {
        // 读取并编码音频文件 (每次重试都重新读取可能没必要，但为了安全起见暂时不改这里)
        let audio_bytes = fs::read(audio_path).map_err(|e| format!("读取音频文件失败: {}", e))?;

        let audio_base64 = BASE64.encode(&audio_bytes);
        let audio_size_mb = audio_bytes.len() as f64 / 1024.0 / 1024.0;
        println!("[SubtitleExtraction] 音频文件大小: {:.2} MB", audio_size_mb);

        // 注意：20MB 限制现在由分片提取算法处理，此处不再需要检查

        // 转录提示词 - 强调时间戳精度和按句子断句
        let transcription_prompt = r#"Transcribe this audio into text with precise timestamps. Return strictly in the following JSON format.

Requirements:
1. **Sentence-level segmentation**: Each segment contains exactly ONE complete sentence. Do NOT merge multiple sentences.
2. Split at sentence-ending punctuation (periods, question marks, exclamation marks) or natural speech pauses.
3. Each sentence should be roughly 5-30 characters/words. Never exceed 50.
4. **Timestamp accuracy is critical**: start and end times MUST precisely match when the speech actually begins and ends in the audio. Listen carefully to the exact timing.
5. Format: MM:SS (e.g., "01:23" for 1 minute 23 seconds). Both start and end are required.
6. Keep the original language. Do NOT translate.
7. Timestamps must be monotonically increasing — each segment's start must be >= the previous segment's end.

Return format:
{
  "segments": [
    {
      "start": "00:00",
      "end": "00:03",
      "content": "First sentence of the audio.",
      "speaker": null
    },
    {
      "start": "00:03",
      "end": "00:06",
      "content": "Second sentence of the audio.",
      "speaker": null
    }
  ],
  "full_text": "Full transcription text..."
}

IMPORTANT: Each segment = one sentence. Timestamps must be precise to the second.
"#;

        let client = Client::new();

        // 根据提供商选择不同的 API 格式
        let response = match provider {
            "google" | "google-ai-studio" => {
                // Google Gemini 直接 API
                let url = format!(
                    "{}/{}:generateContent?key={}",
                    GOOGLE_GEMINI_URL,
                    model.strip_prefix("models/").unwrap_or(model),
                    api_key
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
                // OpenAI 兼容格式：优先使用用户配置的 base_url，避免错误回退到固定网关
                let api_url = if let Some(custom_base_url) =
                    base_url.and_then(|url| (!url.trim().is_empty()).then_some(url))
                {
                    let trimmed = custom_base_url.trim_end_matches('/');
                    if trimmed.ends_with("/chat/completions") {
                        trimmed.to_string()
                    } else {
                        format!("{}/chat/completions", trimmed)
                    }
                } else {
                    match provider {
                        "openrouter" => OPENROUTER_API_URL.to_string(),
                        "302ai" => API_302AI_URL.to_string(),
                        "moonshot" => MOONSHOT_API_URL.to_string(),
                        "openai" => OPENAI_API_URL.to_string(),
                        "openai-compatible" => {
                            return Err(
                                "openai-compatible provider requires base_url in settings"
                                    .to_string(),
                            );
                        }
                        _ => {
                            return Err(format!(
                                "Unsupported provider '{}' for subtitle transcription without base_url",
                                provider
                            ));
                        }
                    }
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
                    .post(&api_url)
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
        match parse_transcription_response(&content) {
            Ok(result) => return Ok(result),
            Err(e) => {
                println!("[SubtitleExtraction] JSON 解析失败: {}", e);
                println!("[SubtitleExtraction] 尝试解析的原始内容: {}", content);

                retry_count += 1;
                if retry_count >= MAX_RETRIES {
                    // 最后一次尝试失败，如果是解析错误且内容不为空，可能是格式问题
                    // 但如果内容为空，已经在 parse_transcription_response 中处理了
                    return Err(format!("多次重试后仍然失败: {}", e));
                }

                println!(
                    "[SubtitleExtraction] 将进行第 {} 次重试...",
                    retry_count + 1
                );
                tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                continue;
            }
        }
    } // end loop
}

/// 解析转录 API 响应
/// 解析转录 API 响应
fn parse_transcription_response(content: &str) -> Result<TranscriptionResult, String> {
    // 0. 处理空内容
    if content.trim().is_empty() {
        println!("[SubtitleExtraction] 警告: API 返回内容为空，视为空音频处理");
        return Ok(TranscriptionResult {
            segments: Vec::new(),
            full_text: String::new(),
        });
    }

    // 尝试提取 JSON
    let mut json_str = extract_json(content);

    // 如果提取出的 JSON 为空
    if json_str.trim().is_empty() {
        println!("[SubtitleExtraction] 警告: 无法提取有效 JSON，尝试直接解析原始内容");
        // 尝试直接解析内容，也许内容本身就是 JSON
        if let Ok(parsed) = serde_json::from_str::<Value>(content) {
            if parsed.get("segments").is_some() {
                // 内容本身就是有效的 JSON
                json_str = content.to_string();
            } else {
                println!("[SubtitleExtraction] 警告: 内容是 JSON 但没有 segments 字段，视为空音频");
                return Ok(TranscriptionResult {
                    segments: Vec::new(),
                    full_text: String::new(),
                });
            }
        } else {
            println!("[SubtitleExtraction] 警告: 内容不是 JSON 且无法提取，视为空音频");
            return Ok(TranscriptionResult {
                segments: Vec::new(),
                full_text: String::new(),
            });
        }
    }

    // 解析 JSON
    let parsed: Value = serde_json::from_str(&json_str).map_err(|e| {
        format!(
            "JSON 解析失败: {}. \n提取的JSON: {}\n原始响应: {}",
            e, json_str, content
        )
    })?;

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

    let full_text = parsed["full_text"].as_str().unwrap_or("").to_string();

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
                return content[start + 7..start + end].trim().to_string();
            }
        }
    }

    // 2. 尝试找通用代码块
    if let Some(start) = content.find("```") {
        if let Some(end_offset) = content[start + 3..].find("```") {
            let end = start + 3 + end_offset;
            return content[start + 3..end].trim().to_string();
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
    transcription
        .segments
        .iter()
        .enumerate()
        .map(|(i, seg)| ArticleSegment {
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
        let content =
            r#"{"segments": [{"start": "00:00", "content": "Test"}], "full_text": "Test"}"#;
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
