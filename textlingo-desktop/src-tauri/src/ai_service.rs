use crate::types::{
    AnalysisRequest, AnalysisResponse, AnalysisType, ChatRequest, ChatResponse,
    TranslationRequest, TranslationResponse,
};
use reqwest::Client;
use serde_json::{json, Value};

const OPENAI_API_URL: &str = "https://api.openai.com/v1/chat/completions";
const OPENROUTER_API_URL: &str = "https://openrouter.ai/api/v1/chat/completions";
const DEEPSEEK_API_URL: &str = "https://api.deepseek.com/v1/chat/completions";
const SILICONFLOW_API_URL: &str = "https://api.siliconflow.cn/v1/chat/completions";
const API_302AI_URL: &str = "https://api.302.ai/v1/chat/completions";

pub struct AIService {
    client: Client,
    api_key: String,
    provider: String,
    model: String,
}

impl AIService {
    pub fn new(api_key: String, provider: String, model: String) -> Self {
        Self {
            client: Client::new(),
            api_key,
            provider,
            model,
        }
    }

    fn get_api_url(&self) -> &str {
        match self.provider.as_str() {
            "openrouter" => OPENROUTER_API_URL,
            "deepseek" => DEEPSEEK_API_URL,
            "siliconflow" => SILICONFLOW_API_URL,
            "302ai" => API_302AI_URL,
            _ => OPENAI_API_URL,
        }
    }

    async fn make_request(
        &self,
        messages: Vec<Value>,
        temperature: Option<f32>,
    ) -> Result<String, String> {
        let request_body = json!({
            "model": self.model,
            "messages": messages,
            "temperature": temperature.unwrap_or(0.7)
        });

        let response = self
            .client
            .post(self.get_api_url())
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&request_body)
            .send()
            .await
            .map_err(|e| format!("Failed to send request: {}", e))?;

        if !response.status().is_success() {
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(format!("API error: {}", error_text));
        }

