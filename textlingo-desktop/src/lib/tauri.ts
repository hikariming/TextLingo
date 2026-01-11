// Type definitions for Tauri commands

export interface ModelConfig {
  id: string;
  name: string;
  api_key: string;
  api_provider: string;
  model: string;
  is_default: boolean;
  created_at?: string;
}

export interface AppConfig {
  // Legacy fields (deprecated, for backward compatibility)
  api_key?: string;
  api_provider?: string;
  model?: string;
  // New model config system
  active_model_id?: string;
  model_configs?: ModelConfig[];
  // Other settings
  target_language: string;
  interface_language?: string;
  // Backend API URL for services like webpage fetching
  backend_url?: string;
  // Auth token for backend API
  auth_token?: string;
}

import { Article } from "../types";

export { type Article };

export type AnalysisType = "summary" | "key_points" | "vocabulary" | "grammar" | "full";

export interface TranslationRequest {
  text: string;
  target_language: string;
  context?: string;
}

export interface TranslationResponse {
  translated_text: string;
  original_text: string;
  model_used: string;
}

export interface AnalysisRequest {
  text: string;
  analysis_type: AnalysisType;
}

export interface AnalysisResponse {
  analysis_type: AnalysisType;
  result: string;
  metadata?: unknown;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  model: string;
  temperature?: number;
}

export interface ChatResponse {
  content: string;
  model: string;
  tokens_used?: number;
}

// Tauri command type imports
export type TauriCommand = {
  init_app: () => Promise<string>;
  get_config: () => Promise<AppConfig | null>;
  save_config_cmd: (config: AppConfig) => Promise<string>;
  set_api_key: (apiKey: string, provider: string, model: string) => Promise<string>;
  create_article: (
    title: string,
    content: string,
    sourceUrl?: string
  ) => Promise<Article>;
  get_article: (id: string) => Promise<Article>;
  list_articles_cmd: () => Promise<Article[]>;
  update_article: (
    id: string,
    title?: string,
    content?: string,
    sourceUrl?: string,
    translated?: boolean
  ) => Promise<Article>;
  update_article_segment: (
    articleId: string,
    segmentId: string,
    explanation?: any,
    reading?: string,
    translation?: string
  ) => Promise<Article>;
  delete_article_cmd: (id: string) => Promise<void>;
  translate_text: (request: TranslationRequest) => Promise<TranslationResponse>;
  analyze_text: (request: AnalysisRequest) => Promise<AnalysisResponse>;
  chat_completion: (request: ChatRequest) => Promise<ChatResponse>;
  translate_article: (
    articleId: string,
    targetLanguage: string
  ) => Promise<Article>;
  analyze_article: (
    articleId: string,
    analysisType: AnalysisType
  ) => Promise<string>;
};
