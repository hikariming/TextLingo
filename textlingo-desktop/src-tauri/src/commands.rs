use crate::ai_service::{get_ai_service, get_or_create_ai_service, AIServiceCache};
use crate::storage::{
    delete_article,
    delete_bookmark,
    delete_favorite_grammar,
    delete_favorite_vocabulary,
    delete_word_pack,
    ensure_app_dirs,
    ensure_favorites_dirs,
    list_articles,
    list_bookmarks,
    list_bookmarks_for_book,
    list_favorite_grammars,
    list_favorite_vocabularies,
    list_word_packs,
    load_article,
    load_bookmark,
    load_config,
    load_favorite_grammar,
    load_favorite_vocabulary,
    load_word_pack,
    save_article,
    // 书签存储函数
    save_bookmark,
    save_config,
    save_favorite_grammar,
    // 收藏夹存储函数
    save_favorite_vocabulary,
    save_word_pack,
};
use crate::types::{
    AnalysisRequest, AnalysisResponse, AnalysisType, Article, ArticleSegment, Bookmark,
    ChatRequest, ChatResponse, FavoriteGrammar, FavoriteVocabulary, ModelConfig,
    TranslationRequest, TranslationResponse, WordPack,
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::PathBuf;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager, State};
use uuid::Uuid;

pub type AppState<'a> = State<'a, AIServiceCache>;

// Helper function to create segments from content
// 按句子分隔内容（使用.或。作为分隔符），并标记是否需要换行
fn create_segments_from_content(article_id: &str, content: &str) -> Vec<ArticleSegment> {
    let mut segments = Vec::new();
    let mut order = 0;

    // 首先按段落分割（双换行或单换行）
    let paragraphs: Vec<&str> = content
        .split('\n')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect();

    for paragraph in paragraphs {
        // 将段落按句子分割（使用 . 或 。 作为分隔符）
        // 使用正则表达式保留分隔符
        let sentences = split_into_sentences(paragraph);

        for (sentence_index, sentence) in sentences.iter().enumerate() {
            let text = sentence.trim();
            if text.is_empty() {
                continue;
            }

            segments.push(ArticleSegment {
                id: Uuid::new_v4().to_string(),
                article_id: article_id.to_string(),
                order,
                text: text.to_string(),
                reading_text: None,
                translation: None,
                explanation: None,
                start_time: None,
                end_time: None,
                created_at: chrono::Utc::now().to_rfc3339(),
                // 段落的第一个句子需要换行显示，后续句子紧跟前一个显示
                is_new_paragraph: sentence_index == 0,
            });
            order += 1;
        }
    }

    segments
}

/// 将段落拆分成句子，保留句末标点
/// 支持英文句号(.)、中文句号(。)、问号(?/？)、感叹号(!/！)
fn split_into_sentences(text: &str) -> Vec<String> {
    let mut sentences = Vec::new();
    let mut current = String::new();
    let chars: Vec<char> = text.chars().collect();

    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        current.push(c);

        // 检查是否是句子结束符
        let is_sentence_end = c == '。'
            || c == '？'
            || c == '！'
            || (c == '.' && !is_abbreviation(&chars, i))
            || c == '?'
            || c == '!';

        if is_sentence_end {
            // 处理引号闭合情况：如 ... said." 这种情况
            // 向后看，如果下一个字符是引号，把它也加进来
            if i + 1 < chars.len() {
                let next = chars[i + 1];
                if next == '"'
                    || next == '"'
                    || next == '\''
                    || next == '\u{2019}'
                    || next == ')'
                    || next == '）'
                {
                    i += 1;
                    current.push(next);
                }
            }

            let trimmed = current.trim().to_string();
            if !trimmed.is_empty() {
                sentences.push(trimmed);
            }
            current = String::new();
        }

        i += 1;
    }

    // 处理剩余内容（没有句号结尾的情况）
    let trimmed = current.trim().to_string();
    if !trimmed.is_empty() {
        sentences.push(trimmed);
    }

    // 如果整个段落没有分割成功（没有找到分隔符），返回整段
    if sentences.is_empty() && !text.trim().is_empty() {
        sentences.push(text.trim().to_string());
    }

    sentences
}

/// 检查句点是否是缩写的一部分（如 Mr. Mrs. Dr. U.S. 等）
/// 简单的启发式规则
fn is_abbreviation(chars: &[char], pos: usize) -> bool {
    // 如果句点后面紧跟字母，可能是缩写 (如 U.S.A)
    if pos + 1 < chars.len() && chars[pos + 1].is_alphabetic() {
        return true;
    }

    // 检查句点前是否是常见缩写
    // 向前查找单词
    let mut word = String::new();
    let mut j = pos as i32 - 1;
    while j >= 0 && chars[j as usize].is_alphabetic() {
        word.insert(0, chars[j as usize]);
        j -= 1;
    }

    let word_lower = word.to_lowercase();
    let abbreviations = [
        "mr", "mrs", "ms", "dr", "jr", "sr", "vs", "etc", "inc", "ltd", "no", "st", "ave", "rd",
    ];

    if abbreviations.contains(&word_lower.as_str()) {
        return true;
    }

    // 单字母后跟句点通常是缩写（如 A. B. C.）
    if word.len() == 1 && word.chars().next().unwrap().is_uppercase() {
        return true;
    }

    false
}

const DEFAULT_UNGROUPED_PACK_ID: &str = "system-ungrouped";
const DEFAULT_UNGROUPED_PACK_NAME: &str = "未分组";

