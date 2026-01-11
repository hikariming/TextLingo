import type { AppConfig } from "./tauri";
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { SegmentExplanation } from "../types";

/**
 * API client for backend services
 */
export class ApiClient {
  private backendUrl: string | null = null;
  private authToken: string | null = null;

  constructor(config?: AppConfig) {
    if (config) {
      this.updateConfig(config);
    }
  }

  updateConfig(config: AppConfig) {
    this.backendUrl = config.backend_url || null;
    this.authToken = config.auth_token || null;
  }

  private getBaseUrl(): string {
    // Default to port 4000 (Node API) instead of 8000 (Python API)
    return this.backendUrl || "http://localhost:4000";
  }

  /**
   * Fetch content from a URL using the backend Dify workflow
   * This matches the Flutter implementation using webpage-to-text workflow
   */
  async fetchUrlContent(url: string): Promise<{ title: string; content: string }> {
    if (!this.backendUrl || !this.authToken) {
      throw new Error("Backend not configured. Please configure backend URL and auth token in settings.");
    }

    try {
      const formData = new FormData();
      formData.append("flow_id", "webpage-to-text");
      formData.append("inputs", JSON.stringify({ url }));

      const response = await fetch(`${this.getBaseUrl()}/api/v1/dify/workflow/run`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${this.authToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Extract content from Dify workflow response
      const outputs = data.data?.outputs || {};
      const content = outputs.text || outputs.content || outputs.result || outputs.answer || "";

      // Extract title from URL if not in response
      const title = outputs.title || this.extractTitleFromUrl(url);

      return { title, content };
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Failed to fetch URL content");
    }
  }

  /**
   * Fallback: Use local Tauri command to fetch URL content
   * This uses the Rust implementation with html2text
   */
  async fetchUrlContentLocal(url: string): Promise<{ title: string; content: string }> {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke("fetch_url_content", { url }) as { title: string; content: string };
  }

  /**
   * Check if backend is configured and available
   */
  isBackendConfigured(): boolean {
    return !!(this.backendUrl && this.authToken);
  }

  /**
   * Test backend connection
   */
  async testConnection(): Promise<boolean> {
    if (!this.backendUrl) return false;

    try {
      const response = await fetch(`${this.getBaseUrl()}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  private extractTitleFromUrl(url: string): string {
    try {
      const urlObj = new URL(url);
      const pathParts = urlObj.pathname.split("/").filter(Boolean);
      const lastPart = pathParts[pathParts.length - 1];
      if (lastPart) {
        return lastPart
          .replace(/[-_]/g, " ")
          .replace(/\.[^/.]+$/, "")
          .split(" ")
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(" ");
      }
      return urlObj.hostname;
    } catch {
      return "Untitled";
    }
  }

  // --- Novel Chat API Methods ---

  async createNovelSession(data: CreateNovelSessionRequest): Promise<CreateNovelSessionResponse> {
    if (!this.backendUrl || !this.authToken) throw new Error("Backend not configured");

    const response = await fetch(`${this.getBaseUrl()}/api/v2/novel-chat/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.authToken}`
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${await response.text()}`);
    }

    return response.json();
  }

  async getQuickActions(params: {
    selected_text?: string;
    chapter_id?: string;
    user_language?: string;
    novel_id?: string;
  }): Promise<QuickAction[]> {
    if (!this.backendUrl || !this.authToken) throw new Error("Backend not configured");

    const queryParams = new URLSearchParams();
    if (params.selected_text) queryParams.append('selected_text', params.selected_text);
    if (params.chapter_id) queryParams.append('chapter_id', params.chapter_id);
    if (params.user_language) queryParams.append('user_language', params.user_language);
    if (params.novel_id) queryParams.append('novel_id', params.novel_id);

    const response = await fetch(`${this.getBaseUrl()}/api/v2/novel-chat/quick-actions?${queryParams}`, {
      headers: {
        'Authorization': `Bearer ${this.authToken}`
      }
    });

    if (!response.ok) throw new Error('Failed to fetch quick actions');
    return response.json();
  }

  async getNovelContext(novelId: string, chapterId?: string): Promise<any> {
    if (!this.backendUrl || !this.authToken) throw new Error("Backend not configured");

    const url = chapterId
      ? `${this.getBaseUrl()}/api/v2/novel-chat/context/${novelId}?chapterId=${chapterId}`
      : `${this.getBaseUrl()}/api/v2/novel-chat/context/${novelId}`;

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${this.authToken}` }
    });

    if (!response.ok) throw new Error('Failed to fetch context');
    return response.json();
  }

  async streamNovelChat(
    data: NovelChatMessageRequest,
    onChunk: (chunk: StreamChunk) => void,
    onError?: (error: Error) => void,
    signal?: AbortSignal
  ): Promise<void> {
    if (!this.backendUrl || !this.authToken) throw new Error("Backend not configured");

    await fetchEventSource(`${this.getBaseUrl()}/api/v2/novel-chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.authToken}`
      },
      body: JSON.stringify(data),
      signal,
      onmessage(event) {
        try {
          if (!event.data || event.data.trim() === '') return;
          const chunk = JSON.parse(event.data) as StreamChunk;
          onChunk(chunk);
        } catch (error) {
          console.error('Failed to parse chunk:', error);
        }
      },
      onerror(error) {
        console.error('Stream error:', error);
        if (onError) onError(error as Error);
      },
    });
  }

  async segmentTranslateExplainStream(
    data: {
      article_id: string;
      segment_id: string;
      aimodel_id?: string;
      force_regenerate?: boolean;
      auto_charge?: boolean;
    },
    onChunk: (chunk: SSEChunk) => void,
    _onError?: (error: Error) => void, // Deprecated, use try/catch
    signal?: AbortSignal
  ): Promise<void> {
    const baseUrl = this.getBaseUrl().replace(/\/$/, ""); // Remove trailing slash
    const finalUrl = baseUrl.endsWith("/api/v1")
      ? `${baseUrl}/ai-enhanced/segment-translate-explain-stream`
      : `${baseUrl}/api/v1/ai-enhanced/segment-translate-explain-stream`;

    if (!this.backendUrl || !this.authToken) throw new Error("Backend not configured");

    await fetchEventSource(finalUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.authToken}`
      },
      body: JSON.stringify(data),
      signal,
      async onopen(response) {
        if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
          return; // everything's good
        } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
          // Client-side errors are usually non-retriable
          const errorText = await response.text().catch(() => "");
          throw new Error(`Server Error ${response.status}: ${errorText}`);
        } else {
          // 5xx errors might be retriable, but for now we fail fast to show user feedback
          const errorText = await response.text().catch(() => "");
          throw new Error(`Server Error ${response.status}: ${errorText}`);
        }
      },
      onmessage(event) {
        try {
          if (!event.data || event.data.trim() === '') return;
          const chunk = JSON.parse(event.data) as SSEChunk;
          onChunk(chunk);
        } catch (error) {
          console.error('Failed to parse chunk:', error);
        }
      },
      onerror(error) {
        console.error('Stream error:', error);
        // Throwing here makes the await fetchEventSource reject
        throw error;
      },
    });
  }
}