        let response_json: Value = response
            .json()
            .await
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        response_json["choices"][0]["message"]["content"]
            .as_str()
            .map(|s| s.to_string())
            .ok_or_else(|| "No content in response".to_string())
    }

    pub async fn translate(&self, request: TranslationRequest) -> Result<TranslationResponse, String> {
        let system_prompt = format!(
            "You are a professional translator. Translate the following text to {}. \
            Preserve the original meaning and tone. Only return the translated text without any explanations.",
            request.target_language
        );

        let messages = vec![
            json!({"role": "system", "content": system_prompt}),
            json!({"role": "user", "content": request.text}),
        ];

        let translated_text = self.make_request(messages, Some(0.3)).await?;

        Ok(TranslationResponse {
            translated_text,
            original_text: request.text,
            model_used: self.model.clone(),
        })
    }

    pub async fn analyze(&self, request: AnalysisRequest) -> Result<AnalysisResponse, String> {
        let system_prompt = match request.analysis_type {
            AnalysisType::Summary => {
                "Provide a concise summary of the following text in 3-5 sentences."
                    .to_string()
            }
            AnalysisType::KeyPoints => {
                "Extract and list the key points from the following text. Use bullet points."
                    .to_string()
            }
            AnalysisType::Vocabulary => {
                "Identify and explain important vocabulary words, phrases, and idioms from the following text. \
                Include definitions and example sentences."
                    .to_string()
            }
            AnalysisType::Grammar => {
                "Analyze the grammatical structures and patterns used in the following text. \
                Highlight any interesting or complex constructions."
                    .to_string()
            }
            AnalysisType::FullAnalysis => {
                "Provide a comprehensive analysis of the following text including: \
                1) Summary, 2) Key points, 3) Vocabulary highlights, 4) Grammar notes."
                    .to_string()
            }
        };

        let messages = vec![
            json!({"role": "system", "content": system_prompt}),
            json!({"role": "user", "content": request.text}),
        ];

        let result = self.make_request(messages, Some(0.5)).await?;

        Ok(AnalysisResponse {
            analysis_type: request.analysis_type,
            result,
            metadata: None,
        })
    }

    pub async fn chat(&self, request: ChatRequest) -> Result<ChatResponse, String> {
        let messages: Vec<Value> = request
            .messages
            .into_iter()
            .map(|msg| {
                json!({
                    "role": msg.role,
                    "content": msg.content
                })
            })
            .collect();

        let content = self.make_request(messages, request.temperature).await?;

        Ok(ChatResponse {
            content,
            model: self.model.clone(),
            tokens_used: None,
        })
    }

    pub async fn segment_translate_explain(
        &self,
        text: String,
        target_language: String,
    ) -> Result<crate::types::SegmentExplanation, String> {
        println!("Starting segment_translate_explain for text: '{}'...", text.chars().take(50).collect::<String>());
        let native_language_name = match target_language.as_str() {
            "zh" | "zh-CN" => "中文",
            "en" => "英文",
            "ja" => "日语",
            "ko" => "韩语",
            _ => "中文",
        };

        let system_prompt = format!(
            r#"你是一个专业的语言学习助手。用户的母语是{0}。请对以下文本段落进行全面的分析，并严格按照下面的JSON格式返回结果，不要添加任何额外的解释或说明。

用户语言设置：
- 母语：{0}

要分析的文本：
---
{1}
---

请根据用户的语言设置，严格按照以下JSON结构返回，所有key都必须是英文：
{{
  "translation": "将原文翻译成{0}，要求自然流畅，符合{0}的表达习惯",
  "explanation": "使用{0}对整个段落进行详细讲解，使用Markdown格式。包含对上下文、语气、文化背景的说明",
  "vocabulary": [
    {{
      "word": "要分析的单词或短语(不要展示读音，这里写上原文中的单词即可)",
      "reading": "该单词或短语的读音（如果是日语，则使用日语的五十音平假名，如果是英语，则使用英语的音标）",
      "meaning": "单词或短语在当前语境下的核心释义，用{0}解释",
      "usage": "用{0}对用法和搭配进行详细说明",
      "example": "使用该单词或短语的例句，并附上{0}翻译"
    }}
  ],
  "grammar_points": [
    {{
      "point": "要分析的语法点名称",
      "explanation": "用{0}对该语法点进行详细解释",
      "example": "使用该语法点的例句，并附上{0}翻译"
    }}
  ],
  "cultural_context": "如果文本涉及特定文化背景，用{0}进行说明",
  "difficulty_level": "beginner | intermediate | advanced",
  "learning_tips": "用{0}提供针对该段落的学习建议"
}}

请确保所有解释、说明、建议都使用{0}。"#,
            native_language_name, text
        );

        let messages = vec![
            json!({"role": "system", "content": system_prompt}),
            json!({"role": "user", "content": format!("请分析这个段落：{}", text)}),
        ];

        println!("Sending request to AI provider: {}", self.provider);
        let content = self.make_request(messages, Some(0.3)).await?;
        println!("Received response from AI provider. Content length: {}", content.len());

        // Parse JSON from content
        // Handle markdown code blocks if present
        let cleaned_content = if let Some(start) = content.find("```json") {
            if let Some(end) = content[start..].find("```") {
                 // start + 7 to skip ```json
                 // find next ```
                 let json_part = &content[start+7..];
                 if let Some(end_idx) = json_part.find("```") {
                     json_part[..end_idx].trim()
                 } else {
                     content.trim()
                 }
            } else {
                content.trim()
            }
        } else if let Some(start) = content.find('{') {
             if let Some(end) = content.rfind('}') {
                 &content[start..=end]
             } else {
                 content.trim()
             }
        } else {
            content.trim()
        };
        
        // Remove markdown block if it was ``` without json
        let cleaned_content = cleaned_content.trim_start_matches("```json").trim_start_matches("```").trim_end_matches("```").trim();

        println!("Attempting to parse JSON content...");
        let explanation: crate::types::SegmentExplanation = serde_json::from_str(cleaned_content)
            .map_err(|e| format!("Failed to parse JSON response: {}. Content: {}", e, cleaned_content))?;

        println!("Successfully parsed explanation JSON.");
        Ok(explanation)
    }
}

// Simple in-memory cache for AI service instances
use std::sync::Arc;
use tokio::sync::RwLock;

// Newtype wrapper to allow Default implementation
#[derive(Clone)]
pub struct AIServiceCache(Arc<RwLock<Option<AIService>>>);

impl Default for AIServiceCache {
    fn default() -> Self {
        Self(Arc::new(RwLock::new(None)))
    }
}

impl AIServiceCache {
    pub async fn read(&self) -> tokio::sync::RwLockReadGuard<'_, Option<AIService>> {
        self.0.read().await
    }

    pub async fn write(&self) -> tokio::sync::RwLockWriteGuard<'_, Option<AIService>> {
        self.0.write().await
    }
}

pub async fn get_or_create_ai_service(
    cache: &AIServiceCache,
    api_key: String,
    provider: String,
    model: String,
) -> Result<(), String> {
    let mut cache_guard = cache.write().await;
    *cache_guard = Some(AIService::new(api_key, provider, model));
    Ok(())
}

pub async fn get_ai_service(cache: &AIServiceCache) -> Result<AIService, String> {
    let cache_guard = cache.read().await;
    cache_guard
        .as_ref()
        .map(|service| AIService {
            client: Client::new(),
            api_key: service.api_key.clone(),
            provider: service.provider.clone(),
            model: service.model.clone(),
        })
        .ok_or_else(|| "AI service not initialized".to_string())
}
