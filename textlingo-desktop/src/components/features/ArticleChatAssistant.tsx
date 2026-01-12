import React, { useState, useEffect, useRef } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import {
    Send, Bot, User, Sparkles, Languages, X,
    Loader2, Copy, Paperclip, File as FileIcon
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";
import {
    getApiClient,
    NovelSession,
    QuickAction
} from "../../lib/api";
import { invoke } from "@tauri-apps/api/core";

// Simple Card component since we don't have one in UI
const Card = ({ className, children }: { className?: string; children: React.ReactNode }) => (
    <div className={cn("bg-card border border-border rounded-lg", className)}>
        {children}
    </div>
);

interface ArticleChatAssistantProps {
    articleId: string;
    articleTitle: string;
    sourceLanguage?: string; // e.g. "ja", "en"
    targetLanguage: string; // e.g. "zh-CN"
    selectedText?: string;
    currentSegment?: string;
    readingProgress?: number;
    onClose?: () => void;
    className?: string;
}

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
    metadata?: {
        selected_text?: string;
        action_type?: string;
        file_attachment?: {
            name: string;
            type: string;
            data: string; // Base64
        };
    };
}

interface Attachment {
    file: File;
    preview?: string;
    base64: string;
}

export function ArticleChatAssistant({
    articleId,
    articleTitle,
    sourceLanguage = "auto",
    targetLanguage,
    selectedText,
    currentSegment,
    readingProgress,
    onClose,
    className,
}: ArticleChatAssistantProps) {
    const { t, i18n } = useTranslation();
    const [session, setSession] = useState<NovelSession | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isInitializing, setIsInitializing] = useState(true);
    const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
    const [activeTab, setActiveTab] = useState("chat");
    const [attachment, setAttachment] = useState<Attachment | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Initialize session
    useEffect(() => {
        initializeSession();
    }, [articleId]);

    // Load quick actions when selected text changes
    useEffect(() => {
        if (selectedText) {
            loadQuickActions();
        }
    }, [selectedText]);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        // Also scroll when attachment changes to keep input visible
        if (attachment) {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, attachment]);

    const initializeSession = async () => {
        try {
            setIsInitializing(true);
            const api = getApiClient();

            // Try connection to remote
            if (api.isBackendConfigured()) {
                await api.testConnection(); // Verify connectivity
                try {
                    const response = await api.createNovelSession({
                        novel_id: articleId,
                        user_language: targetLanguage,
                        novel_language: sourceLanguage,
                        title: `${articleTitle} - Assistant`
                    });
                    setSession(response.session);
                    setQuickActions(response.quick_actions);
                } catch (e) {
                    console.warn("Failed to create remote session, falling back to local mode", e);
                }
            } else {
                console.log("Backend not configured, using local mode");
            }

            const welcomeMessage = i18n.language.startsWith('zh')
                ? `你好！我是你的阅读助手。我可以帮你翻译、解释文本，分析语法，或讨论文章内容。`
                : `Hello! I'm your reading assistant. I can help translate, explain text, analyze grammar, or discuss the article.`;

            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: welcomeMessage,
                timestamp: new Date()
            }]);
        } catch (error) {
            console.error('Failed to initialize session:', error);
            // Don't show error to user, just fallback silently or show welcome
        } finally {
            setIsInitializing(false);
        }
    };

    const loadQuickActions = async () => {
        const api = getApiClient();
        if (!session || !api.isBackendConfigured()) return;

        try {
            const actions = await api.getQuickActions({
                selected_text: selectedText,
                user_language: targetLanguage,
                novel_id: articleId
            });
            setQuickActions(actions);
        } catch (error) {
            console.error('Failed to load quick actions:', error);
        }
    };

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Limit size? 10MB
        if (file.size > 10 * 1024 * 1024) {
            alert("File is too large (max 10MB)");
            return;
        }

        const reader = new FileReader();
        reader.onload = (ev) => {
            const base64 = ev.target?.result as string;
            // Extract base64 part
            const base64Data = base64.split(',')[1];
            setAttachment({
                file,
                preview: file.type.startsWith('image/') ? base64 : undefined,
                base64: base64Data
            });
        };
        reader.readAsDataURL(file);
    };

    const handleSendMessage = async (message?: string, actionType?: string) => {
        const messageToSend = message || input.trim();
        if ((!messageToSend && !attachment) || isLoading) return;

        if (!message) {
            setInput("");
            setAttachment(null);
        }

        const currentAttachment = attachment;

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: messageToSend,
            timestamp: new Date(),
            metadata: {
                selected_text: selectedText,
                action_type: actionType,
                file_attachment: currentAttachment ? {
                    name: currentAttachment.file.name,
                    type: currentAttachment.file.type,
                    data: currentAttachment.base64
                } : undefined
            }
        };
        setMessages(prev => [...prev, userMessage]);

        const assistantMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true
        };
        setMessages(prev => [...prev, assistantMessage]);

        setIsLoading(true);

        const api = getApiClient();

        // Check if we use Remote or Local
        // Use Remote ONLY if session exists AND no file attachment (unless remote supports it, which novel-chat doesn't yet)
        // If file attachment exists, FORCE Local.
        const useRemote = session && !currentAttachment && api.isBackendConfigured();

        if (useRemote) {
            // Remote Streaming Logic
            try {
                abortControllerRef.current = new AbortController();
                await api.streamNovelChat(
                    {
                        session_id: session!.id,
                        message: messageToSend,
                        selected_text: selectedText,
                        current_segment: currentSegment,
                        reading_progress: readingProgress,
                    },
                    (chunk) => {
                        if (chunk.type === 'message' || (chunk.type as any) === 'content') {
                            const content = typeof chunk.content === 'string'
                                ? chunk.content
                                : (chunk.content?.content || '');

                            if (content) {
                                setMessages(prev => {
                                    const newMessages = [...prev];
                                    const lastMessage = newMessages[newMessages.length - 1];
                                    if (lastMessage.role === 'assistant') {
                                        lastMessage.content += content;
                                    }
                                    return newMessages;
                                });
                            }
                        } else if (chunk.type === 'done') {
                            setMessages(prev => {
                                const newMessages = [...prev];
                                const lastMessage = newMessages[newMessages.length - 1];
                                if (lastMessage.role === 'assistant') {
                                    lastMessage.isStreaming = false;
                                }
                                return newMessages;
                            });
                        } else if (chunk.type === 'error') {
                            throw new Error(chunk.error);
                        }
                    },
                    (error) => {
                        throw error;
                    },
                    abortControllerRef.current.signal
                );
            } catch (error: any) {
                console.error('Remote chat failed:', error);
                setMessages(prev => {
                    const newMessages = [...prev];
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage.role === 'assistant') {
                        lastMessage.content += `\n[Error: ${error.message}]`;
                        lastMessage.isStreaming = false;
                    }
                    return newMessages;
                });
            } finally {
                setIsLoading(false);
                abortControllerRef.current = null;
            }
        } else {
            // Local Command Logic (Non-streaming for now)
            try {
                // Construct history
                // Convert ChatMessage to backend format
                // Backend ChatMessage content is ChatContent enum
                const history = messages.map(m => ({
                    role: m.role,
                    content: m.content // History currently only supports text to keep simple
                }));
                // Add current message with updated structure
                let content: any = messageToSend;
                if (currentAttachment) {
                    content = {
                        parts: [
                            { type: "text", text: messageToSend },
                            {
                                type: "file",
                                file_data: {
                                    mime_type: currentAttachment.file.type,
                                    data: currentAttachment.base64
                                }
                            }
                        ]
                    };
                    // User message in history should also reflect this? 
                    // Backend expects specific structure. 
                    // Let's rely on the backend command 'chat_completion'
                }

                // For the backend, we need to send history + new message.
                // Or just send the whole history including the new message?
                // `chat_completion` takes `messages: Vec<ChatMessage>`.

                const requestMessages = [...history, {
                    role: 'user',
                    content: content
                }];

                // We need to fetch the ACTIVE model first?
                // `chat_completion` uses `get_ai_service` which uses cached active service.
                // Assuming it's initialized.

                // If history items are plain strings, backend `ChatMessage` deserialization works 
                // because `ChatContent` is `#[serde(untagged)]` enum with `Text(String)`.

                // BUT current message is an object.
                // Since `ChatContent` is untagged, it should handle it.
                // However, `content` in state is just string.
                // For history, we just send text content.

                console.log("Sending local chat request:", requestMessages);
                const response = await invoke<any>("chat_completion", {
                    request: {
                        messages: requestMessages,
                        // model: "", // backend uses active model
                        temperature: 0.7
                    }
                });

                setMessages(prev => {
                    const newMessages = [...prev];
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage.role === 'assistant') {
                        lastMessage.content = response.content;
                        lastMessage.isStreaming = false;
                    }
                    return newMessages;
                });

            } catch (error: any) {
                console.error('Local chat failed:', error);
                // Try to fallback to remote if local failed? No, probably config issue.
                setMessages(prev => {
                    const newMessages = [...prev];
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage.role === 'assistant') {
                        lastMessage.content += `\n[Error: ${error.message || error}]`;
                        lastMessage.isStreaming = false;
                    }
                    return newMessages;
                });
            } finally {
                setIsLoading(false);
            }
        }
    };

    const stopStreaming = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
            setIsLoading(false);
        }
    };

    const handleQuickAction = (action: QuickAction) => {
        if (!selectedText) return;

        const prompt = action.prompt_template
            .replace('{text}', selectedText)
            .replace('{target_language}', targetLanguage)
            .replace('{source_language}', sourceLanguage);

        handleSendMessage(prompt, action.action);
    };

    if (isInitializing) {
        return (
            <Card className={cn("p-6 flex items-center justify-center", className)}>
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span className="ml-2 text-muted-foreground">{t("novelChat.initializing") || "Initializing..."}</span>
            </Card>
        );
    }

    return (
        <Card className={cn("flex flex-col h-full", className)}>
            {/* Header */}
            <div className="border-b border-border p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-foreground">
                        <Sparkles className="h-5 w-5 text-primary" />
                        <h3 className="font-semibold">{t("novelChat.aiAssistant") || "AI Assistant"}</h3>
                    </div>
                    {onClose && (
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X className="h-4 w-4" />
                        </Button>
                    )}
                </div>

                {/* Selected Text Display */}
                {selectedText && (
                    <div className="mt-2 p-2 bg-muted rounded text-sm text-muted-foreground">
                        <div className="flex items-start justify-between">
                            <span className="text-muted-foreground/70 text-xs">{t("novelChat.selectedText") || "Selected text"}:</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 px-1"
                                onClick={() => navigator.clipboard.writeText(selectedText)}
                            >
                                <Copy className="h-3 w-3" />
                            </Button>
                        </div>
                        <p className="mt-1 line-clamp-2 italic text-foreground">"{selectedText}"</p>
                    </div>
                )}
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
                <div className="px-4 mt-2">
                    <TabsList className="w-full">
                        <TabsTrigger value="chat" className="flex-1">
                            <Bot className="h-4 w-4 mr-2" />
                            {t("novelChat.chat") || "Chat"}
                        </TabsTrigger>
                        <div className="text-muted-foreground flex items-center justify-center flex-1 text-sm">
                            <Languages className="h-4 w-4 mr-2" />
                            {t("novelChat.batch") || "Batch"} (Coming Soon)
                        </div>
                    </TabsList>
                </div>

                <TabsContent value="chat" className="flex-1 flex flex-col p-4 pt-2 min-h-0">
                    {/* Quick Actions */}
                    {quickActions.length > 0 && selectedText && (
                        <div className="mb-4">
                            <div className="flex flex-wrap gap-2">
                                {quickActions.slice(0, 4).map((action) => (
                                    <Button
                                        key={action.action}
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => handleQuickAction(action)}
                                        disabled={isLoading}
                                        className="text-xs h-7"
                                    >
                                        {action.label}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto pr-2 space-y-4 mb-4">
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={cn(
                                    "flex gap-3",
                                    message.role === 'user' ? "justify-end" : "justify-start"
                                )}
                            >
                                {message.role === 'assistant' && (
                                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                                        <Bot className="h-5 w-5 text-primary" />
                                    </div>
                                )}

                                <div className={cn(
                                    "max-w-[85%] rounded-lg p-3 text-sm flex flex-col gap-2",
                                    message.role === 'user'
                                        ? "bg-primary text-primary-foreground"
                                        : "bg-muted text-foreground"
                                )}>
                                    {message.metadata?.file_attachment && (
                                        <div className="rounded overflow-hidden border border-border/20 bg-black/10">
                                            {message.metadata.file_attachment.type.startsWith('image/') ? (
                                                <img
                                                    src={`data:${message.metadata.file_attachment.type};base64,${message.metadata.file_attachment.data}`}
                                                    alt="attachment"
                                                    className="max-h-32 object-contain"
                                                />
                                            ) : (
                                                <div className="p-2 flex items-center gap-2">
                                                    <FileIcon size={16} />
                                                    <span className="truncate max-w-[150px]">{message.metadata.file_attachment.name}</span>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <div className="whitespace-pre-wrap leading-relaxed">
                                        {message.content}
                                        {message.isStreaming && (
                                            <span className="inline-block w-1 h-4 ml-1 bg-current animate-pulse align-middle" />
                                        )}
                                    </div>
                                </div>

                                {message.role === 'user' && (
                                    <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                                        <User className="h-5 w-5 text-muted-foreground" />
                                    </div>
                                )}
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Attachment Preview in Input Area */}
                    {attachment && (
                        <div className="mb-2 p-2 bg-muted rounded-lg flex items-center justify-between animate-in slide-in-from-bottom-2">
                            <div className="flex items-center gap-2 overflow-hidden">
                                {attachment.preview ? (
                                    <img src={attachment.preview} alt="preview" className="h-8 w-8 object-cover rounded" />
                                ) : (
                                    <FileIcon className="h-5 w-5 text-primary" />
                                )}
                                <span className="text-xs truncate max-w-[200px]">{attachment.file.name}</span>
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => setAttachment(null)} className="h-6 w-6 p-0 hover:bg-destructive/10 hover:text-destructive">
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    )}

                    {/* Input */}
                    <div className="mt-auto flex gap-2">
                        <input
                            type="file"
                            ref={fileInputRef}
                            className="hidden"
                            onChange={handleFileSelect}
                            accept="image/*,video/*,audio/*,.pdf,.txt"
                        />
                        <Button
                            variant="secondary"
                            size="sm"
                            className="w-10 px-0"
                            title={t("novelChat.attachFile") || "Attach file"}
                            onClick={() => fileInputRef.current?.click()}
                            disabled={isLoading}
                        >
                            <Paperclip className="h-4 w-4" />
                        </Button>
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                            placeholder={t("novelChat.inputPlaceholder") || "Ask a question..."}
                            disabled={isLoading}
                            className="flex-1 bg-background border-input"
                        />
                        {isLoading ? (
                            <Button onClick={stopStreaming} variant="danger" size="sm" className="w-10 px-0">
                                <X className="h-4 w-4" />
                            </Button>
                        ) : (
                            <Button onClick={() => handleSendMessage()} disabled={!input.trim() && !attachment} size="sm" className="w-10 px-0">
                                <Send className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </TabsContent>
            </Tabs>
        </Card>
    );
}