#[derive(Debug, Clone, Serialize, Deserialize)]
struct WordPackExportMeta {
    name: String,
    #[serde(default)]
    description: Option<String>,
    #[serde(default)]
    cover_url: Option<String>,
    #[serde(default)]
    author: Option<String>,
    #[serde(default)]
    language_from: Option<String>,
    #[serde(default)]
    language_to: Option<String>,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct WordPackExportEntry {
    word: String,
    meaning: String,
    #[serde(default)]
    usage: Option<String>,
    #[serde(default)]
    example: Option<String>,
    #[serde(default)]
    reading: Option<String>,
    #[serde(default)]
    explanation: Option<String>,
    #[serde(default)]
    tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct WordPackExportFile {
    schema_version: String,
    pack: WordPackExportMeta,
    entries: Vec<WordPackExportEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportWordPackResult {
    pub file_name: String,
    pub json_content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportWordPackResult {
    pub created_pack_id: String,
    pub total: usize,
    pub imported: usize,
    pub skipped: usize,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SrsUpdateResult {
    pub srs_state: String,
    pub repetitions: i32,
    pub interval_days: i32,
    pub ease_factor: f64,
    pub due_date: String,
}

fn normalize_word(word: &str) -> String {
    word.trim().to_lowercase()
}

fn parse_local_date(date_local: &str) -> Result<chrono::NaiveDate, String> {
    chrono::NaiveDate::parse_from_str(date_local, "%Y-%m-%d")
        .map_err(|_| format!("Invalid local date format: {}", date_local))
}

fn today_local_date() -> chrono::NaiveDate {
    chrono::Local::now().date_naive()
}

fn ensure_default_word_pack(app_handle: &AppHandle) -> Result<WordPack, String> {
    ensure_favorites_dirs(app_handle)?;
    let now = chrono::Utc::now().to_rfc3339();
    let default_pack = WordPack {
        id: DEFAULT_UNGROUPED_PACK_ID.to_string(),
        name: DEFAULT_UNGROUPED_PACK_NAME.to_string(),
        description: Some("系统默认合集".to_string()),
        cover_url: None,
        author: Some("OpenKoto".to_string()),
        language_from: None,
        language_to: None,
        tags: vec!["system".to_string()],
        version: Some("1.0.0".to_string()),
        created_at: now.clone(),
        updated_at: now,
        is_system: true,
    };

    let existing = load_word_pack(app_handle, DEFAULT_UNGROUPED_PACK_ID)
        .ok()
        .and_then(|json| serde_json::from_str::<WordPack>(&json).ok());

    if let Some(pack) = existing {
        return Ok(pack);
    }

    let json = serde_json::to_string(&default_pack)
        .map_err(|e| format!("Failed to serialize default pack: {}", e))?;
    save_word_pack(app_handle, &default_pack.id, &json)?;
    Ok(default_pack)
}

fn load_all_word_packs(app_handle: &AppHandle) -> Result<Vec<WordPack>, String> {
    let ids = list_word_packs(app_handle)?;
    let mut packs = Vec::new();

    for id in ids {
        if let Ok(json) = load_word_pack(app_handle, &id) {
            if let Ok(pack) = serde_json::from_str::<WordPack>(&json) {
                packs.push(pack);
            }
        }
    }

    packs.sort_by(|a, b| a.created_at.cmp(&b.created_at));
    Ok(packs)
}

fn load_all_favorite_vocabularies_internal(
    app_handle: &AppHandle,
) -> Result<Vec<FavoriteVocabulary>, String> {
    let ids = list_favorite_vocabularies(app_handle)?;
    let mut favorites = Vec::new();

    for id in ids {
        if let Ok(json) = load_favorite_vocabulary(app_handle, &id) {
            if let Ok(favorite) = serde_json::from_str::<FavoriteVocabulary>(&json) {
                favorites.push(favorite);
            }
        }
    }

    Ok(favorites)
}

fn persist_favorite_vocabulary(
    app_handle: &AppHandle,
    favorite: &FavoriteVocabulary,
) -> Result<(), String> {
    let json = serde_json::to_string(favorite)
        .map_err(|e| format!("Failed to serialize favorite vocabulary: {}", e))?;
    save_favorite_vocabulary(app_handle, &favorite.id, &json)
}

fn sanitize_pack_ids(pack_ids: Option<Vec<String>>) -> Vec<String> {
    let mut seen = HashSet::new();
    pack_ids
        .unwrap_or_default()
        .into_iter()
        .map(|id| id.trim().to_string())
        .filter(|id| !id.is_empty())
        .filter(|id| seen.insert(id.clone()))
        .collect()
}

fn filter_existing_pack_ids(
    pack_ids: Vec<String>,
    existing_pack_ids: &HashSet<String>,
    default_pack_id: &str,
) -> Vec<String> {
    let mut result: Vec<String> = pack_ids
        .into_iter()
        .filter(|id| existing_pack_ids.contains(id))
        .collect();

    if result.is_empty() {
        result.push(default_pack_id.to_string());
    }

    result
}

fn sort_by_due_then_last_review(
    a: &FavoriteVocabulary,
    b: &FavoriteVocabulary,
) -> std::cmp::Ordering {
    match a.due_date.cmp(&b.due_date) {
        std::cmp::Ordering::Equal => a.last_reviewed_at.cmp(&b.last_reviewed_at),
        ord => ord,
    }
}

fn is_due_on_or_before(due_date: &str, target_date: chrono::NaiveDate) -> bool {
    parse_local_date(due_date)
        .map(|due| due <= target_date)
        .unwrap_or(true)
}

fn sanitize_file_name(name: &str) -> String {
    let sanitized = name
        .chars()
        .map(|c| match c {
            '/' | '\\' | '?' | '%' | '*' | ':' | '|' | '"' | '<' | '>' => '-',
            _ => c,
        })
        .collect::<String>()
        .trim()
        .to_string();

    if sanitized.is_empty() {
        "openkoto_word_pack".to_string()
    } else {
        sanitized
    }
}

pub fn calculate_sm2_update(
    repetitions: i32,
    interval_days: i32,
    ease_factor: f64,
    grade: &str,
    review_date: chrono::NaiveDate,
) -> Result<SrsUpdateResult, String> {
    let q = match grade {
        "unknown" => 2.0,
        "uncertain" => 3.0,
        "known" => 5.0,
        _ => return Err("Invalid grade, expected unknown|uncertain|known".to_string()),
    };

    let mut next_repetitions = repetitions.max(0);
    let mut next_interval_days = interval_days.max(0);
    let mut next_ease_factor = if ease_factor < 1.3 { 2.5 } else { ease_factor };
    let next_state;

    if q < 3.0 {
        next_repetitions = 0;
        next_interval_days = 1;
        next_state = "learning".to_string();
    } else {
        if next_repetitions == 0 {
            next_interval_days = 1;
        } else if next_repetitions == 1 {
            next_interval_days = 6;
        } else {
            next_interval_days = ((next_interval_days as f64) * next_ease_factor).round() as i32;
        }
        next_repetitions += 1;
        next_state = "review".to_string();
    }

    next_ease_factor = (next_ease_factor + (0.1 - (5.0 - q) * (0.08 + (5.0 - q) * 0.02))).max(1.3);
    let due_date = (review_date + chrono::Duration::days(next_interval_days as i64))
        .format("%Y-%m-%d")
        .to_string();

    Ok(SrsUpdateResult {
        srs_state: next_state,
        repetitions: next_repetitions,
        interval_days: next_interval_days,
        ease_factor: next_ease_factor,
        due_date,
    })
}

pub fn build_due_vocabulary_queue(
    mut all: Vec<FavoriteVocabulary>,
    pack_id: &str,
    date_local: &str,
    new_limit: i32,
    review_limit: i32,
) -> Result<Vec<FavoriteVocabulary>, String> {
    let target_date = parse_local_date(date_local)?;
    let new_limit = new_limit.max(0) as usize;
    let review_limit = review_limit.max(0) as usize;

    if pack_id != "all" {
        all.retain(|fav| fav.pack_ids.iter().any(|id| id == pack_id));
    }
    all.retain(|fav| is_due_on_or_before(&fav.due_date, target_date));

    let (mut new_learning, mut review): (Vec<_>, Vec<_>) = all
        .into_iter()
        .partition(|fav| fav.srs_state == "new" || fav.srs_state == "learning");

    new_learning.sort_by(sort_by_due_then_last_review);
    review.sort_by(sort_by_due_then_last_review);

    let mut queue = Vec::new();
    queue.extend(new_learning.into_iter().take(new_limit));
    queue.extend(review.into_iter().take(review_limit));
    Ok(queue)
}

fn migrate_favorite_vocabularies(app_handle: &AppHandle) -> Result<(), String> {
    let default_pack = ensure_default_word_pack(app_handle)?;
    let ids = list_favorite_vocabularies(app_handle)?;
    let today = today_local_date().format("%Y-%m-%d").to_string();

    for id in ids {
        let json = match load_favorite_vocabulary(app_handle, &id) {
            Ok(content) => content,
            Err(_) => continue,
        };

        let mut favorite = match serde_json::from_str::<FavoriteVocabulary>(&json) {
            Ok(item) => item,
            Err(_) => continue,
        };

        let mut changed = false;

        if favorite.pack_ids.is_empty() {
            favorite.pack_ids = vec![default_pack.id.clone()];
            changed = true;
        } else {
            let dedup = sanitize_pack_ids(Some(favorite.pack_ids.clone()));
            if dedup != favorite.pack_ids {
                favorite.pack_ids = dedup;
                changed = true;
            }
        }

        if favorite.srs_state != "new"
            && favorite.srs_state != "learning"
            && favorite.srs_state != "review"
        {
            favorite.srs_state = "new".to_string();
            changed = true;
        }

        if favorite.ease_factor < 1.3 {
            favorite.ease_factor = 2.5;
            changed = true;
        }

        if favorite.due_date.trim().is_empty() {
            favorite.due_date = today.clone();
            changed = true;
        } else if parse_local_date(&favorite.due_date).is_err() {
            favorite.due_date = today.clone();
            changed = true;
        }

        if favorite.interval_days < 0 {
            favorite.interval_days = 0;
            changed = true;
        }

        if favorite.repetitions < 0 {
            favorite.repetitions = 0;
            changed = true;
        }

        if favorite.review_count < 0 {
            favorite.review_count = 0;
            changed = true;
        }

        if changed {
            persist_favorite_vocabulary(app_handle, &favorite)?;
        }
    }

    Ok(())
}

// Initialize the app (ensure directories exist)
#[tauri::command]
pub async fn init_app(app_handle: AppHandle) -> Result<String, String> {
    ensure_app_dirs(&app_handle)?;
    ensure_favorites_dirs(&app_handle)?;
    let _ = ensure_default_word_pack(&app_handle)?;
    migrate_favorite_vocabularies(&app_handle)?;
    Ok("App initialized successfully".to_string())
}

// Configuration commands
#[tauri::command]
pub async fn get_config(
    app_handle: AppHandle,
    state: AppState<'_>,
) -> Result<Option<crate::types::AppConfig>, String> {
    let config = load_config(&app_handle)?;

    // If we have a config and an active model, ensure AI service is initialized
    if let Some(ref app_config) = config {
        if let Some(active_id) = &app_config.active_model_id {
            if let Some(model_config) = app_config.get_config(active_id) {
                // We don't fail here if init fails, just log it or ignore
                // real errors will bubble up when user tries to use AI features
                let _ = get_or_create_ai_service(
                    &state,
                    model_config.api_key.clone(),
                    model_config.api_provider.clone(),
                    model_config.model.clone(),
                    model_config.base_url.clone(),
                )
                .await;
            }
        }
    }

    Ok(config)
}

#[tauri::command]
pub async fn save_config_cmd(
    app_handle: AppHandle,
    config: crate::types::AppConfig,
) -> Result<String, String> {
    save_config(&app_handle, &config)?;
    Ok("Configuration saved".to_string())
}

/// Add or update a model configuration
#[tauri::command]
pub async fn save_model_config(
    app_handle: AppHandle,
    state: AppState<'_>,
    config: ModelConfig,
) -> Result<ModelConfig, String> {
    let mut app_config = load_config(&app_handle)?.unwrap_or_default();

    // Check if this is an update or new config
    let existing_index = app_config
        .model_configs
        .iter()
        .position(|c| c.id == config.id);

    if let Some(idx) = existing_index {
        // Update existing config
        app_config.model_configs[idx] = config.clone();
    } else {
        // Add new config
        app_config.model_configs.push(config.clone());
    }

    // Set as active if it's the first one or marked as default
    if app_config.model_configs.len() == 1 || config.is_default {
        app_config.active_model_id = Some(config.id.clone());
        // Unset other defaults
        for c in &mut app_config.model_configs {
            if c.id != config.id {
                c.is_default = false;
            }
        }
    }

    save_config(&app_handle, &app_config)?;

    // Update AI service cache if this is the active config
    if app_config.active_model_id.as_ref() == Some(&config.id) {
        get_or_create_ai_service(
            &state,
            config.api_key.clone(),
            config.api_provider.clone(),
            config.model.clone(),
            config.base_url.clone(),
        )
        .await?;
    }

    Ok(config)
}

/// Delete a model configuration
#[tauri::command]
pub async fn delete_model_config(app_handle: AppHandle, config_id: String) -> Result<(), String> {
    let mut app_config = load_config(&app_handle)?.unwrap_or_default();

    // Remove the config
    let original_len = app_config.model_configs.len();
    app_config.model_configs.retain(|c| c.id != config_id);

    if app_config.model_configs.len() == original_len {
        return Err("Configuration not found".to_string());
    }

    // If we deleted the active config, set a new active one
    if app_config.active_model_id.as_ref() == Some(&config_id) {
        app_config.active_model_id = app_config.model_configs.first().map(|c| c.id.clone());
    }

    save_config(&app_handle, &app_config)?;
    Ok(())
}

/// Set the active model configuration
#[tauri::command]
pub async fn set_active_model_config(
    app_handle: AppHandle,
    state: AppState<'_>,
    config_id: String,
) -> Result<ModelConfig, String> {
    let mut app_config = load_config(&app_handle)?.unwrap_or_default();

    let config = app_config
        .get_config(&config_id)
        .ok_or("Configuration not found")?
        .clone();

    app_config.active_model_id = Some(config_id.clone());

    save_config(&app_handle, &app_config)?;

    // Update AI service cache
    get_or_create_ai_service(
        &state,
        config.api_key.clone(),
        config.api_provider.clone(),
        config.model.clone(),
        config.base_url.clone(),
    )
    .await?;

    Ok(config)
}

/// Get the active model configuration
#[tauri::command]
pub async fn get_active_model_config(app_handle: AppHandle) -> Result<Option<ModelConfig>, String> {
    let app_config = load_config(&app_handle)?.unwrap_or_default();
    Ok(app_config.get_active_config().cloned())
}

/// Legacy command for backward compatibility - redirects to new model config system
#[tauri::command]
pub async fn set_api_key(
    app_handle: AppHandle,
    state: AppState<'_>,
    api_key: String,
    provider: String,
    model: String,
) -> Result<String, String> {
    let mut app_config = load_config(&app_handle)?.unwrap_or_default();

    // Create a default config name
    let config_name = format!("{} - {}", provider, model);

    // Check if a config with same provider/model already exists
    let existing = app_config
        .model_configs
        .iter()
        .find(|c| c.api_provider == provider && c.model == model);

    let config = if let Some(existing) = existing {
        // Update existing
        ModelConfig {
            api_key,
            ..existing.clone()
        }
    } else {
        // Create new
        ModelConfig::new(config_name, api_key, provider, model)
    };

    let config_id = config.id.clone();

    // Add or update
    let existing_index = app_config
        .model_configs
        .iter()
        .position(|c| c.id == config.id);
    if let Some(idx) = existing_index {
        app_config.model_configs[idx] = config.clone();
    } else {
        app_config.model_configs.push(config.clone());
    }

    // Set as active
    app_config.active_model_id = Some(config_id.clone());

    save_config(&app_handle, &app_config)?;

    // Update AI service cache
    get_or_create_ai_service(
        &state,
        config.api_key.clone(),
        config.api_provider.clone(),
        config.model.clone(),
        config.base_url.clone(),
    )
    .await?;

    Ok("API key saved successfully".to_string())
}

// Article commands
#[tauri::command]
pub async fn create_article(
    app_handle: AppHandle,
    title: String,
    content: String,
    source_url: Option<String>,
) -> Result<Article, String> {
    let id = Uuid::new_v4().to_string();
    let created_at = chrono::Utc::now().to_rfc3339();

    let segments = create_segments_from_content(&id, &content);

    let article = Article {
        id: id.clone(),
        title: title.clone(),
        content: content.clone(),
        source_type: Some("article".to_string()),
        source_url: source_url.clone(),
        media_path: None,
        book_path: None,
        book_type: None,
        created_at: created_at.clone(),
        translated: false,
        segments,
    };

    // Save article metadata and content
    let article_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &id, &article_json)?;

    Ok(article)
}

#[tauri::command]
pub async fn resegment_article(
    app_handle: AppHandle,
    article_id: String,
) -> Result<Article, String> {
    let article_json = load_article(&app_handle, &article_id)?;
    let mut article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;

    article.segments = create_segments_from_content(&article.id, &article.content);

    let updated_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &article.id, &updated_json)?;

    Ok(article)
}

#[tauri::command]
pub async fn get_article(app_handle: AppHandle, id: String) -> Result<Article, String> {
    let article_json = load_article(&app_handle, &id)?;
    let article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;
    Ok(article)
}

#[tauri::command]
pub async fn list_articles_cmd(app_handle: AppHandle) -> Result<Vec<Article>, String> {
    let article_ids = list_articles(&app_handle)?;

    let mut articles = Vec::new();
    for id in article_ids {
        if let Ok(article_json) = load_article(&app_handle, &id) {
            if let Ok(article) = serde_json::from_str::<Article>(&article_json) {
                articles.push(article);
            }
        }
    }

    // Sort by created_at (newest first)
    articles.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(articles)
}

#[tauri::command]
pub async fn update_article(
    app_handle: AppHandle,
    id: String,
    title: Option<String>,
    content: Option<String>,
    source_url: Option<String>,
    translated: Option<bool>,
) -> Result<Article, String> {
    let article_json = load_article(&app_handle, &id)?;
    let mut article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;

    if let Some(t) = title {
        article.title = t;
    }
    if let Some(c) = content {
        article.content = c;
    }
    if let Some(s) = source_url {
        article.source_url = Some(s);
    }
    if let Some(t) = translated {
        article.translated = t;
    }

    let updated_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &id, &updated_json)?;

    Ok(article)
}

#[tauri::command]
pub async fn delete_article_cmd(app_handle: AppHandle, id: String) -> Result<(), String> {
    delete_article(&app_handle, &id)?;
    Ok(())
}

#[tauri::command]
pub async fn update_article_segment(
    app_handle: AppHandle,
    article_id: String,
    segment_id: String,
    explanation: Option<crate::types::SegmentExplanation>,
    reading: Option<String>,
    translation: Option<String>,
) -> Result<Article, String> {
    let article_json = load_article(&app_handle, &article_id)?;
    let mut article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;

    if let Some(segment) = article.segments.iter_mut().find(|s| s.id == segment_id) {
        if let Some(exp) = explanation {
            segment.explanation = Some(exp);
        }
        if let Some(read) = reading {
            segment.reading_text = Some(read);
        }
        if let Some(trans) = translation {
            segment.translation = Some(trans);
        }
    } else {
        return Err("Segment not found".to_string());
    }

    let updated_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &article_id, &updated_json)?;

    Ok(article)
}

// AI commands
#[tauri::command]
pub async fn translate_text(
    state: AppState<'_>,
    request: TranslationRequest,
) -> Result<TranslationResponse, String> {
    let ai_service = get_ai_service(&state).await?;
    ai_service.translate(request).await
}

#[tauri::command]
pub async fn analyze_text(
    state: AppState<'_>,
    request: AnalysisRequest,
) -> Result<AnalysisResponse, String> {
    let ai_service = get_ai_service(&state).await?;
    ai_service.analyze(request).await
}

#[tauri::command]
pub async fn chat_completion(
    state: AppState<'_>,
    request: ChatRequest,
) -> Result<ChatResponse, String> {
    let ai_service = get_ai_service(&state).await?;
    ai_service.chat(request).await
}

#[tauri::command]
pub async fn stream_chat_completion(
    app_handle: AppHandle,
    state: AppState<'_>,
    request: ChatRequest,
    event_id: String,
) -> Result<String, String> {
    let ai_service = get_ai_service(&state).await?;

    // Create a callback that emits events to the frontend
    let app_handle_clone = app_handle.clone();
    let event_name = format!("chat-stream://{}", event_id);

    ai_service
        .stream_chat(request, move |chunk| {
            // Emit the chunk to the frontend
            // We ignore errors here as we can't do much if emission fails
            let _ = app_handle_clone.emit(&event_name, chunk);
        })
        .await
}

#[tauri::command]
pub async fn segment_translate_explain_cmd(
    state: AppState<'_>,
    text: String,
    target_language: String,
) -> Result<crate::types::SegmentExplanation, String> {
    let ai_service = get_ai_service(&state).await?;
    ai_service
        .segment_translate_explain(text, target_language)
        .await
}

#[tauri::command]
pub async fn translate_article(
    app_handle: AppHandle,
    state: AppState<'_>,
    article_id: String,
    target_language: String,
) -> Result<Article, String> {
    let mut article = get_article(app_handle.clone(), article_id.clone()).await?;

    // Ensure segments exist
    if article.segments.is_empty() {
        article.segments = create_segments_from_content(&article.id, &article.content);
    }

    // 收集需要翻译的段落（没有翻译的）
    let untranslated: Vec<(String, String)> = article
        .segments
        .iter()
        .filter(|s| s.translation.is_none())
        .map(|s| (s.id.clone(), s.text.clone()))
        .collect();

    if !untranslated.is_empty() {
        let ai_service = get_ai_service(&state).await?;

        // 批量翻译（每批最多30条）
        const BATCH_SIZE: usize = 30;
        let total_count = untranslated.len();
        let total_chunks = (total_count + BATCH_SIZE - 1) / BATCH_SIZE;

        println!(
            "[Article] Starting quick translation for article: {}, items: {}",
            article_id, total_count
        );

        for (i, chunk) in untranslated.chunks(BATCH_SIZE).enumerate() {
            println!(
                "[Article] Translating chunk {}/{} ({} items)...",
                i + 1,
                total_chunks,
                chunk.len()
            );
            let batch_items: Vec<(String, String)> = chunk.to_vec();

            match ai_service
                .batch_translate(batch_items, &target_language)
                .await
            {
                Ok(translations) => {
                    // 将翻译结果写回对应的 segment
                    for (id, translation) in translations {
                        if let Some(seg) = article.segments.iter_mut().find(|s| s.id == id) {
                            seg.translation = Some(translation);
                        }
                    }
                    println!(
                        "[Article] Chunk {}/{} completed successfully",
                        i + 1,
                        total_chunks
                    );

                    // Emit progress event
                    let progress = serde_json::json!({
                        "current": (i + 1) * BATCH_SIZE,
                        "total": total_count,
                        "message": format!("Translating chunk {}/{}", i + 1, total_chunks)
                    });
                    let _ = app_handle
                        .emit(&format!("translation-progress://{}", article_id), progress);
                }
                Err(e) => {
                    // 批量翻译失败，记录错误但继续
                    eprintln!(
                        "[Article] Batch translation error in chunk {}/{}: {}",
                        i + 1,
                        total_chunks,
                        e
                    );
                }
            }
        }
    }

    // Emit complete event
    let _ = app_handle.emit(
        &format!("translation-progress://{}", article_id),
        serde_json::json!({
            "current": untranslated.len(),
            "total": untranslated.len(),
            "message": "Translation completed"
        }),
    );

    println!(
        "[Article] Quick translation completed for article: {}",
        article_id
    );
    article.translated = true;

    let article_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &article_id, &article_json)?;

