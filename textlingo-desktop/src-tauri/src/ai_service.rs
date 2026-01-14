use regex::Regex;
use futures::StreamExt;
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
    /// Custom base URL for openai-compatible, ollama, lmstudio providers
    base_url: Option<String>,
}

// Default base URLs for local providers
const OLLAMA_DEFAULT_URL: &str = "http://localhost:11434/v1/chat/completions";
const LMSTUDIO_DEFAULT_URL: &str = "http://localhost:1234/v1/chat/completions";

impl AIService {
    pub fn new(api_key: String, provider: String, model: String) -> Self {
        Self::with_base_url(api_key, provider, model, None)
    }

    pub fn with_base_url(api_key: String, provider: String, model: String, base_url: Option<String>) -> Self {
        Self {
            client: Client::new(),
            api_key,
            provider,
            model,
            base_url,
        }
    }

    fn get_api_url(&self) -> String {
        // If custom base_url is provided, use it (append /chat/completions if needed)
        if let Some(ref url) = self.base_url {
            let trimmed = url.trim_end_matches('/');
            if trimmed.ends_with("/chat/completions") {
                return trimmed.to_string();
            } else {
                return format!("{}/chat/completions", trimmed);
            }
        }
        
        // Default URLs for known providers
        match self.provider.as_str() {
            "openrouter" => OPENROUTER_API_URL.to_string(),
            "deepseek" => DEEPSEEK_API_URL.to_string(),
            "siliconflow" => SILICONFLOW_API_URL.to_string(),
            "302ai" => API_302AI_URL.to_string(),
            "google" | "google-ai-studio" => format!(
                "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent",
                self.model.strip_prefix("models/").unwrap_or(&self.model)
            ),
            "ollama" => OLLAMA_DEFAULT_URL.to_string(),
            "lmstudio" => LMSTUDIO_DEFAULT_URL.to_string(),
            "openai-compatible" => {
                // Should not reach here if base_url is properly set
                OPENAI_API_URL.to_string()
            },
            _ => OPENAI_API_URL.to_string(),
        }
    }

