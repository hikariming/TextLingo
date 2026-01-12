use crate::ai_service::{get_ai_service, get_or_create_ai_service, AIServiceCache};
use crate::storage::{
    delete_article, ensure_app_dirs, load_article, load_config, list_articles, save_article,
    save_config,
    // 收藏夹存储函数
    save_favorite_vocabulary, load_favorite_vocabulary, list_favorite_vocabularies, delete_favorite_vocabulary,
    save_favorite_grammar, load_favorite_grammar, list_favorite_grammars, delete_favorite_grammar,
};
use crate::types::{
    AnalysisRequest, AnalysisResponse, AnalysisType, Article, ChatRequest, ChatResponse,
    TranslationRequest, TranslationResponse, ModelConfig, ArticleSegment,
    FavoriteVocabulary, FavoriteGrammar,
};
use tauri::{AppHandle, State, Manager};
use uuid::Uuid;
use reqwest::Client;
use std::time::Duration;

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
        let is_sentence_end = c == '。' || c == '？' || c == '！' ||
            (c == '.' && !is_abbreviation(&chars, i)) ||
            c == '?' || c == '!';
        
        if is_sentence_end {
            // 处理引号闭合情况：如 ... said." 这种情况
            // 向后看，如果下一个字符是引号，把它也加进来
            if i + 1 < chars.len() {
                let next = chars[i + 1];
                if next == '"' || next == '"' || next == '\'' || next == '\u{2019}' || next == ')' || next == '）' {
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
    let abbreviations = ["mr", "mrs", "ms", "dr", "jr", "sr", "vs", "etc", "inc", "ltd", "no", "st", "ave", "rd"];
    
    if abbreviations.contains(&word_lower.as_str()) {
        return true;
    }
    
    // 单字母后跟句点通常是缩写（如 A. B. C.）
    if word.len() == 1 && word.chars().next().unwrap().is_uppercase() {
        return true;
    }
    
    false
}

// Initialize the app (ensure directories exist)
#[tauri::command]
pub async fn init_app(app_handle: AppHandle) -> Result<String, String> {
    ensure_app_dirs(&app_handle)?;
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
    let existing_index = app_config.model_configs.iter().position(|c| c.id == config.id);

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
        ).await?;
    }

    Ok(config)
}

