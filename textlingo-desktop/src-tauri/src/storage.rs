use crate::types::AppConfig;
use serde_json;
use std::fs;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

const CONFIG_FILE: &str = "config.json";
const ARTICLES_DIR: &str = "articles";

pub fn get_app_data_dir(app_handle: &AppHandle) -> Result<PathBuf, String> {
    app_handle
        .path()
        .app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))
}

pub fn ensure_app_dirs(app_handle: &AppHandle) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let articles_dir = data_dir.join(ARTICLES_DIR);

    fs::create_dir_all(&articles_dir)
        .map_err(|e| format!("Failed to create articles directory: {}", e))?;

    Ok(())
}

pub fn save_config(app_handle: &AppHandle, config: &AppConfig) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let config_path = data_dir.join(CONFIG_FILE);

    let config_json = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config: {}", e))?;

    fs::write(config_path, config_json)
        .map_err(|e| format!("Failed to write config: {}", e))?;

    Ok(())
}

pub fn load_config(app_handle: &AppHandle) -> Result<Option<AppConfig>, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let config_path = data_dir.join(CONFIG_FILE);

    if !config_path.exists() {
        return Ok(None);
    }

    let config_content = fs::read_to_string(config_path)
        .map_err(|e| format!("Failed to read config: {}", e))?;

    let mut deserializer = serde_json::Deserializer::from_str(&config_content);
    let config: AppConfig = match serde::Deserialize::deserialize(&mut deserializer) {
        Ok(c) => c,
        Err(e) => {
            return Err(format!("FATAL_CONFIG_CORRUPTION: {}", e));
        }
    };

    Ok(Some(config))
}

pub fn save_article(
    app_handle: &AppHandle,
    article_id: &str,
    content: &str,
) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let article_path = data_dir.join(ARTICLES_DIR).join(article_id);

    fs::write(article_path, content)
        .map_err(|e| format!("Failed to save article: {}", e))?;

    Ok(())
}

pub fn load_article(app_handle: &AppHandle, article_id: &str) -> Result<String, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let article_path = data_dir.join(ARTICLES_DIR).join(article_id);

    if !article_path.exists() {
        return Err("Article not found".to_string());
    }

    fs::read_to_string(article_path)
        .map_err(|e| format!("Failed to read article: {}", e))
}

pub fn list_articles(app_handle: &AppHandle) -> Result<Vec<String>, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let articles_dir = data_dir.join(ARTICLES_DIR);

    if !articles_dir.exists() {
        return Ok(Vec::new());
    }

    let entries = fs::read_dir(articles_dir)
        .map_err(|e| format!("Failed to read articles directory: {}", e))?;

    let article_ids: Vec<String> = entries
        .filter_map(|entry| entry.ok())
        .filter(|entry| entry.path().is_file())
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();

    Ok(article_ids)
}

pub fn delete_article(app_handle: &AppHandle, article_id: &str) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let article_path = data_dir.join(ARTICLES_DIR).join(article_id);

    if article_path.exists() {
        fs::remove_file(article_path)
            .map_err(|e| format!("Failed to delete article: {}", e))?;
    }

    Ok(())
}

// ============================================================================
// Favorites Storage - 独立于文章存储，删除文章不会影响收藏
// ============================================================================

const FAVORITES_VOCAB_DIR: &str = "favorites/vocabulary";
const FAVORITES_GRAMMAR_DIR: &str = "favorites/grammar";

/// 确保收藏夹目录存在
pub fn ensure_favorites_dirs(app_handle: &AppHandle) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let vocab_dir = data_dir.join(FAVORITES_VOCAB_DIR);
    let grammar_dir = data_dir.join(FAVORITES_GRAMMAR_DIR);

    fs::create_dir_all(&vocab_dir)
        .map_err(|e| format!("Failed to create vocabulary favorites directory: {}", e))?;
    fs::create_dir_all(&grammar_dir)
        .map_err(|e| format!("Failed to create grammar favorites directory: {}", e))?;

    Ok(())
}