    Ok(article)
}

#[tauri::command]
pub async fn analyze_article(
    app_handle: AppHandle,
    state: AppState<'_>,
    article_id: String,
    analysis_type: String,
) -> Result<String, String> {
    let article = get_article(app_handle.clone(), article_id.clone()).await?;

    let analysis_type = match analysis_type.as_str() {
        "summary" => AnalysisType::Summary,
        "key_points" => AnalysisType::KeyPoints,
        "vocabulary" => AnalysisType::Vocabulary,
        "grammar" => AnalysisType::Grammar,
        "full" => AnalysisType::FullAnalysis,
        _ => return Err("Invalid analysis type".to_string()),
    };

    let request = AnalysisRequest {
        text: article.content,
        analysis_type,
    };

    let response = analyze_text(state, request).await?;
    Ok(response.result)
}

// Return type for fetch_url_content
#[derive(serde::Serialize)]
pub struct FetchedContent {
    pub title: String,
    pub content: String,
}

// Fetch content from a URL
#[tauri::command]
pub async fn fetch_url_content(url: String) -> Result<FetchedContent, String> {
    // Validate URL
    let parsed_url = url::Url::parse(&url).map_err(|_| "Invalid URL format".to_string())?;

    // Only allow http/https
    if parsed_url.scheme() != "http" && parsed_url.scheme() != "https" {
        return Err("Only HTTP and HTTPS URLs are supported".to_string());
    }

    // Create HTTP client with timeout
    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    // Fetch the page with better headers to avoid blocking
    let response = client
        .get(&url)
        .header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
        .header("Accept-Language", "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7")
        .send()
        .await
        .map_err(|e| format!("Failed to fetch URL: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("HTTP error: {}", response.status()));
    }

    // Get HTML content
    // Note: readability prefers a "Cursor" or string. We'll get text first.
    let html = response
        .text()
        .await
        .map_err(|e| format!("Failed to read response: {}", e))?;

    // Pre-process HTML to handle common issues (optional)
    // For now, feed directly to readability.

    // Extract content using readability
    // This removes ads, sidebars, navigation, and JS.
    let mut cursor = std::io::Cursor::new(html.as_bytes());
    let mut title = String::new();
    let mut content = String::new();

    // Try readability first
    if let Ok(extracted) =
        readability::extractor::extract(&mut cursor, &url::Url::parse(&url).unwrap())
    {
        title = extracted.title;
        content = html_to_text_preserving_layout(&extracted.content);
    }

    // Check if we got meaningful content. If not, try fallback selectors.
    // Uta-net returns very short content (e.g. "Voting thanks") via readability.
    if content.trim().len() < 200 {
        if let Some(fallback_content) = try_fallback_extraction(&html) {
            // If fallback found something substantial, use it
            if fallback_content.len() > content.len() {
                content = html_to_text_preserving_layout(&fallback_content);
                // If title was missing, try to get it again or keep old one
                if title.is_empty() {
                    title = extract_title_from_html(&html, &url);
                }
            }
        }
    }

    // Final check
    if content.trim().len() < 10 {
        if content.trim().is_empty() {
            return Err("Could not extract meaningful content. The page might be empty or require JavaScript interaction that is not supported.".to_string());
        }
    }

    // If title is still empty
    if title.is_empty() {
        title = extract_title_from_html(&html, &url);
    }

    Ok(FetchedContent { title, content })
}

/// Fallback extraction using CSS selectors for known difficult sites
fn try_fallback_extraction(html: &str) -> Option<String> {
    use scraper::{Html, Selector};

    let document = Html::parse_document(html);

    // List of selectors to try, in order of preference
    // #kashi_area: Uta-net
    // .lyrics_box: common lyrics class
    // #lyrics: common lyrics id
    let selectors = vec![
        "#kashi_area",
        "div[itemprop='text']", // Generic schema.org text
        ".lyrics",
        "#lyrics",
        ".post-content",
        "article",
        "main",
    ];

    for selector_str in selectors {
        if let Ok(selector) = Selector::parse(selector_str) {
            if let Some(element) = document.select(&selector).next() {
                let html_content = element.html();
                // Simple heuristic: must be at least somewhat long
                if html_content.len() > 100 {
                    return Some(html_content);
                }
            }
        }
    }

    None
}

/// Convert HTML to text, preserving significant layout (newlines)
/// Ideal for lyrics, poems, and clean articles.
fn html_to_text_preserving_layout(html: &str) -> String {
    use regex::Regex;

    // 1. Normalize newlines in source to spaces (browser behavior), we will re-add them based on tags.
    let normalized = html.replace("\r", " ").replace("\n", " ");

    // 2. Replace block tags with sentinel newlines
    // <br>, <br/> -> \n
    // <p>, <div>, <li>, <h1>-<h6>, <blockquote>, <pre> -> \n\n (surround with breaks)
    // </tr> -> \n (table rows)
    let re_br = Regex::new(r"(?i)<br\s*/?>").unwrap();
    let with_br = re_br.replace_all(&normalized, "\n");

    let re_block_start = Regex::new(r"(?i)<(p|div|h[1-6]|li|blockquote|pre|tr)[^>]*>").unwrap();
    let with_block_start = re_block_start.replace_all(&with_br, "\n"); // Add newline before block

    let re_block_end = Regex::new(r"(?i)</(p|div|h[1-6]|li|blockquote|pre|tr)>").unwrap();
    let with_block_end = re_block_end.replace_all(&with_block_start, "\n\n"); // Add double newline after block

    // 3. Strip all other tags
    let re_tags = Regex::new(r"<[^>]*>").unwrap();
    let stripped = re_tags.replace_all(&with_block_end, "");

    // 4. Decode HTML entities
    let decoded = html_escape::decode_html_entities(&stripped);

    // 5. Clean up whitespace
    // Split by newline, trim each line, filter empty lines if they are excessive (more than 2)
    // But for lyrics, we want to keep single empty lines (stanza breaks).
    let lines: Vec<&str> = decoded.lines().collect();
    let mut clean_lines = Vec::new();
    let mut empty_count = 0;

    for line in lines {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            empty_count += 1;
            // Allow up to 2 consecutive empty lines (paragraph break)
            if empty_count <= 2 {
                clean_lines.push("");
            }
        } else {
            empty_count = 0;
            clean_lines.push(trimmed);
        }
    }

    let result = clean_lines.join("\n");

    // Final trim of the whole text
    result.trim().to_string()
}

