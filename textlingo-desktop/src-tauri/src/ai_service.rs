use regex::Regex;
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
            json!({"role": "system", "content": system_prompt}),
            json!({"role": "user", "content": format!("Analyze this: {}", text)}),
        ];

        println!("Sending request to AI provider: {}", self.provider);
        let content = self.make_request(messages, Some(0.3)).await?;
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
