// Modules
mod ai_service;
mod commands;
mod storage;
mod types;
mod video_server;
mod youtube;

// Re-exports
use ai_service::AIServiceCache;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .manage(AIServiceCache::default())
        .invoke_handler(tauri::generate_handler![
            // App initialization
            commands::init_app,
            // Configuration
            commands::get_config,
            commands::save_config_cmd,
            commands::set_api_key,
            commands::save_model_config,
            commands::delete_model_config,
            commands::set_active_model_config,
            commands::get_active_model_config,
            // Articles
            commands::create_article,
            commands::resegment_article,
            commands::get_article,
            commands::list_articles_cmd,
            commands::update_article,
            commands::update_article_segment,
            commands::delete_article_cmd,
            commands::fetch_url_content,
            // AI operations
            commands::translate_text,
            commands::analyze_text,
            commands::chat_completion,
            commands::translate_article,
            commands::analyze_article,
            commands::segment_translate_explain_cmd,
            // 收藏夹命令
            commands::add_favorite_vocabulary_cmd,
            commands::list_favorite_vocabularies_cmd,
            commands::delete_favorite_vocabulary_cmd,
            commands::add_favorite_grammar_cmd,
            commands::list_favorite_grammars_cmd,
            commands::delete_favorite_grammar_cmd,
            // External
            commands::import_youtube_video_cmd,
        ])
        .setup(|app| {
            // Initialize app on startup
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Ensure app directories exist
                let _ = commands::init_app(app_handle.clone()).await;
                
                // 启动视频服务器
                let app_data_dir = app_handle.path().app_data_dir().unwrap();
                let videos_dir = app_data_dir.join("videos");
                if let Err(e) = video_server::start_video_server(videos_dir).await {
                    eprintln!("[VideoServer] Failed to start: {}", e);
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