// Extract title from HTML
fn extract_title_from_html(html: &str, url: &str) -> String {
    let html_lower = html.to_lowercase();

    // Find <title> tag
    if let Some(start) = html_lower.find("<title>") {
        let start = start + 7; // len("<title>")
        if let Some(end) = html_lower[start..].find("</title>") {
            let title_html = &html[start..start + end];
            // Decode basic HTML entities
            let decoded = html_escape::decode_html_entities(title_html).to_string();
            let trimmed = decoded.trim();
            if !trimmed.is_empty() {
                return trimmed.to_string();
            }
        }
    }

    // Fallback: extract from URL
    if let Ok(parsed) = url::Url::parse(url) {
        if let Some(segments) = parsed.path_segments() {
            let last = segments.last().unwrap_or("");
            if !last.is_empty() {
                return last
                    .replace('-', " ")
                    .replace('_', " ")
                    .split(' ')
                    .map(|s| {
                        let mut chars = s.chars();
                        match chars.next() {
                            None => String::new(),
                            Some(first) => {
                                if !first.is_alphabetic() {
                                    String::new()
                                } else {
                                    first.to_uppercase().collect::<String>() + chars.as_str()
                                }
                            }
                        }
                    })
                    .collect::<Vec<_>>()
                    .join(" ");
            }
            return parsed.host_str().unwrap_or("Untitled").to_string();
        }
    }

    "Untitled".to_string()
}

// ============================================================================
// Favorites Commands - 收藏夹命令
// ============================================================================