export interface SSEChunk {
  event: 'start' | 'chunk' | 'partial_update' | 'complete' | 'error' | 'warning';
  content?: string;
  message?: string;
  updates?: Record<string, any>;
  parsed_sections?: SegmentExplanation;
  full_response?: string;
  cached?: boolean;
}

// Novel Chat Types
export interface NovelSession {
  id: string;
  title: string;
  created_at: string;
  model_id: string;
  metadata: {
    type: 'novel_reading';
    novel_id: string;
    chapter_id?: string;
  };
}

export interface NovelContext {
  id: string;
  title: string;
  author: string;
  language: string;
  genre?: string;
  total_chapters?: number;
  description?: string;
}

export interface CreateNovelSessionRequest {
  novel_id: string;
  chapter_id?: string;
  model_id?: string;
  user_language: string;
  novel_language?: string;
  title?: string;
}

export interface NovelChatMessageRequest {
  session_id: string;
  message: string;
  selected_text?: string;
  current_segment?: string;
  reading_progress?: number;
  model_config?: {
    id?: string;
    temperature?: number;
    max_tokens?: number;
  };
  previous_questions?: string[];
}

export interface QuickAction {
  action: 'translate' | 'explain' | 'grammar' | 'vocabulary' | 'culture' | 'plot' | 'character' | 'summary';
  label: string;
  description: string;
  prompt_template: string;
  icon?: string;
  estimated_points?: number;
}

export interface CreateNovelSessionResponse {
  session: NovelSession;
  novel_context: NovelContext;
  quick_actions: QuickAction[];
}

export interface StreamChunk {
  type: 'connected' | 'message' | 'done' | 'error';
  content?: {
    id?: string;
    content?: string;
    [key: string]: any;
  } | string;
  error?: string;
}

// Singleton instance
let apiClient: ApiClient | null = null;

export function getApiClient(config?: AppConfig): ApiClient {
  if (!apiClient) {
    apiClient = new ApiClient(config);
  } else if (config) {
    apiClient.updateConfig(config);
  }
  return apiClient;
}
