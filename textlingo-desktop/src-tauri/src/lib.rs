// Modules
mod ai_service;
mod commands;
mod plugin_manager;
mod storage;
mod subtitle_extraction;
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
        .plugin(tauri_plugin_dialog::init())
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
            commands::stream_chat_completion,
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
            commands::import_local_video_cmd,
            // 书籍导入
            commands::import_book_cmd,
            // 字幕提取
            commands::extract_subtitles_cmd,
            // 文件操作
            commands::write_text_file,
            // 删除操作
            commands::delete_article_subtitles_cmd,
            commands::delete_article_analysis_cmd,
            // PDF翻译
            commands::translate_pdf_document,
            commands::check_pdf_translation_files,
            commands::export_file_cmd,
            // 插件管理
            plugin_manager::list_plugins_cmd,
            plugin_manager::open_plugins_directory,
            plugin_manager::set_plugin_mode_cmd,
            plugin_manager::get_plugin_modes_cmd,
            // 插件自动安装
            plugin_manager::check_plugin_installed_cmd,
            plugin_manager::get_plugin_release_info_cmd,
            plugin_manager::install_plugin_cmd,
            // 书签管理
            commands::add_bookmark_cmd,
            commands::list_bookmarks_cmd,
            commands::list_bookmarks_for_book_cmd,
            commands::update_bookmark_cmd,
            commands::delete_bookmark_cmd,
        ])
        .setup(|app| {
            // Initialize app on startup
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Ensure app directories exist
                let _ = commands::init_app(app_handle.clone()).await;

                // 启动资源服务器 (视频 + 书籍)
                let app_data_dir = app_handle.path().app_data_dir().unwrap();
                if let Err(e) = video_server::start_resource_server(app_data_dir).await {
                    eprintln!("[ResourceServer] Failed to start: {}", e);
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