/// 创建单词包
#[tauri::command]
pub async fn create_word_pack_cmd(
    app_handle: AppHandle,
    name: String,
    description: Option<String>,
    cover_url: Option<String>,
    author: Option<String>,
    language_from: Option<String>,
    language_to: Option<String>,
    tags: Option<Vec<String>>,
    version: Option<String>,
) -> Result<WordPack, String> {
    ensure_default_word_pack(&app_handle)?;

    let now = chrono::Utc::now().to_rfc3339();
    let pack = WordPack {
        id: Uuid::new_v4().to_string(),
        name: name.trim().to_string(),
        description,
        cover_url,
        author,
        language_from,
        language_to,
        tags: tags.unwrap_or_default(),
        version,
        created_at: now.clone(),
        updated_at: now,
        is_system: false,
    };

    if pack.name.is_empty() {
        return Err("Pack name is required".to_string());
    }

    let json = serde_json::to_string(&pack)
        .map_err(|e| format!("Failed to serialize word pack: {}", e))?;
    save_word_pack(&app_handle, &pack.id, &json)?;
    Ok(pack)
}

/// 更新单词包
#[tauri::command]
pub async fn update_word_pack_cmd(
    app_handle: AppHandle,
    id: String,
    name: Option<String>,
    description: Option<String>,
    cover_url: Option<String>,
    author: Option<String>,
    language_from: Option<String>,
    language_to: Option<String>,
    tags: Option<Vec<String>>,
    version: Option<String>,
) -> Result<WordPack, String> {
    let json = load_word_pack(&app_handle, &id)?;
    let mut pack: WordPack =
        serde_json::from_str(&json).map_err(|e| format!("Failed to parse word pack: {}", e))?;

    if let Some(name) = name {
        let trimmed = name.trim();
        if trimmed.is_empty() {
            return Err("Pack name is required".to_string());
        }
        pack.name = trimmed.to_string();
    }
    if description.is_some() {
        pack.description = description;
    }
    if cover_url.is_some() {
        pack.cover_url = cover_url;
    }
    if author.is_some() {
        pack.author = author;
    }
    if language_from.is_some() {
        pack.language_from = language_from;
    }
    if language_to.is_some() {
        pack.language_to = language_to;
    }
    if tags.is_some() {
        pack.tags = tags.unwrap_or_default();
    }
    if version.is_some() {
        pack.version = version;
    }

    pack.updated_at = chrono::Utc::now().to_rfc3339();

    let updated_json = serde_json::to_string(&pack)
        .map_err(|e| format!("Failed to serialize word pack: {}", e))?;
    save_word_pack(&app_handle, &pack.id, &updated_json)?;
    Ok(pack)
}

/// 列出所有单词包
#[tauri::command]
pub async fn list_word_packs_cmd(app_handle: AppHandle) -> Result<Vec<WordPack>, String> {
    ensure_default_word_pack(&app_handle)?;
    let mut packs = load_all_word_packs(&app_handle)?;
    packs.sort_by(|a, b| a.name.cmp(&b.name));
    packs.sort_by(|a, b| b.is_system.cmp(&a.is_system));
    Ok(packs)
}

/// 删除单词包（系统包不可删除）
#[tauri::command]
pub async fn delete_word_pack_cmd(app_handle: AppHandle, id: String) -> Result<(), String> {
    if id == DEFAULT_UNGROUPED_PACK_ID {
        return Err("System pack cannot be deleted".to_string());
    }

    let default_pack = ensure_default_word_pack(&app_handle)?;
    let _ = load_word_pack(&app_handle, &id)?;

    delete_word_pack(&app_handle, &id)?;

    let mut favorites = load_all_favorite_vocabularies_internal(&app_handle)?;
    for favorite in &mut favorites {
        if favorite.pack_ids.iter().any(|pack_id| pack_id == &id) {
            favorite.pack_ids.retain(|pack_id| pack_id != &id);
            if favorite.pack_ids.is_empty() {
                favorite.pack_ids.push(default_pack.id.clone());
            }
            persist_favorite_vocabulary(&app_handle, favorite)?;
        }
    }

    Ok(())
}

/// 添加单词收藏
#[tauri::command]
pub async fn add_favorite_vocabulary_cmd(
    app_handle: AppHandle,
    word: String,
    meaning: String,
    usage: String,
    explanation: Option<String>,
    example: Option<String>,
    reading: Option<String>,
    source_article_id: Option<String>,
    source_article_title: Option<String>,
    pack_ids: Option<Vec<String>>,
) -> Result<FavoriteVocabulary, String> {
    let default_pack = ensure_default_word_pack(&app_handle)?;
    let packs = load_all_word_packs(&app_handle)?;
    let existing_pack_ids: HashSet<String> = packs.into_iter().map(|p| p.id).collect();

    let normalized_input = normalize_word(&word);
    if normalized_input.is_empty() || meaning.trim().is_empty() {
        return Err("Word and meaning are required".to_string());
    }

    let mut pack_ids = filter_existing_pack_ids(
        sanitize_pack_ids(pack_ids),
        &existing_pack_ids,
        &default_pack.id,
    );

    let mut favorites = load_all_favorite_vocabularies_internal(&app_handle)?;
    if let Some(existing) = favorites
        .iter_mut()
        .find(|fav| normalize_word(&fav.word) == normalized_input)
    {
        let mut merged = existing.pack_ids.clone();
        merged.append(&mut pack_ids);
        existing.pack_ids = sanitize_pack_ids(Some(merged));
        if existing.pack_ids.is_empty() {
            existing.pack_ids.push(default_pack.id.clone());
        }

        if existing.meaning.trim().is_empty() {
            existing.meaning = meaning.clone();
        }
        if existing.usage.trim().is_empty() {
            existing.usage = usage.clone();
        }
        if existing.example.is_none() {
            existing.example = example.clone();
        }
        if existing.reading.is_none() {
            existing.reading = reading.clone();
        }
        if existing.explanation.is_none() {
            existing.explanation = explanation.clone();
        }
        if existing.source_article_id.is_none() {
            existing.source_article_id = source_article_id.clone();
        }
        if existing.source_article_title.is_none() {
            existing.source_article_title = source_article_title.clone();
        }

        persist_favorite_vocabulary(&app_handle, existing)?;
        return Ok(existing.clone());
    }

    let favorite = FavoriteVocabulary {
        id: Uuid::new_v4().to_string(),
        word: word.trim().to_string(),
        meaning: meaning.trim().to_string(),
        usage: usage.trim().to_string(),
        explanation,
        example,
        reading,
        source_article_id,
        source_article_title,
        pack_ids,
        srs_state: "new".to_string(),
        ease_factor: 2.5,
        repetitions: 0,
        interval_days: 0,
        due_date: today_local_date().format("%Y-%m-%d").to_string(),
        last_reviewed_at: None,
        review_count: 0,
        created_at: chrono::Utc::now().to_rfc3339(),
    };

    persist_favorite_vocabulary(&app_handle, &favorite)?;
    Ok(favorite)
}

/// 列出所有单词收藏
#[tauri::command]
pub async fn list_favorite_vocabularies_cmd(
    app_handle: AppHandle,
) -> Result<Vec<FavoriteVocabulary>, String> {
    ensure_default_word_pack(&app_handle)?;
    migrate_favorite_vocabularies(&app_handle)?;
    let mut favorites = load_all_favorite_vocabularies_internal(&app_handle)?;

    // 按创建时间降序排列
    favorites.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(favorites)
}

/// 删除单词收藏
#[tauri::command]
pub async fn delete_favorite_vocabulary_cmd(
    app_handle: AppHandle,
    id: String,
) -> Result<(), String> {
    delete_favorite_vocabulary(&app_handle, &id)?;
    Ok(())
}

/// 设置单词收藏所属合集
#[tauri::command]
pub async fn set_vocabulary_pack_ids_cmd(
    app_handle: AppHandle,
    vocabulary_id: String,
    pack_ids: Vec<String>,
) -> Result<FavoriteVocabulary, String> {
    let default_pack = ensure_default_word_pack(&app_handle)?;
    let existing_pack_ids: HashSet<String> = list_word_packs(&app_handle)?.into_iter().collect();

    let json = load_favorite_vocabulary(&app_handle, &vocabulary_id)?;
    let mut favorite: FavoriteVocabulary = serde_json::from_str(&json)
        .map_err(|e| format!("Failed to parse favorite vocabulary: {}", e))?;

    favorite.pack_ids = filter_existing_pack_ids(
        sanitize_pack_ids(Some(pack_ids)),
        &existing_pack_ids,
        &default_pack.id,
    );
    persist_favorite_vocabulary(&app_handle, &favorite)?;
    Ok(favorite)
}

/// 按合集列出单词收藏
#[tauri::command]
pub async fn list_favorite_vocabularies_by_pack_cmd(
    app_handle: AppHandle,
    pack_id: String,
) -> Result<Vec<FavoriteVocabulary>, String> {
    let mut favorites = list_favorite_vocabularies_cmd(app_handle).await?;
    if pack_id != "all" {
        favorites.retain(|fav| fav.pack_ids.iter().any(|id| id == &pack_id));
    }
    favorites.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    Ok(favorites)
}

/// 获取指定日期到期的背诵队列
#[tauri::command]
pub async fn get_due_vocabulary_queue_cmd(
    app_handle: AppHandle,
    pack_id: String,
    date_local: String,
) -> Result<Vec<FavoriteVocabulary>, String> {
    let config = load_config(&app_handle)?.unwrap_or_default();
    let all = list_favorite_vocabularies_cmd(app_handle).await?;
    build_due_vocabulary_queue(
        all,
        &pack_id,
        &date_local,
        config.srs_daily_new_limit,
        config.srs_daily_review_limit,
    )
}