    /// 检查是否为 Google 类型的 provider（需要使用 X-goog-api-key 认证）
    fn is_google_provider(&self) -> bool {
        self.provider == "google" || self.provider == "google-ai-studio"
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

        let mut request = self
            .client
            .post(self.get_api_url())
            .header("Content-Type", "application/json");
        
        // Only add Authorization header if API key is provided (local services may not need it)
        if !self.api_key.is_empty() {
            request = request.header("Authorization", format!("Bearer {}", self.api_key));
        }

        let response = request
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

    async fn make_google_request(
        &self,
        contents: Vec<Value>,
        temperature: Option<f32>,
    ) -> Result<String, String> {
        let request_body = json!({
            "contents": contents,
            "generationConfig": {
                "temperature": temperature.unwrap_or(0.7)
            }
        });

        let response = self
            .client
            .post(self.get_api_url())
            .header("Content-Type", "application/json")
            .header("X-goog-api-key", &self.api_key)
            .json(&request_body)
            .send()
            .await
            .map_err(|e| format!("Failed to send request: {}", e))?;

        if !response.status().is_success() {
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(format!("Google API error: {}", error_text));
        }

        let response_json: Value = response
            .json()
            .await
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        // Google response structure: { candidates: [ { content: { parts: [ { text: "..." } ] } } ] }
        response_json["candidates"][0]["content"]["parts"][0]["text"]
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

        let translated_text = if self.is_google_provider() {
            // 使用 Google API 格式
            let contents = vec![
                json!({
                    "role": "user",
                    "parts": [{"text": format!("{}\n\n{}", system_prompt, request.text)}]
                })
            ];
            self.make_google_request(contents, Some(0.3)).await?
        } else {
            let messages = vec![
                json!({"role": "system", "content": system_prompt}),
                json!({"role": "user", "content": request.text.clone()}),
            ];
            self.make_request(messages, Some(0.3)).await?
        };

        Ok(TranslationResponse {
            translated_text,
            original_text: request.text,
            model_used: self.model.clone(),
        })
    }

    /// 批量翻译多个文本段落（最多30条）
    /// 返回 Vec<(id, translation)>
    pub async fn batch_translate(
        &self,
        items: Vec<(String, String)>,  // Vec<(id, text)>
        target_language: &str,
    ) -> Result<Vec<(String, String)>, String> {
        if items.is_empty() {
            return Ok(vec![]);
        }

        // 构建批量翻译提示词
        let mut prompt = format!(
            "将以下编号的文本翻译成{}。严格按照JSON数组格式返回，每项包含id和translation字段。\n\n",
            target_language
        );
        prompt.push_str("待翻译文本：\n");
        for (id, text) in &items {
            prompt.push_str(&format!("[{}] {}\n", id, text));
        }
        prompt.push_str("\n返回格式示例：\n");
        prompt.push_str(r#"[{"id": "xxx", "translation": "翻译结果"}, ...]"#);

        let response_text = if self.is_google_provider() {
            let contents = vec![
                json!({
                    "role": "user",
                    "parts": [{"text": prompt}]
                })
            ];
            self.make_google_request(contents, Some(0.3)).await?
        } else {
            let messages = vec![
                json!({"role": "system", "content": "你是专业翻译助手，将文本翻译并返回JSON格式结果。"}),
                json!({"role": "user", "content": prompt}),
            ];
            self.make_request(messages, Some(0.3)).await?
        };

        // 解析返回的 JSON 数组
        let json_str = Self::extract_json_array(&response_text);
        let parsed: Vec<Value> = serde_json::from_str(&json_str)
            .map_err(|e| format!("Failed to parse batch translation response: {} - raw: {}", e, json_str))?;

        let mut results = Vec::new();
        for item in parsed {
            if let (Some(id), Some(translation)) = (
                item.get("id").and_then(|v| v.as_str()),
                item.get("translation").and_then(|v| v.as_str()),
            ) {
                results.push((id.to_string(), translation.to_string()));
            }
        }

        Ok(results)
    }

    /// 从响应中提取 JSON 数组
    fn extract_json_array(content: &str) -> String {
        // 尝试提取 markdown 代码块
        if let Some(start) = content.find("```json") {
            if let Some(end) = content[start..].rfind("```") {
                if end > 7 {
                    return content[start+7..start+end].trim().to_string();
                }
            }
        }
        
        if let Some(start) = content.find("```") {
            if let Some(end_offset) = content[start+3..].find("```") {
                let end = start + 3 + end_offset;
                return content[start+3..end].trim().to_string();
            }
        }

        // 提取 JSON 数组 (以 [ 开头)
        if let Some(start_idx) = content.find('[') {
            let mut balance = 0;
            let mut end_idx = start_idx;
            let mut found_end = false;
            
            for (i, c) in content[start_idx..].char_indices() {
                match c {
                    '[' => balance += 1,
                    ']' => {
                        balance -= 1;
                        if balance == 0 {
                            end_idx = start_idx + i;
                            found_end = true;
                            break;
                        }
                    },
                    _ => {}
                }
            }
            
            if found_end {
                return content[start_idx..=end_idx].to_string();
            }
        }

        content.trim().to_string()
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

        let result = if self.is_google_provider() {
            // 使用 Google API 格式
            let contents = vec![
                json!({
                    "role": "user",
                    "parts": [{"text": format!("{}\n\n{}", system_prompt, request.text)}]
                })
            ];
            self.make_google_request(contents, Some(0.5)).await?
        } else {
            let messages = vec![
                json!({"role": "system", "content": system_prompt}),
                json!({"role": "user", "content": request.text}),
            ];
            self.make_request(messages, Some(0.5)).await?
        };

        Ok(AnalysisResponse {
            analysis_type: request.analysis_type,
            result,
            metadata: None,
        })
    }

    pub async fn chat(&self, request: ChatRequest) -> Result<ChatResponse, String> {
        if self.provider == "google" || self.provider == "google-ai-studio" {
            return self.chat_google(request).await;
        }

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



// ... imports

    pub async fn stream_chat<F>(
        &self,
        request: ChatRequest,
        callback: F,
    ) -> Result<String, String>
    where
        F: Fn(String) + Send + Sync + 'static,
    {
        // For now, only support standard OpenAI SSE streaming
        // Google streaming requires different handling, fallback to normal chat
        if self.is_google_provider() {
            let response = self.chat(request).await?;
            callback(response.content.clone());
            return Ok(response.content);
        }

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

        let request_body = json!({
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature.unwrap_or(0.7),
            "stream": true
        });

        let mut request_builder = self
            .client
            .post(self.get_api_url())
            .header("Content-Type", "application/json");
        
        if !self.api_key.is_empty() {
            request_builder = request_builder.header("Authorization", format!("Bearer {}", self.api_key));
        }

        let response = request_builder
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

        let mut stream = response.bytes_stream();
        let mut full_content = String::new();

        while let Some(item) = stream.next().await {
            let chunk = item.map_err(|e| format!("Error reading stream: {}", e))?;
            let chunk_str = String::from_utf8_lossy(&chunk);
            
            for line in chunk_str.lines() {
                let line = line.trim();
                if line.is_empty() || !line.starts_with("data: ") {
                    continue;
                }

                let data = &line[6..];
                if data == "[DONE]" {
                    continue;
                }

                if let Ok(json) = serde_json::from_str::<Value>(data) {
                    if let Some(content) = json["choices"][0]["delta"]["content"].as_str() {
                        if !content.is_empty() {
                            full_content.push_str(content);
                            callback(content.to_string());
                        }
                    }
                }
            }
        }

        Ok(full_content)
    }

    async fn chat_google(&self, request: ChatRequest) -> Result<ChatResponse, String> {
        let contents: Vec<Value> = request
            .messages
            .into_iter()
            .map(|msg| {
                let role = if msg.role == "assistant" { "model" } else { "user" };
                
                let parts = match msg.content {
                    crate::types::ChatContent::Text(text) => vec![json!({"text": text})],
                    crate::types::ChatContent::Parts(parts) => parts.into_iter().map(|part| {
                        if let Some(text) = part.text {
                            json!({"text": text})
                        } else if let Some(file) = part.file_data {
                            json!({
                                "inlineData": {
                                    "mimeType": file.mime_type,
                                    "data": file.data
                                }
                            })
                        } else {
                            json!({"text": ""}) // Fallback
                        }
                    }).collect()
                };

                json!({
                    "role": role,
                    "parts": parts
                })
            })
            .collect();

        let content = self.make_google_request(contents, request.temperature).await?;

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
            "en" => "English",
            "ja" => "Japanese",
            "ko" => "Korean",
            _ => "中文",
        };

        let system_prompt = format!(
            r#"You are a professional language learning assistant. The user's native language is {0}. Please analyze the following text segment comprehensively and return the result strictly in the following JSON format. Do NOT add any extra explanations or markdown formatting outside the JSON block.

User's Native Language: {0}

Text to Analyze:
---
{1}
---

Please strictly adhere to this JSON structure (all keys must be in English):
{{
  "translation": "Translate the text into natural, fluent {0}",
  "explanation": "Explain the text in {0}, covering context, tone, and cultural background. Use Markdown formatting.",
  "vocabulary": [
    {{
      "word": "The word or phrase from the text",
      "reading": "Pronunciation/Reading (e.g., Hiragana for Japanese, IPA for English)",
      "meaning": "Core meaning in the context, explained in {0}",
      "usage": "Usage notes and collocations in {0}",
      "example": "Example sentence containing the word, with {0} translation"
    }}
  ],
  "grammar_points": [
    {{
      "point": "Name of the grammar point",
      "explanation": "Detailed explanation in {0}",
      "example": "Example sentence using the grammar point, with {0} translation"
    }}
  ],
  "cultural_context": "Cultural background info in {0} (if applicable, else null)",
  "difficulty_level": "beginner | intermediate | advanced",
  "learning_tips": "Learning advice for this segment in {0}"
}}

Ensure all explanations, meanings, and descriptive text are written in {0}."#,
            native_language_name, text
        );

        let messages = vec![
            json!({"role": "system", "content": system_prompt.clone()}),
            json!({"role": "user", "content": format!("Analyze this: {}", text)}),
        ];

        println!("Sending request to AI provider: {}", self.provider);
        let content = if self.is_google_provider() {
            // 使用 Google API 格式
            let contents = vec![
                json!({
                    "role": "user",
                    "parts": [{"text": format!("{}\n\nAnalyze this: {}", system_prompt, text)}]
                })
            ];
            self.make_google_request(contents, Some(0.3)).await?
        } else {
            self.make_request(messages, Some(0.3)).await?
        };
        println!("Received response from AI provider. Content length: {}", content.len());

        // Robust JSON extraction
        let json_str = Self::extract_json(&content);
        println!("Extracted JSON candidate length: {}", json_str.len());

        // Try parsing, with repair fallback
        match serde_json::from_str::<crate::types::SegmentExplanation>(&json_str) {
            Ok(explanation) => {
                println!("Successfully parsed explanation JSON.");
                Ok(explanation)
            },
            Err(e) => {
                println!("Initial JSON parse failed: {}. Attempting repair...", e);
                let repaired_json = Self::repair_json(&json_str);
                match serde_json::from_str::<crate::types::SegmentExplanation>(&repaired_json) {
                    Ok(explanation) => {
                        println!("Successfully parsed repaired JSON.");
                        Ok(explanation)
                    },
                    Err(e2) => {
                        println!("Failed to parse repaired JSON: {}.", e2);
                        println!("Original content: {}", content);
                        Err(format!("Failed to parse AI response. Error: {}. Content: {}", e2, repaired_json))
                    }
                }
            }
        }
    }

    /// Extracts the likely JSON part from a string.
    /// Prioritizes code blocks, then finding the outermost matching braces.
    fn extract_json(content: &str) -> String {
        // 1. Try finding markdown code blocks explicitly
        if let Some(start) = content.find("```json") {
            if let Some(end) = content[start..].rfind("```") {
                if end > 7 { // Ensure there's content between ```json and ```
                     return content[start+7..start+end].trim().to_string();
                }
            }
        }
        
        // 2. Try generic code blocks
        if let Some(start) = content.find("```") {
             // Find the next ``` 
             if let Some(end_offset) = content[start+3..].find("```") {
                 let end = start + 3 + end_offset;
                 return content[start+3..end].trim().to_string();
             }
        }

        // 3. Robust brace counting to find the main JSON object
        if let Some(start_idx) = content.find('{') {
             let mut balance = 0;
             let mut end_idx = start_idx;
             let mut found_end = false;
             
             // Iterate through chars to find the matching closing brace
             for (i, c) in content[start_idx..].char_indices() {
                 match c {
                     '{' => balance += 1,
                     '}' => {
                         balance -= 1;
                         if balance == 0 {
                             end_idx = start_idx + i;
                             found_end = true;
                             break;
                         }
                     },
                     _ => {}
                 }
             }
             
             if found_end {
                 return content[start_idx..=end_idx].to_string();
             }
        }

        // 4. Fallback to just trimming
        content.trim().trim_start_matches("```json").trim_start_matches("```").trim_end_matches("```").to_string()
    }

    /// Attempts to repair common JSON errors from LLMs
    fn repair_json(json_str: &str) -> String {
        // Use regex to remove trailing commas which are invalid in JSON but common in LLM output
        // Invalid: { "a": 1, } -> Valid: { "a": 1 }
        // Invalid: [ "a", ] -> Valid: [ "a" ]
        
        let mut repaired = json_str.to_string();

        if let Ok(re) = Regex::new(r",(\s*\})") {
            repaired = re.replace_all(&repaired, "$1").to_string();
        }

        if let Ok(re) = Regex::new(r",(\s*\])") {
            repaired = re.replace_all(&repaired, "$1").to_string();
        }
        
        // Normalize quotes
        repaired = repaired.replace("“", "\"").replace("”", "\"");

        repaired
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
    get_or_create_ai_service_with_base_url(cache, api_key, provider, model, None).await
}

pub async fn get_or_create_ai_service_with_base_url(
    cache: &AIServiceCache,
    api_key: String,
    provider: String,
    model: String,
    base_url: Option<String>,
) -> Result<(), String> {
    let mut cache_guard = cache.write().await;
    *cache_guard = Some(AIService::with_base_url(api_key, provider, model, base_url));
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
            base_url: service.base_url.clone(),
        })
        .ok_or_else(|| "AI service not initialized".to_string())
}
