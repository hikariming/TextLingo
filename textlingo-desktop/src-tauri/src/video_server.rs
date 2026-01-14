// 本地 HTTP 视频流服务器
// 使用 warp 框架提供视频文件，完美支持 Range 请求
// 这是解决 macOS WebKit 自定义协议视频播放问题的终极方案

use std::path::PathBuf;
use std::sync::Arc;
use warp::Filter;
use warp::http::{Response, StatusCode};
use warp::hyper::Body;
use tokio::fs::File;
use tokio::io::{AsyncReadExt, AsyncSeekExt};
use std::io::SeekFrom;

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
    } else if decoded_filename.ends_with(".epub") {
        "application/epub+zip"
    } else if decoded_filename.ends_with(".txt") {
        "text/plain; charset=utf-8"
    } else {
        "application/octet-stream"
    };
    
    // 处理 Range 请求
    if let Some(range) = range_header {
        // 解析 Range: bytes=start-end
        let range = range.trim_start_matches("bytes=");
        let parts: Vec<&str> = range.split('-').collect();
        
        let start: u64 = parts[0].parse().unwrap_or(0);
        let end: u64 = if parts.len() > 1 && !parts[1].is_empty() {
            parts[1].parse().unwrap_or(file_size - 1)
        } else {
            // 如果没有指定 end，返回一个合理的块大小（10MB，EPUB可能需要较大块）
            std::cmp::min(start + 10 * 1024 * 1024, file_size - 1)
        };
        
        let end = std::cmp::min(end, file_size - 1);
        
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
        
        // 读取指定范围的数据
        let mut buffer = vec![0u8; chunk_size as usize];
        if let Err(_) = file.read_exact(&mut buffer).await {
            return Ok(Response::builder()
                .status(StatusCode::INTERNAL_SERVER_ERROR)
                .body(Body::empty())
                .unwrap());
        }
        
        Ok(Response::builder()
            .status(StatusCode::PARTIAL_CONTENT)
            .header("Content-Type", content_type)
            .header("Content-Length", chunk_size.to_string())
            .header("Content-Range", format!("bytes {}-{}/{}", start, end, file_size))
            .header("Accept-Ranges", "bytes")
            .header("Access-Control-Allow-Origin", "*")
            .body(Body::from(buffer))
            .unwrap())
    } else {
        // 没有 Range 请求，返回整个文件
        let mut buffer = Vec::new();
        if let Err(_) = file.read_to_end(&mut buffer).await {
            return Ok(Response::builder()
                .status(StatusCode::INTERNAL_SERVER_ERROR)
                .body(Body::empty())
                .unwrap());
        }
        
        Ok(Response::builder()
            .status(StatusCode::OK)
            .header("Content-Type", content_type)
            .header("Content-Length", file_size.to_string())
            .header("Accept-Ranges", "bytes")
            .header("Access-Control-Allow-Origin", "*")
            .body(Body::from(buffer))
            .unwrap())
    }
}