/// 复习单词并更新 SM-2 状态
#[tauri::command]
pub async fn review_vocabulary_cmd(
    app_handle: AppHandle,
    vocabulary_id: String,
    grade: String,
    date_local: String,
) -> Result<FavoriteVocabulary, String> {
    let review_date = parse_local_date(&date_local)?;

    let json = load_favorite_vocabulary(&app_handle, &vocabulary_id)?;
    let mut favorite: FavoriteVocabulary = serde_json::from_str(&json)
        .map_err(|e| format!("Failed to parse favorite vocabulary: {}", e))?;

    let next = calculate_sm2_update(
        favorite.repetitions,
        favorite.interval_days,
        favorite.ease_factor,
        &grade,
        review_date,
    )?;

    favorite.srs_state = next.srs_state;
    favorite.repetitions = next.repetitions;
    favorite.interval_days = next.interval_days;
    favorite.ease_factor = next.ease_factor;
    favorite.due_date = next.due_date;
    favorite.last_reviewed_at = Some(chrono::Utc::now().to_rfc3339());
    favorite.review_count += 1;

    persist_favorite_vocabulary(&app_handle, &favorite)?;
    Ok(favorite)
}

/// 导出单词包为 OpenKoto JSON 包
#[tauri::command]
pub async fn export_word_pack_cmd(
    app_handle: AppHandle,
    pack_id: String,
) -> Result<ExportWordPackResult, String> {
    let pack_json = load_word_pack(&app_handle, &pack_id)?;
    let pack: WordPack = serde_json::from_str(&pack_json)
        .map_err(|e| format!("Failed to parse word pack: {}", e))?;

    let mut entries: Vec<WordPackExportEntry> =
        list_favorite_vocabularies_by_pack_cmd(app_handle.clone(), pack_id)
            .await?
            .into_iter()
            .map(|fav| WordPackExportEntry {
                word: fav.word,
                meaning: fav.meaning,
                usage: if fav.usage.trim().is_empty() {
                    None
                } else {
                    Some(fav.usage)
                },
                example: fav.example,
                reading: fav.reading,
                explanation: fav.explanation,
                tags: Vec::new(),
            })
            .collect();

    entries.sort_by(|a, b| a.word.cmp(&b.word));

    let export_file = WordPackExportFile {
        schema_version: "openkoto-word-pack-v1".to_string(),
        pack: WordPackExportMeta {
            name: pack.name.clone(),
            description: pack.description.clone(),
            cover_url: pack.cover_url.clone(),
            author: pack.author.clone(),
            language_from: pack.language_from.clone(),
            language_to: pack.language_to.clone(),
            tags: pack.tags.clone(),
            version: pack.version.clone(),
        },
        entries,
    };

    let json_content = serde_json::to_string_pretty(&export_file)
        .map_err(|e| format!("Failed to serialize export file: {}", e))?;
    let file_name = format!("{}.okpack.json", sanitize_file_name(&pack.name));

    Ok(ExportWordPackResult {
        file_name,
        json_content,
    })
}

/// 导入 OpenKoto JSON 单词包
#[tauri::command]
pub async fn import_word_pack_cmd(
    app_handle: AppHandle,
    json_content: String,
) -> Result<ImportWordPackResult, String> {
    ensure_default_word_pack(&app_handle)?;
    let parsed: WordPackExportFile = serde_json::from_str(&json_content)
        .map_err(|e| format!("Invalid word pack JSON: {}", e))?;

    if parsed.entries.len() > 20000 {
        return Err("Word pack is too large (max 20000 entries)".to_string());
    }

    let now = chrono::Utc::now().to_rfc3339();
    let pack = WordPack {
        id: Uuid::new_v4().to_string(),
        name: if parsed.pack.name.trim().is_empty() {
            "Imported Pack".to_string()
        } else {
            parsed.pack.name.trim().to_string()
        },
        description: parsed.pack.description.clone(),
        cover_url: parsed.pack.cover_url.clone(),
        author: parsed.pack.author.clone(),
        language_from: parsed.pack.language_from.clone(),
        language_to: parsed.pack.language_to.clone(),
        tags: parsed.pack.tags.clone(),
        version: parsed.pack.version.clone(),
        created_at: now.clone(),
        updated_at: now,
        is_system: false,
    };

    let pack_json = serde_json::to_string(&pack)
        .map_err(|e| format!("Failed to serialize word pack: {}", e))?;
    save_word_pack(&app_handle, &pack.id, &pack_json)?;

    let mut existing_words: HashSet<String> = load_all_favorite_vocabularies_internal(&app_handle)?
        .into_iter()
        .map(|fav| normalize_word(&fav.word))
        .collect();
    let mut file_seen_words = HashSet::new();

    let total = parsed.entries.len();
    let mut imported = 0usize;
    let mut skipped = 0usize;
    let mut errors = Vec::new();

    for (index, entry) in parsed.entries.into_iter().enumerate() {
        let word = entry.word.trim().to_string();
        let meaning = entry.meaning.trim().to_string();
        if word.is_empty() || meaning.is_empty() {
            skipped += 1;
            errors.push(format!("Entry {} missing required word/meaning", index + 1));
            continue;
        }

        let normalized = normalize_word(&word);
        if file_seen_words.contains(&normalized) || existing_words.contains(&normalized) {
            skipped += 1;
            continue;
        }

        file_seen_words.insert(normalized.clone());
        existing_words.insert(normalized);

        let favorite = FavoriteVocabulary {
            id: Uuid::new_v4().to_string(),
            word,
            meaning,
            usage: entry.usage.unwrap_or_default(),
            explanation: entry.explanation,
            example: entry.example,
            reading: entry.reading,
            source_article_id: None,
            source_article_title: None,
            pack_ids: vec![pack.id.clone()],
            srs_state: "new".to_string(),
            ease_factor: 2.5,
            repetitions: 0,
            interval_days: 0,
            due_date: today_local_date().format("%Y-%m-%d").to_string(),
            last_reviewed_at: None,
            review_count: 0,
            created_at: chrono::Utc::now().to_rfc3339(),
        };

        if let Err(e) = persist_favorite_vocabulary(&app_handle, &favorite) {
            skipped += 1;
            errors.push(format!("Entry {} failed to import: {}", index + 1, e));
            continue;
        }

        imported += 1;
    }

    Ok(ImportWordPackResult {
        created_pack_id: pack.id,
        total,
        imported,
        skipped,
        errors,
    })
}

/// 添加语法收藏
#[tauri::command]
pub async fn add_favorite_grammar_cmd(
    app_handle: AppHandle,
    point: String,
    explanation: String,
    example: Option<String>,
    source_article_id: Option<String>,
    source_article_title: Option<String>,
) -> Result<FavoriteGrammar, String> {
    let favorite = FavoriteGrammar {
        id: Uuid::new_v4().to_string(),
        point,
        explanation,
        example,
        source_article_id,
        source_article_title,
        created_at: chrono::Utc::now().to_rfc3339(),
    };

    let json = serde_json::to_string(&favorite)
        .map_err(|e| format!("Failed to serialize favorite: {}", e))?;
    save_favorite_grammar(&app_handle, &favorite.id, &json)?;

    Ok(favorite)
}

/// 列出所有语法收藏
#[tauri::command]
pub async fn list_favorite_grammars_cmd(
    app_handle: AppHandle,
) -> Result<Vec<FavoriteGrammar>, String> {
    let ids = list_favorite_grammars(&app_handle)?;
    let mut favorites = Vec::new();

    for id in ids {
        if let Ok(json) = load_favorite_grammar(&app_handle, &id) {
            if let Ok(favorite) = serde_json::from_str::<FavoriteGrammar>(&json) {
                favorites.push(favorite);
            }
        }
    }

    // 按创建时间降序排列
    favorites.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(favorites)
}

/// 删除语法收藏
#[tauri::command]
pub async fn delete_favorite_grammar_cmd(app_handle: AppHandle, id: String) -> Result<(), String> {
    delete_favorite_grammar(&app_handle, &id)?;
    Ok(())
}

// YouTube Import
#[tauri::command]
pub async fn import_youtube_video_cmd(
    app_handle: AppHandle,
    url: String,
) -> Result<Article, String> {
    let article = crate::youtube::import_youtube_video(app_handle.clone(), url).await?;

    let article_json = serde_json::to_string(&article)
        .map_err(|e| format!("Failed to serialize article: {}", e))?;
    save_article(&app_handle, &article.id, &article_json)?;

    Ok(article)
}

