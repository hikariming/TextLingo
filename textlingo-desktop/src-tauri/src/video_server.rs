// 本地 HTTP 视频流服务器
// 使用 warp 框架提供视频文件，完美支持 Range 请求
// 这是解决 macOS WebKit 自定义协议视频播放问题的终极方案

use std::io::SeekFrom;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::fs::File;
use tokio::io::{AsyncReadExt, AsyncSeekExt};
use tokio_util::io::ReaderStream;
use warp::http::{Response, StatusCode};
use warp::hyper::Body;
use warp::Filter;

/// 视频服务器端口（固定使用一个不太常用的端口）
pub const VIDEO_SERVER_PORT: u16 = 19420;

/// 启动资源服务器（在后台运行）
/// 提供视频和书籍文件的本地访问
pub async fn start_resource_server(app_data_dir: PathBuf) -> Result<(), String> {
    let app_data_dir = Arc::new(app_data_dir);

    // 视频目录: app_data_dir/videos
    let videos_dir_filter = {
        let dir = app_data_dir.join("videos");
        warp::any().map(move || Arc::new(dir.clone()))
    };

    // 书籍目录: app_data_dir/books
    let books_dir_filter = {
        let dir = app_data_dir.join("books");
        warp::any().map(move || Arc::new(dir.clone()))
    };

    // GET /video/{filename}
    let video_route = warp::path("video")
        .and(warp::path::param::<String>())
        .and(warp::header::optional::<String>("range"))
        .and(videos_dir_filter)
        .and_then(serve_file);

    // GET /book/{filename}
    let book_route = warp::path("book")
        .and(warp::path::param::<String>())
        .and(warp::header::optional::<String>("range"))
        .and(books_dir_filter)
        .and_then(serve_file);

    // CORS 支持（允许来自 Tauri webview 的请求）
    let cors = warp::cors()
        .allow_any_origin()
        .allow_methods(vec!["GET", "HEAD", "OPTIONS"])
        .allow_headers(vec!["range", "content-type"]);

    let routes = video_route.or(book_route).with(cors);

    // 在后台启动服务器
    tokio::spawn(async move {
        println!("[ResourceServer] Starting on port {}", VIDEO_SERVER_PORT);
        warp::serve(routes)
            .run(([127, 0, 0, 1], VIDEO_SERVER_PORT))
            .await;
    });

    Ok(())
}