/// 保存单词收藏
pub fn save_favorite_vocabulary(
    app_handle: &AppHandle,
    id: &str,
    content: &str,
) -> Result<(), String> {
    ensure_favorites_dirs(app_handle)?;
    let data_dir = get_app_data_dir(app_handle)?;
    let path = data_dir.join(FAVORITES_VOCAB_DIR).join(id);

    fs::write(path, content)
        .map_err(|e| format!("Failed to save vocabulary favorite: {}", e))?;

    Ok(())
}

/// 加载单词收藏
pub fn load_favorite_vocabulary(app_handle: &AppHandle, id: &str) -> Result<String, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let path = data_dir.join(FAVORITES_VOCAB_DIR).join(id);

    if !path.exists() {
        return Err("Vocabulary favorite not found".to_string());
    }

    fs::read_to_string(path)
        .map_err(|e| format!("Failed to read vocabulary favorite: {}", e))
}

/// 列出所有单词收藏ID
pub fn list_favorite_vocabularies(app_handle: &AppHandle) -> Result<Vec<String>, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let dir = data_dir.join(FAVORITES_VOCAB_DIR);

    if !dir.exists() {
        return Ok(Vec::new());
    }

    let entries = fs::read_dir(dir)
        .map_err(|e| format!("Failed to read vocabulary favorites directory: {}", e))?;

    let ids: Vec<String> = entries
        .filter_map(|entry| entry.ok())
        .filter(|entry| entry.path().is_file())
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();

    Ok(ids)
}

/// 删除单词收藏
pub fn delete_favorite_vocabulary(app_handle: &AppHandle, id: &str) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let path = data_dir.join(FAVORITES_VOCAB_DIR).join(id);

    if path.exists() {
        fs::remove_file(path)
            .map_err(|e| format!("Failed to delete vocabulary favorite: {}", e))?;
    }

    Ok(())
}

/// 保存语法收藏
pub fn save_favorite_grammar(
    app_handle: &AppHandle,
    id: &str,
    content: &str,
) -> Result<(), String> {
    ensure_favorites_dirs(app_handle)?;
    let data_dir = get_app_data_dir(app_handle)?;
    let path = data_dir.join(FAVORITES_GRAMMAR_DIR).join(id);

    fs::write(path, content)
        .map_err(|e| format!("Failed to save grammar favorite: {}", e))?;

    Ok(())
}

/// 加载语法收藏
pub fn load_favorite_grammar(app_handle: &AppHandle, id: &str) -> Result<String, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let path = data_dir.join(FAVORITES_GRAMMAR_DIR).join(id);

    if !path.exists() {
        return Err("Grammar favorite not found".to_string());
    }

    fs::read_to_string(path)
        .map_err(|e| format!("Failed to read grammar favorite: {}", e))
}

/// 列出所有语法收藏ID
pub fn list_favorite_grammars(app_handle: &AppHandle) -> Result<Vec<String>, String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let dir = data_dir.join(FAVORITES_GRAMMAR_DIR);

    if !dir.exists() {
        return Ok(Vec::new());
    }

    let entries = fs::read_dir(dir)
        .map_err(|e| format!("Failed to read grammar favorites directory: {}", e))?;

    let ids: Vec<String> = entries
        .filter_map(|entry| entry.ok())
        .filter(|entry| entry.path().is_file())
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();

    Ok(ids)
}

/// 删除语法收藏
pub fn delete_favorite_grammar(app_handle: &AppHandle, id: &str) -> Result<(), String> {
    let data_dir = get_app_data_dir(app_handle)?;
    let path = data_dir.join(FAVORITES_GRAMMAR_DIR).join(id);

    if path.exists() {
        fs::remove_file(path)
            .map_err(|e| format!("Failed to delete grammar favorite: {}", e))?;
    }

    Ok(())
}