#[tauri::command]
pub async fn import_local_video_cmd(
    app_handle: AppHandle,
    file_path: String,
) -> Result<Article, String> {
    let app_data_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?;

    let videos_dir = app_data_dir.join("videos");
    if !videos_dir.exists() {
        std::fs::create_dir_all(&videos_dir)
            .map_err(|e| format!("Failed to create videos dir: {}", e))?;
    }

    let src_path = std::path::Path::new(&file_path);
    if !src_path.exists() {
        return Err("Source file does not exist".to_string());
    }

    let file_name = src_path
        .file_name()
        .ok_or("Invalid file name")?
        .to_string_lossy();

    let ext = src_path
        .extension()
        .map(|e| e.to_string_lossy().to_string())
        .unwrap_or_else(|| "mp4".to_string());

    let id = Uuid::new_v4().to_string();
    let dest_name = format!("{}.{}", id, ext);
    let dest_path = videos_dir.join(&dest_name);

    std::fs::copy(src_path, &dest_path).map_err(|e| format!("Failed to copy file: {}", e))?;

    let created_at = chrono::Utc::now().to_rfc3339();
    let is_audio = matches!(
        ext.to_lowercase().as_str(),
        "mp3" | "wav" | "m4a" | "aac" | "flac" | "ogg" | "wma"
    );

    // Initial content placeholder
    let content = if is_audio {
        format!("[Audio Import] {}", file_name)
    } else {
        format!("[Local Import] {}", file_name)
    };

    let article = Article {
        id: id.clone(),
        title: file_name.into_owned(),
        content,
        source_type: Some(if is_audio {
            "audio".to_string()
        } else {
            "local_video".to_string()
        }),
        source_url: Some(format!("file://{}", file_path)),
        media_path: Some(dest_path.to_string_lossy().into_owned()),
        book_path: None,
        book_type: None,
        created_at,
        translated: false,
        segments: Vec::new(),
    };

    let article_json = serde_json::to_string(&article)
        .map_err(|e| format!("Failed to serialize article: {}", e))?;
    save_article(&app_handle, &id, &article_json)?;

    Ok(article)
}

// 字幕提取
/// 提取视频字幕
/// 使用 Gemini 多模态 API 从视频中提取音频并转录为字幕
#[tauri::command]
pub async fn extract_subtitles_cmd(
    app_handle: AppHandle,
    article_id: String,
) -> Result<Article, String> {
    println!("[ExtractSubtitles] 开始提取字幕: {}", article_id);

    // 1. 加载文章
    let article_json = load_article(&app_handle, &article_id)?;
    let mut article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;

    // 2. 验证是视频并获取视频路径
    let video_path = article
        .media_path
        .as_ref()
        .ok_or("该文章不是视频，无法提取字幕")?;
    let video_path = std::path::Path::new(video_path);

    if !video_path.exists() {
        return Err(format!("视频文件不存在: {:?}", video_path));
    }

    // 3. 获取 API 配置
    let config = load_config(&app_handle)?.ok_or("未配置 API，请先在设置中配置 AI 模型")?;

    let active_config = config
        .get_active_config()
        .ok_or("未设置活动模型配置，请先在设置中配置 AI 模型")?;

    // 检查是否是 Gemini 模型
    let model = &active_config.model;
    let provider = &active_config.api_provider;
    let api_key = &active_config.api_key;
    let base_url = active_config.base_url.as_deref();

    // 本地 provider 当前不支持字幕提取（该流程依赖云端多模态转录能力）
    if provider == "ollama" || provider == "lmstudio" {
        return Err(
            "字幕提取暂不支持 Ollama / LM Studio 本地模型。请切换到 Gemini 或 Kimi K2.5。"
                .to_string(),
        );
    }

    // 允许的 Gemini 或 Kimi K2.5 模型
    let is_supported = model.contains("gemini")
        || model.starts_with("google/gemini")
        || provider == "google"
        || provider == "google-ai-studio"
        || (provider == "moonshot" && model.contains("kimi"))
        || model.contains("kimi");

    if !is_supported {
        return Err(
            "字幕提取需要使用 Gemini 或 Kimi K2.5 云端模型。请在设置中切换模型。".to_string(),
        );
    }

    // 4. 调用字幕提取模块 (使用 article_id 作为 event_id)
    let segments = crate::subtitle_extraction::extract_subtitles(
        app_handle.clone(),
        video_path,
        &article_id,
        provider,
        api_key,
        model,
        base_url,
        &article_id, // event_id 用于进度事件
    )
    .await?;

    if segments.is_empty() {
        return Err("未能从视频中提取到字幕内容".to_string());
    }

    println!("[ExtractSubtitles] 提取到 {} 个字幕片段", segments.len());

    // 5. 更新文章内容
    article.segments = segments;
    article.content = article
        .segments
        .iter()
        .map(|s| s.text.clone())
        .collect::<Vec<_>>()
        .join(" ");

    // 6. 保存文章
    let updated_json = serde_json::to_string(&article)
        .map_err(|e| format!("Failed to serialize article: {}", e))?;
    save_article(&app_handle, &article_id, &updated_json)?;

    println!("[ExtractSubtitles] 字幕提取完成并保存");

    Ok(article)
}

// ============================================================================
// 书籍导入功能 - 支持 EPUB、TXT 和 PDF 格式
// ============================================================================

const BOOKS_DIR: &str = "books";

/// 确保书籍存储目录存在
fn ensure_books_dir(app_handle: &AppHandle) -> Result<PathBuf, String> {
    let app_data_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| format!("获取应用数据目录失败: {}", e))?;

    let books_dir = app_data_dir.join(BOOKS_DIR);
    if !books_dir.exists() {
        std::fs::create_dir_all(&books_dir).map_err(|e| format!("创建书籍目录失败: {}", e))?;
    }

    Ok(books_dir)
}

/// 导入书籍文件 (EPUB/TXT/PDF)
/// 将文件复制到应用数据目录并创建 Article 记录
#[tauri::command]
pub async fn import_book_cmd(
    app_handle: AppHandle,
    file_path: String,
    title: Option<String>,
) -> Result<Article, String> {
    use std::path::Path;

    let src_path = Path::new(&file_path);

    // 验证文件存在
    if !src_path.exists() {
        return Err(format!("文件不存在: {}", file_path));
    }

    // 获取文件扩展名并验证格式
    let ext = src_path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_lowercase())
        .ok_or("无法识别文件格式")?;

    let book_type = match ext.as_str() {
        "epub" => "epub",
        "txt" => "txt",
        "pdf" => "pdf",
        _ => return Err(format!("不支持的文件格式: {}", ext)),
    };

    // 获取文件名作为默认标题
    let file_name = src_path
        .file_stem()
        .and_then(|n| n.to_str())
        .unwrap_or("未命名书籍");

    let book_title = title.unwrap_or_else(|| file_name.to_string());

    // 确保书籍目录存在
    let books_dir = ensure_books_dir(&app_handle)?;

    // 生成唯一 ID 和目标路径
    let id = Uuid::new_v4().to_string();
    let dest_name = format!("{}.{}", id, ext);
    let dest_path = books_dir.join(&dest_name);

    // 复制文件到应用数据目录
    std::fs::copy(src_path, &dest_path).map_err(|e| format!("复制文件失败: {}", e))?;

    let created_at = chrono::Utc::now().to_rfc3339();

    // 读取 TXT 文件内容作为 content，EPUB/PDF 使用占位符
    let content = match book_type {
        "txt" => {
            // 尝试读取 TXT 文件内容
            std::fs::read_to_string(&dest_path)
                .unwrap_or_else(|_| format!("[书籍已导入] {}", book_title))
        }
        "epub" => format!("[EPUB 书籍] {}", book_title),
        "pdf" => format!("[PDF 书籍] {}", book_title),
        _ => format!("[书籍已导入] {}", book_title),
    };

    // 创建 Article 记录
    let article = Article {
        id: id.clone(),
        title: book_title,
        content,
        source_type: Some("book".to_string()),
        source_url: Some(format!("file://{}", file_path)),
        media_path: None,
        book_path: Some(dest_path.to_string_lossy().into_owned()),
        book_type: Some(book_type.to_string()),
        created_at,
        translated: false,
        segments: Vec::new(), // 书籍不预分段，由阅读器处理
    };

    // 保存文章记录
    let article_json =
        serde_json::to_string(&article).map_err(|e| format!("序列化文章失败: {}", e))?;
    save_article(&app_handle, &id, &article_json)?;

    println!(
        "[ImportBook] 书籍导入成功: {} ({})",
        article.title, book_type
    );

    Ok(article)
}

#[tauri::command]
pub async fn import_web_material_cmd(
    app_handle: AppHandle,
    url: String,
    title: Option<String>,
    content: String,
) -> Result<Article, String> {
    let parsed_url = url::Url::parse(&url).map_err(|_| "Invalid URL format".to_string())?;
    if parsed_url.scheme() != "http" && parsed_url.scheme() != "https" {
        return Err("Only HTTP and HTTPS URLs are supported".to_string());
    }

    if content.trim().len() < 10 {
        return Err(
            "Extracted content is too short. Please check the URL and try again.".to_string(),
        );
    }

    let id = Uuid::new_v4().to_string();
    let created_at = chrono::Utc::now().to_rfc3339();
    let final_title = title.unwrap_or_else(|| "Untitled Web Material".to_string());
    let segments = create_segments_from_content(&id, &content);

    let article = Article {
        id: id.clone(),
        title: final_title,
        content,
        source_type: Some("web".to_string()),
        source_url: Some(url),
        media_path: None,
        book_path: None,
        book_type: None,
        created_at,
        translated: false,
        segments,
    };

    let article_json = serde_json::to_string(&article)
        .map_err(|e| format!("Failed to serialize article: {}", e))?;
    save_article(&app_handle, &id, &article_json)?;

    Ok(article)
}

// File System Commands
#[tauri::command]
pub async fn write_text_file(path: String, content: String) -> Result<(), String> {
    use std::fs;
    fs::write(path, content).map_err(|e| format!("Failed to write file: {}", e))
}

