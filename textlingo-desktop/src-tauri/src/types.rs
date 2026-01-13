use serde::{Deserialize, Serialize};

/// A single model configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    pub id: String,
    pub name: String,
    pub api_key: String,
    pub api_provider: String, // "openai", "openrouter", "deepseek", "google", "openai-compatible", "ollama", "lmstudio"
    pub model: String,
    pub is_default: bool,
    #[serde(default)]
    pub created_at: Option<String>,
    /// Custom base URL for OpenAI-compatible services, Ollama, LM Studio, etc.
    #[serde(default)]
    pub base_url: Option<String>,
}

impl ModelConfig {
    pub fn new(name: String, api_key: String, api_provider: String, model: String) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            name,
            api_key,
            api_provider,
            model,
            is_default: false,
            created_at: Some(chrono::Utc::now().to_rfc3339()),
            base_url: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Active model config ID (defaults to first config if not set)
    #[serde(default)]
    pub active_model_id: Option<String>,
    /// List of saved model configurations
    #[serde(default)]
    pub model_configs: Vec<ModelConfig>,
    /// Default target language for translations
    pub target_language: String,
    /// Interface language
    #[serde(default = "default_interface_language")]
    pub interface_language: String,
    /// Backend API URL for enhanced features
    #[serde(default)]
    pub backend_url: Option<String>,
    /// Auth token for backend API
    #[serde(default)]
    pub auth_token: Option<String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            active_model_id: None,
            model_configs: Vec::new(),
            target_language: "zh-CN".to_string(),
            interface_language: default_interface_language(),
            backend_url: None,
            auth_token: None,
        }
    }
}

impl AppConfig {
    /// Get the active model config, or the first one, or None
    pub fn get_active_config(&self) -> Option<&ModelConfig> {
        if let Some(id) = &self.active_model_id {
            self.model_configs.iter().find(|c| &c.id == id)
        } else {
            self.model_configs.first()
        }
    }

    /// Get a model config by ID
    pub fn get_config(&self, id: &str) -> Option<&ModelConfig> {
        self.model_configs.iter().find(|c| c.id == id)
    }
}

fn default_interface_language() -> String {
    "en".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Article {
    pub id: String,
    pub title: String,
    pub content: String,
    pub source_url: Option<String>,
    pub media_path: Option<String>,
    pub created_at: String,
    pub translated: bool,
    #[serde(default)]
    pub segments: Vec<ArticleSegment>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArticleSegment {
    pub id: String,
    pub article_id: String,
    pub order: i32,
    pub text: String,
    pub reading_text: Option<String>,
    pub translation: Option<String>,
    pub explanation: Option<SegmentExplanation>,
    /// Start time in seconds (for subtitles)
    #[serde(default)]
    pub start_time: Option<f64>,
    /// End time in seconds (for subtitles)
    #[serde(default)]
    pub end_time: Option<f64>,
    pub created_at: String,
    /// 是否是新段落开始（true则另起一行显示，false则紧跟上一段显示）
    #[serde(default)]
    pub is_new_paragraph: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SegmentExplanation {
    pub translation: String,
    pub explanation: String,
    pub reading_text: Option<String>,
    #[serde(default)]
    pub vocabulary: Vec<VocabularyItem>,
    #[serde(default)]
    pub grammar_points: Vec<GrammarPoint>,
    pub cultural_context: Option<String>,
    pub difficulty_level: Option<String>,
    pub learning_tips: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VocabularyItem {
    pub word: String,
    pub meaning: String,
    pub usage: String,
    pub example: Option<String>,
    pub reading: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrammarPoint {
    pub point: String,
    pub explanation: String,
    pub example: Option<String>,
}

/// 收藏的单词
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FavoriteVocabulary {
    pub id: String,
    pub word: String,
    pub meaning: String,
    pub usage: String,
    pub example: Option<String>,
    pub reading: Option<String>,
    /// 来源文章ID（可选，文章删除后收藏仍保留）
    pub source_article_id: Option<String>,
    /// 来源文章标题（快照，便于显示）
    pub source_article_title: Option<String>,
    pub created_at: String,
}

/// 收藏的语法点
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FavoriteGrammar {
    pub id: String,
    pub point: String,
    pub explanation: String,
    pub example: Option<String>,
    /// 来源文章ID（可选，文章删除后收藏仍保留）
    pub source_article_id: Option<String>,
    /// 来源文章标题（快照，便于显示）
    pub source_article_title: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationRequest {
    pub text: String,
    pub target_language: String,
    pub context: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationResponse {
    pub translated_text: String,
    pub original_text: String,
    pub model_used: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisRequest {
    pub text: String,
    pub analysis_type: AnalysisType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AnalysisType {
    Summary,
    KeyPoints,
    Vocabulary,
    Grammar,
    FullAnalysis,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisResponse {
    pub analysis_type: AnalysisType,
    pub result: String,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ChatContent {
    Text(String),
    Parts(Vec<ContentPart>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentPart {
    #[serde(rename = "type")]
    pub part_type: String, // "text", "image_url", "file"
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image_url: Option<ImageUrl>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file_data: Option<FileData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageUrl {
    pub url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileData {
    pub mime_type: String,
    pub data: String, // Base64
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String, // "user" or "assistant"
    pub content: ChatContent,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    pub messages: Vec<ChatMessage>,
    pub model: String,
    pub temperature: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub content: String,
    pub model: String,
    pub tokens_used: Option<u32>,
}

/// 转录片段 (用于字幕提取)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranscriptionSegment {
    pub speaker: Option<String>,
    pub content: String,
    /// Start time in seconds
    #[serde(default)]
    pub start_time: Option<f64>,
    /// End time in seconds
    #[serde(default)]
    pub end_time: Option<f64>,
}

/// 转录结果 (用于字幕提取)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranscriptionResult {
    pub segments: Vec<TranscriptionSegment>,
    pub full_text: String,
}