/// Delete a model configuration
#[tauri::command]
pub async fn delete_model_config(
    app_handle: AppHandle,
    config_id: String,
) -> Result<(), String> {
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

    let config = app_config.get_config(&config_id)
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
    ).await?;

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
    let existing = app_config.model_configs.iter()
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
    let existing_index = app_config.model_configs.iter().position(|c| c.id == config.id);
    if let Some(idx) = existing_index {
        app_config.model_configs[idx] = config.clone();
    } else {
        app_config.model_configs.push(config.clone());
    }

    // Set as active
    app_config.active_model_id = Some(config_id.clone());

    save_config(&app_handle, &app_config)?;

    // Update AI service cache
    get_or_create_ai_service(&state, config.api_key.clone(), config.api_provider.clone(), config.model.clone()).await?;

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
        source_url: source_url.clone(),
        media_path: None,
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
pub async fn segment_translate_explain_cmd(
    state: AppState<'_>,
    text: String,
    target_language: String,
) -> Result<crate::types::SegmentExplanation, String> {
    let ai_service = get_ai_service(&state).await?;
    ai_service.segment_translate_explain(text, target_language).await
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
    let untranslated: Vec<(String, String)> = article.segments
        .iter()
        .filter(|s| s.translation.is_none())
        .map(|s| (s.id.clone(), s.text.clone()))
        .collect();

    if !untranslated.is_empty() {
        let ai_service = get_ai_service(&state).await?;
        
        // 批量翻译（每批最多30条）
        const BATCH_SIZE: usize = 30;
        for chunk in untranslated.chunks(BATCH_SIZE) {
            let batch_items: Vec<(String, String)> = chunk.to_vec();
            
            match ai_service.batch_translate(batch_items, &target_language).await {
                Ok(translations) => {
                    // 将翻译结果写回对应的 segment
                    for (id, translation) in translations {
                        if let Some(seg) = article.segments.iter_mut().find(|s| s.id == id) {
                            seg.translation = Some(translation);
                        }
                    }
                }
                Err(e) => {
                    // 批量翻译失败，记录错误但继续
                    eprintln!("Batch translation error: {}", e);
                }
            }
        }
    }

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
    let parsed_url = url::Url::parse(&url)
        .map_err(|_| "Invalid URL format".to_string())?;

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
    if let Ok(extracted) = readability::extractor::extract(&mut cursor, &url::Url::parse(&url).unwrap()) {
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

/// 添加单词收藏
#[tauri::command]
pub async fn add_favorite_vocabulary_cmd(
    app_handle: AppHandle,
    word: String,
    meaning: String,
    usage: String,
    example: Option<String>,
    reading: Option<String>,
    source_article_id: Option<String>,
    source_article_title: Option<String>,
) -> Result<FavoriteVocabulary, String> {
    let favorite = FavoriteVocabulary {
        id: Uuid::new_v4().to_string(),
        word,
        meaning,
        usage,
        example,
        reading,
        source_article_id,
        source_article_title,
        created_at: chrono::Utc::now().to_rfc3339(),
    };

    let json = serde_json::to_string(&favorite)
        .map_err(|e| format!("Failed to serialize favorite: {}", e))?;
    save_favorite_vocabulary(&app_handle, &favorite.id, &json)?;

    Ok(favorite)
}

/// 列出所有单词收藏
#[tauri::command]
pub async fn list_favorite_vocabularies_cmd(
    app_handle: AppHandle,
) -> Result<Vec<FavoriteVocabulary>, String> {
    let ids = list_favorite_vocabularies(&app_handle)?;
    let mut favorites = Vec::new();

    for id in ids {
        if let Ok(json) = load_favorite_vocabulary(&app_handle, &id) {
            if let Ok(favorite) = serde_json::from_str::<FavoriteVocabulary>(&json) {
                favorites.push(favorite);
            }
        }
    }

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
pub async fn delete_favorite_grammar_cmd(
    app_handle: AppHandle,
    id: String,
) -> Result<(), String> {
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

    std::fs::copy(src_path, &dest_path)
        .map_err(|e| format!("Failed to copy file: {}", e))?;

    let created_at = chrono::Utc::now().to_rfc3339();
    
    // Initial content placeholder
    let content = format!("[Local Import] {}", file_name);

    let article = Article {
        id: id.clone(),
        title: file_name.into_owned(),
        content,
        source_url: Some(format!("file://{}", file_path)),
        media_path: Some(dest_path.to_string_lossy().into_owned()),
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
    let video_path = article.media_path.as_ref()
        .ok_or("该文章不是视频，无法提取字幕")?;
    let video_path = std::path::Path::new(video_path);
    
    if !video_path.exists() {
        return Err(format!("视频文件不存在: {:?}", video_path));
    }
    
    // 3. 获取 API 配置
    let config = load_config(&app_handle)?
        .ok_or("未配置 API，请先在设置中配置 AI 模型")?;
    
    let active_config = config.get_active_config()
        .ok_or("未设置活动模型配置，请先在设置中配置 AI 模型")?;
    
    // 检查是否是 Gemini 模型
    let model = &active_config.model;
    let provider = &active_config.api_provider;
    let api_key = &active_config.api_key;
    
    // 允许的 Gemini 模型前缀
    let is_gemini = model.contains("gemini") || 
                    model.starts_with("google/gemini") ||
                    provider == "google" || provider == "google-ai-studio";
    
    if !is_gemini {
        return Err("字幕提取需要使用 Gemini 模型。请在设置中配置 Gemini API (gemini-2.0-flash 或更新版本)".to_string());
    }
    
    // 4. 调用字幕提取模块
    let segments = crate::subtitle_extraction::extract_subtitles(
        app_handle.clone(),
        video_path,
        &article_id,
        provider,
        api_key,
        model,
    ).await?;
    
    if segments.is_empty() {
        return Err("未能从视频中提取到字幕内容".to_string());
    }
    
    println!("[ExtractSubtitles] 提取到 {} 个字幕片段", segments.len());
    
    // 5. 更新文章内容
    article.segments = segments;
    article.content = article.segments
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