#[tauri::command]
pub async fn write_binary_file(path: String, content: Vec<u8>) -> Result<(), String> {
    use std::fs;
    fs::write(path, content).map_err(|e| format!("Failed to write file: {}", e))
}

#[tauri::command]
pub async fn delete_article_subtitles_cmd(app_handle: AppHandle, id: String) -> Result<(), String> {
    let article_json = load_article(&app_handle, &id)?;
    let mut article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;

    article.segments = Vec::new();
    article.translated = false;

    let updated_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &id, &updated_json)?;

    Ok(())
}

#[tauri::command]
pub async fn delete_article_analysis_cmd(app_handle: AppHandle, id: String) -> Result<(), String> {
    let article_json = load_article(&app_handle, &id)?;
    let mut article: Article = serde_json::from_str(&article_json)
        .map_err(|e| format!("Failed to parse article: {}", e))?;

    for segment in &mut article.segments {
        segment.translation = None;
        segment.explanation = None;
    }
    article.translated = false;

    let updated_json = serde_json::to_string(&article).unwrap();
    save_article(&app_handle, &id, &updated_json)?;

    Ok(())
}

/// PDF全文翻译命令
/// 调用 Python PDF翻译插件进行翻译，生成纯译文和双语对照PDF
#[tauri::command]
pub async fn translate_pdf_document(
    app_handle: AppHandle,
    pdf_path: String,
    lang_in: String,
    lang_out: String,
    provider: String,
    api_key: String,
    model: String,
    base_url: Option<String>,
) -> Result<serde_json::Value, String> {
    use crate::plugin_manager;
    use std::process::Command;

    println!(
        "[PDF Translate] Starting translation: {} -> {}",
        lang_in, lang_out
    );
    println!("[PDF Translate] Provider: {}, Model: {}", provider, model);

    // 获取输出目录（与原PDF相同目录）
    let pdf_path_buf = PathBuf::from(&pdf_path);
    let output_dir = pdf_path_buf
        .parent()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| ".".to_string());

    let filename_stem = pdf_path_buf
        .file_stem()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "output".to_string());

    // 构建环境变量
    let mut envs: Vec<(&str, String)> = vec![
        ("OPENKOTO_PROVIDER", provider.clone()),
        ("OPENKOTO_API_KEY", api_key.clone()),
        ("OPENKOTO_MODEL", model.clone()),
    ];

    if let Some(ref url) = base_url {
        envs.push(("OPENKOTO_BASE_URL", url.clone()));
    }

    // 使用 PluginManager 获取执行命令
    // 假设插件名称为 "openkoto-pdf-translator"
    let plugin_name = "openkoto-pdf-translator";

    let (cmd, mut args, plugin_dir) =
        match plugin_manager::get_plugin_execution_command(&app_handle, plugin_name) {
            Ok(res) => res,
            Err(e) => return Err(format!("Plugin error: {}", e)),
        };

    // 动态添加参数
    // 我们约定 entry_point.args 包含固定前缀，如 ["-m", "openkoto_pdf_translator.pdf2zh"]
    // 我们需要追加 PDF 相关的参数
    // 原 args: -m openkoto_pdf_translator.pdf2zh [input] -li ...

    args.push(pdf_path.clone());
    args.push("-li".to_string());
    args.push(lang_in);
    args.push("-lo".to_string());
    args.push(lang_out);
    args.push("-s".to_string());
    args.push("openkoto".to_string());
    args.push("-o".to_string());
    args.push(output_dir.clone());

    println!("[Plugin] Executing: {} {:?}", cmd, args);
    println!("[Plugin] CWD: {:?}", plugin_dir);

    // 在插件目录下执行，以确保 Python 模块导入正确 (如果是 Dev 模式)
    // 或者对于 Prod 模式，通常也不影响
    let result = Command::new(&cmd)
        .args(&args)
        .envs(envs.iter().map(|(k, v)| (*k, v.as_str())))
        .current_dir(&plugin_dir) // 关键：设置工作目录为插件目录
        .output();

    match result {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);

            println!("[PDF Translate] stdout: {}", stdout);
            if !stderr.is_empty() {
                println!("[PDF Translate] stderr: {}", stderr);
            }

            if output.status.success() {
                // 构建输出文件路径
                let mono_path = format!("{}/{}-mono.pdf", output_dir, filename_stem);
                let dual_path = format!("{}/{}-dual.pdf", output_dir, filename_stem);

                Ok(serde_json::json!({
                    "success": true,
                    "mono_pdf": mono_path,
                    "dual_pdf": dual_path,
                    "original_pdf": pdf_path,
                }))
            } else {
                Err(format!("PDF translation failed: {}", stderr))
            }
        }
        Err(e) => Err(format!("Failed to execute plugin command '{}': {}", cmd, e)),
    }
}

#[derive(serde::Serialize)]
pub struct TranslationFiles {
    pub mono_path: Option<String>,
    pub dual_path: Option<String>,
}

#[tauri::command]
pub async fn check_pdf_translation_files(pdf_path: String) -> Result<TranslationFiles, String> {
    use std::path::Path;
    let path = Path::new(&pdf_path);
    if !path.exists() {
        return Ok(TranslationFiles {
            mono_path: None,
            dual_path: None,
        });
    }

    let parent = path.parent().unwrap_or(Path::new("."));

    // Safety check: ensure file stem exists
    let stem = match path.file_stem() {
        Some(s) => s.to_string_lossy(),
        None => {
            return Ok(TranslationFiles {
                mono_path: None,
                dual_path: None,
            })
        }
    };

    let mono_name = format!("{}-mono.pdf", stem);
    let dual_name = format!("{}-dual.pdf", stem);

    let mono_path = parent.join(&mono_name);
    let dual_path = parent.join(&dual_name);

    Ok(TranslationFiles {
        mono_path: if mono_path.exists() {
            Some(mono_path.to_string_lossy().into_owned())
        } else {
            None
        },
        dual_path: if dual_path.exists() {
            Some(dual_path.to_string_lossy().into_owned())
        } else {
            None
        },
    })
}

#[tauri::command]
pub async fn export_file_cmd(src_path: String, dest_path: String) -> Result<(), String> {
    std::fs::copy(&src_path, &dest_path).map_err(|e| format!("Failed to export file: {}", e))?;
    Ok(())
}

// ============================================================================
// Bookmarks Commands - 书签命令
// ============================================================================

/// 添加书签
#[tauri::command]
pub async fn add_bookmark_cmd(
    app_handle: AppHandle,
    book_path: String,
    book_type: String,
    title: String,
    note: Option<String>,
    selected_text: Option<String>,
    page_number: Option<i32>,
    epub_cfi: Option<String>,
    color: Option<String>,
) -> Result<Bookmark, String> {
    let bookmark = Bookmark {
        id: Uuid::new_v4().to_string(),
        book_path,
        book_type,
        title,
        note,
        selected_text,
        page_number,
        epub_cfi,
        created_at: chrono::Utc::now().to_rfc3339(),
        color,
    };

    let json = serde_json::to_string(&bookmark)
        .map_err(|e| format!("Failed to serialize bookmark: {}", e))?;
    save_bookmark(&app_handle, &bookmark.id, &json)?;

    Ok(bookmark)
}

/// 列出所有书签
#[tauri::command]
pub async fn list_bookmarks_cmd(app_handle: AppHandle) -> Result<Vec<Bookmark>, String> {
    let ids = list_bookmarks(&app_handle)?;
    let mut bookmarks = Vec::new();

    for id in ids {
        if let Ok(json) = load_bookmark(&app_handle, &id) {
            if let Ok(bookmark) = serde_json::from_str::<Bookmark>(&json) {
                bookmarks.push(bookmark);
            }
        }
    }

    // 按创建时间降序排列
    bookmarks.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(bookmarks)
}

/// 列出指定书籍的书签
#[tauri::command]
pub async fn list_bookmarks_for_book_cmd(
    app_handle: AppHandle,
    book_path: String,
) -> Result<Vec<Bookmark>, String> {
    let ids = list_bookmarks_for_book(&app_handle, &book_path)?;
    let mut bookmarks = Vec::new();

    for id in ids {
        if let Ok(json) = load_bookmark(&app_handle, &id) {
            if let Ok(bookmark) = serde_json::from_str::<Bookmark>(&json) {
                bookmarks.push(bookmark);
            }
        }
    }

    // 按创建时间降序排列
    bookmarks.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(bookmarks)
}

/// 更新书签
#[tauri::command]
pub async fn update_bookmark_cmd(
    app_handle: AppHandle,
    id: String,
    title: Option<String>,
    note: Option<String>,
    color: Option<String>,
) -> Result<Bookmark, String> {
    let json = load_bookmark(&app_handle, &id)?;
    let mut bookmark: Bookmark =
        serde_json::from_str(&json).map_err(|e| format!("Failed to parse bookmark: {}", e))?;

    if let Some(t) = title {
        bookmark.title = t;
    }
    if let Some(n) = note {
        bookmark.note = Some(n);
    }
    if let Some(c) = color {
        bookmark.color = Some(c);
    }

    let updated_json = serde_json::to_string(&bookmark)
        .map_err(|e| format!("Failed to serialize bookmark: {}", e))?;
    save_bookmark(&app_handle, &id, &updated_json)?;

    Ok(bookmark)
}

/// 删除书签
#[tauri::command]
pub async fn delete_bookmark_cmd(app_handle: AppHandle, id: String) -> Result<(), String> {
    delete_bookmark(&app_handle, &id)?;
    Ok(())
}