/// 提供文件（支持 Range 请求）
/// 通用于视频和书籍
async fn serve_file(
    filename: String,
    range_header: Option<String>,
    base_dir: Arc<PathBuf>,
) -> Result<impl warp::Reply, warp::Rejection> {
    // URL 解码文件名
    let decoded_filename = urlencoding::decode(&filename)
        .map(|s| s.to_string())
        .unwrap_or(filename);

    let file_path = base_dir.join(&decoded_filename);

    // 安全检查：确保文件在指定目录内
    if !file_path.starts_with(base_dir.as_ref()) {
        println!("[ResourceServer] Forbidden access: {:?}", file_path);
        return Ok(Response::builder()
            .status(StatusCode::FORBIDDEN)
            .body(Body::empty())
            .unwrap());
    }

    // 打开文件
    let mut file = match File::open(&file_path).await {
        Ok(f) => f,
        Err(e) => {
            println!("[ResourceServer] File not found: {:?} ({})", file_path, e);
            return Ok(Response::builder()
                .status(StatusCode::NOT_FOUND)
                .body(Body::from("File not found"))
                .unwrap());
        }
    };

    let metadata = match file.metadata().await {
        Ok(m) => m,
        Err(_) => {
            return Ok(Response::builder()
                .status(StatusCode::INTERNAL_SERVER_ERROR)
                .body(Body::empty())
                .unwrap());
        }
    };

    let file_size = metadata.len();

    // 确定 Content-Type
    let content_type = if decoded_filename.ends_with(".mp4") {
        "video/mp4"
    } else if decoded_filename.ends_with(".webm") {
        "video/webm"
    } else if decoded_filename.ends_with(".mkv") {
        "video/x-matroska"
    } else if decoded_filename.ends_with(".mp3") {
        "audio/mpeg"
    } else if decoded_filename.ends_with(".wav") {
        "audio/wav"
    } else if decoded_filename.ends_with(".m4a") {
        "audio/mp4"
    } else if decoded_filename.ends_with(".aac") {
        "audio/aac"
    } else if decoded_filename.ends_with(".flac") {
        "audio/flac"
    } else if decoded_filename.ends_with(".ogg") {
        "audio/ogg"
    } else if decoded_filename.ends_with(".wma") {
        "audio/x-ms-wma"
    } else if decoded_filename.ends_with(".epub") {
        "application/epub+zip"
    } else if decoded_filename.ends_with(".txt") {
        "text/plain; charset=utf-8"
    } else if decoded_filename.ends_with(".pdf") {
        "application/pdf"
    } else {
        "application/octet-stream"
    };

    // 判断是否为流媒体类型（视频/音频）
    let is_streaming_media =
        content_type.starts_with("video/") || content_type.starts_with("audio/");

    // 解析 Range 请求，确定读取范围
    // 规则：
    // 1) 如果是视频/音频，始终返回分段响应 (206) 以兼容 WebKit 的拖动
    // 2) 对于 EPUB/PDF/TXT 等非流式文件，始终返回完整文件，避免被截断导致解压失败
    let (start, end, status_code) = if is_streaming_media {
        let (s, e) = match parse_range_header(range_header.as_deref(), file_size) {
            Some((s, e)) => (s, e),
            // 无 Range 时也返回 206，表明支持随机访问
            None => (0, file_size - 1),
        };
        (s, e, StatusCode::PARTIAL_CONTENT)
    } else {
        // 始终返回完整文件 (200) 以避免 EPUB/PDF 被截断
        (0, file_size - 1, StatusCode::OK)
    };

    if start > end || start >= file_size {
        return Ok(Response::builder()
            .status(StatusCode::RANGE_NOT_SATISFIABLE)
            .header("Content-Range", format!("bytes */{}", file_size))
            .body(Body::empty())
            .unwrap());
    }

    let chunk_size = end - start + 1;

    // Seek 到起始位置
    if let Err(_) = file.seek(SeekFrom::Start(start)).await {
        return Ok(Response::builder()
            .status(StatusCode::INTERNAL_SERVER_ERROR)
            .body(Body::empty())
            .unwrap());
    }

    // 使用流式读取，避免一次性将大文件读入内存
    let stream = ReaderStream::new(file.take(chunk_size));

    let mut builder = Response::builder()
        .status(status_code)
        .header("Content-Type", content_type)
        .header("Content-Length", chunk_size.to_string())
        .header("Accept-Ranges", "bytes")
        .header("Access-Control-Allow-Origin", "*");

    // 仅在分段传输时附带 Content-Range
    if status_code == StatusCode::PARTIAL_CONTENT {
        builder = builder.header(
            "Content-Range",
            format!("bytes {}-{}/{}", start, end, file_size),
        );
    }

    Ok(builder.body(Body::wrap_stream(stream)).unwrap())
}

/// 解析 Range 头，返回 (start, end)
fn parse_range_header(range: Option<&str>, file_size: u64) -> Option<(u64, u64)> {
    let range = range?.trim().trim_start_matches("bytes=");
    let parts: Vec<&str> = range.split('-').collect();

    match (parts.get(0), parts.get(1)) {
        // bytes=START-END
        (Some(start), Some(end)) if !start.is_empty() && !end.is_empty() => {
            let s = start.parse().unwrap_or(0);
            let e = end.parse().unwrap_or(file_size.saturating_sub(1));
            if s <= e && s < file_size {
                Some((s, e.min(file_size - 1)))
            } else {
                None
            }
        }
        // bytes=START-
        (Some(start), Some(end)) if !start.is_empty() && end.is_empty() => {
            let s = start.parse().unwrap_or(0);
            if s < file_size {
                Some((s, file_size - 1))
            } else {
                None
            }
        }
        // bytes=-SUFFIX (最后 N 字节)
        (Some(start), Some(end)) if start.is_empty() && !end.is_empty() => {
            let len: u64 = end.parse().unwrap_or(0);
            if len == 0 {
                return None;
            }
            let s = file_size.saturating_sub(len);
            Some((s, file_size - 1))
        }
        _ => None,
    }
}
