import React, { useState, useEffect, useRef } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
    Send, Bot, User, Sparkles, Languages, X,
    Loader2, Copy, Paperclip, File as FileIcon,
    Lightbulb, GraduationCap, Zap
} from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { useTranslation, Trans } from "react-i18next";
import { cn } from "../../lib/utils";
import {
    getApiClient,
    NovelSession,
    QuickAction
} from "../../lib/api";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

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

interface ModelConfig {
    id: string;
    name: string;
    model: string;
    api_provider: string;
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
    const { t } = useTranslation();
    const [session, setSession] = useState<NovelSession | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isInitializing, setIsInitializing] = useState(true);
    const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
    const [attachment, setAttachment] = useState<Attachment | null>(null);
    const [activeModel, setActiveModel] = useState<ModelConfig | null>(null);
    const [isFastTranslateEnabled, setIsFastTranslateEnabled] = useState(false);
    const [showSlowTip, setShowSlowTip] = useState(false);
    const slowTimerRef = useRef<NodeJS.Timeout | null>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Initialize session and model
    useEffect(() => {
        const init = async () => {
            setIsInitializing(true);
            await fetchActiveModel();
            await initializeSession();
            setIsInitializing(false);
        };
        init();
    }, [articleId]);

    // Load quick actions when selected text changes
    useEffect(() => {
        if (selectedText) {
            // Auto translate if enabled
            if (isFastTranslateEnabled) {
                handleQuickAction({
                    action: "translate",
                    label: "Translate",
                    description: "Translate",
                    prompt_template: ""
                },); // Auto-run translate
            }

            // Define local quick actions if no session or just to be instant
            const actions: QuickAction[] = [
                {
                    action: "translate",
                    label: t("novelChat.quickTranslate", "Translate"),
                    description: t("novelChat.quickTranslateDesc", "Translate to target language"),
                    prompt_template: "Translate the following text to {target_language}:\n\n{text}"
                },
                {
                    action: "explain",
                    label: t("novelChat.quickExplain", "Explain"),
                    description: t("novelChat.quickExplainDesc", "Explain the text"),
                    prompt_template: "Explain the following text in {target_language}:\n\n{text}"
                },
                {
                    action: "grammar",
                    label: t("novelChat.quickGrammar", "Grammar"),
                    description: t("novelChat.quickGrammarDesc", "Analyze grammar"),
                    prompt_template: "Analyze the grammar of the following text in {target_language}:\n\n{text}"
                }
            ];
            setQuickActions(actions);
        } else {
            setQuickActions([]);
        }
    }, [selectedText, t, isFastTranslateEnabled]);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        // Also scroll when attachment changes to keep input visible
        if (attachment) {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, attachment]);

    const fetchActiveModel = async () => {
        try {
            const config = await invoke<ModelConfig>("get_active_model_config");
            setActiveModel(config);
        } catch (e) {
            console.error("Failed to fetch active model config:", e);
        }
    };

    const initializeSession = async () => {
        try {
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
                } catch (e) {
                    console.warn("Failed to create remote session, falling back to local mode", e);
                }
            } else {
                console.log("Backend not configured, using local mode");
            }

            // Updated Welcome Message
            const welcomeMessage = "Hello! I'm your reading assistant. I can help translate, explain text, analyze grammar, or discuss the article.";

            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: welcomeMessage,
                timestamp: new Date()
            }]);
        } catch (error) {
            console.error('Failed to initialize session:', error);
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

    const startSlowTimer = () => {
        if (slowTimerRef.current) clearTimeout(slowTimerRef.current);
        setShowSlowTip(false);
        slowTimerRef.current = setTimeout(() => {
            setShowSlowTip(true);
        }, 6000);
    };

    const clearSlowTimer = () => {
        if (slowTimerRef.current) {
            clearTimeout(slowTimerRef.current);
            slowTimerRef.current = null;
        }
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
        startSlowTimer();

        const api = getApiClient();
        const useRemote = session && !currentAttachment && api.isBackendConfigured();

        // Augment prompt with context if meaningful
        let effectiveMessage = messageToSend;
        if (!useRemote && selectedText && !actionType) {
            effectiveMessage = `Context: "${selectedText}"\n\nUser Question: ${messageToSend}`;
        }

        try {
            if (useRemote) {
                // Remote Streaming Logic
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
                        clearSlowTimer(); // Clear timer on first chunk
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
            } else {
                // Local Command Logic (Non-streaming for now)
                try {
                    const history = messages.map(m => ({
                        role: m.role,
                        content: m.content
                    }));
                    let content: any = effectiveMessage;
                    if (currentAttachment) {
                        content = {
                            parts: [
                                { type: "text", text: effectiveMessage },
                                {
                                    type: "file",
                                    file_data: {
                                        mime_type: currentAttachment.file.type,
                                        data: currentAttachment.base64
                                    }
                                }
                            ]
                        };
                    }

                    const requestMessages = [...history, {
                        role: 'user',
                        content: content
                    }];

                    if (history.length === 0) {
                        requestMessages.unshift({
                            role: "user",
                            content: `You are a helpful reading assistant. The user is reading: "${articleTitle}". \nTarget Language: ${targetLanguage}.`
                        } as any);
                    }

                    console.log("Sending local chat request with streaming:", requestMessages);

                    const eventId = crypto.randomUUID();
                    let fullContent = "";

                    const unlisten = await listen<string>(`chat-stream://${eventId}`, (event) => {
                        clearSlowTimer(); // Clear timer on first chunk
                        const chunk = event.payload;
                        if (chunk) {
                            fullContent += chunk;
                            setMessages(prev => {
                                const newMessages = [...prev];
                                const lastMsgIdx = newMessages.length - 1;
                                if (lastMsgIdx >= 0 && newMessages[lastMsgIdx].role === 'assistant') {
                                    newMessages[lastMsgIdx] = {
                                        ...newMessages[lastMsgIdx],
                                        content: fullContent
                                    };
                                }
                                return newMessages;
                            });
                        }
                    });

                    try {
                        await invoke("stream_chat_completion", {
                            request: {
                                messages: requestMessages,
                                model: activeModel?.model || "",
                                temperature: 0.7
                            },
                            eventId
                        });
                    } finally {
                        unlisten();
                        setMessages(prev => {
                            const newMessages = [...prev];
                            const lastMsgIdx = newMessages.length - 1;
                            if (lastMsgIdx >= 0 && newMessages[lastMsgIdx].role === 'assistant') {
                                newMessages[lastMsgIdx] = {
                                    ...newMessages[lastMsgIdx],
                                    isStreaming: false
                                };
                            }
                            return newMessages;
                        });
                    }

                } catch (error: any) {
                    console.error('Local chat failed:', error);
                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastMessage = newMessages[newMessages.length - 1];
                        if (lastMessage.role === 'assistant') {
                            lastMessage.content += `\n[Error: ${error.message || error}]`;
                            lastMessage.isStreaming = false;
                        }
                        return newMessages;
                    });
                }
            }
        } catch (error: any) {
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
            clearSlowTimer();
            abortControllerRef.current = null;
        }
    };

    const stopStreaming = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
            setIsLoading(false);
            clearSlowTimer();
        }
    };

    const handleQuickAction = async (action: QuickAction) => {
        if (!selectedText) return;

        if (action.action === 'translate') {
            const userMessageContent = `Translate:\n"${selectedText}"`;

            const userMessage: ChatMessage = {
                id: Date.now().toString(),
                role: 'user',
                content: userMessageContent,
                timestamp: new Date(),
                metadata: {
                    selected_text: selectedText,
                    action_type: action.action
                }
            };
            setMessages(prev => [...prev, userMessage]);

            const assistantMsgId = (Date.now() + 1).toString();
            const assistantMessage: ChatMessage = {
                id: assistantMsgId,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                isStreaming: true
            };
            setMessages(prev => [...prev, assistantMessage]);

            setIsLoading(true);
            startSlowTimer();

            try {
                const response = await invoke<{ translated_text: string }>("translate_text", {
                    request: {
                        text: selectedText,
                        target_language: targetLanguage
                    }
                });

                // Clear timer as soon as we have response
                clearSlowTimer();

                setMessages(prev => {
                    const newMessages = [...prev];
                    const idx = newMessages.findIndex(m => m.id === assistantMsgId);
                    if (idx !== -1) {
                        newMessages[idx] = {
                            ...newMessages[idx],
                            content: response.translated_text,
                            isStreaming: false
                        };
                    }
                    return newMessages;
                });
            } catch (error: any) {
                console.error("Translation failed:", error);
                setMessages(prev => {
                    const newMessages = [...prev];
                    const idx = newMessages.findIndex(m => m.id === assistantMsgId);
                    if (idx !== -1) {
                        newMessages[idx] = {
                            ...newMessages[idx],
                            content: `Translation failed: ${error.message || error}`,
                            isStreaming: false
                        };
                    }
                    return newMessages;
                });
            } finally {
                setIsLoading(false);
                clearSlowTimer();
            }
            return;
        }

        const prompt = action.prompt_template
            .replace('{text}', selectedText)
            .replace('{target_language}', targetLanguage)
            .replace('{source_language}', sourceLanguage);

        handleSendMessage(prompt, action.action);
    };

    const getActionIcon = (action: string) => {
        switch (action) {
            case 'translate': return <Languages size={14} className="mr-1" />;
            case 'explain': return <Lightbulb size={14} className="mr-1" />;
            case 'grammar': return <GraduationCap size={14} className="mr-1" />;
            default: return <Sparkles size={14} className="mr-1" />;
        }
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
                    <div className="flex items-center gap-1">
                        <Button
                            variant={isFastTranslateEnabled ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setIsFastTranslateEnabled(!isFastTranslateEnabled)}
                            className={cn("text-xs h-7 px-2", isFastTranslateEnabled && "bg-amber-500 hover:bg-amber-600 text-white")}
                            title={t("novelChat.fastTranslate", "Fast Translate")}
                        >
                            <Zap className={cn("h-3.5 w-3.5 mr-1", isFastTranslateEnabled ? "fill-white" : "text-muted-foreground")} />
                            <span className={cn(!isFastTranslateEnabled && "text-muted-foreground")}>{t("common.fast", "Fast")}</span>
                        </Button>
                        {onClose && (
                            <Button variant="ghost" size="sm" onClick={onClose}>
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
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

            <div className="flex-1 flex flex-col p-4 pt-2 min-h-0 overflow-hidden">
                {/* Slow Response Tip */}
                {showSlowTip && !isLoading && (
                    <div className="mx-4 mt-2 mb-2 p-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-md flex items-start gap-2 animate-in fade-in slide-in-from-top-1">
                        <Sparkles className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-600 dark:text-amber-400">
                            <Trans
                                i18nKey="novelChat.slowResponseTip"
                                defaults="Response slow? Try a faster model like <b>Gemini 3 Flash</b> for instant results."
                                components={{ 1: <b /> }}
                            />
                        </p>
                    </div>
                )}

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
                                    className="text-xs h-8"
                                >
                                    {getActionIcon(action.action)}
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

                                <div className="leading-relaxed overflow-hidden">
                                    {message.role === 'user' ? (
                                        <div className="whitespace-pre-wrap">{message.content}</div>
                                    ) : (
                                        <div className="prose prose-sm dark:prose-invert max-w-none break-words [&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:list-disc [&>ul]:pl-4 [&>ol]:list-decimal [&>ol]:pl-4">
                                            <ReactMarkdown
                                                components={{
                                                    code({ node, className, children, ...props }: any) {
                                                        const match = /language-(\w+)/.exec(className || '')
                                                        return match ? (
                                                            <div className="relative rounded bg-muted-foreground/20 p-2 my-2 font-mono text-xs overflow-x-auto">
                                                                <code className={className} {...props}>
                                                                    {children}
                                                                </code>
                                                            </div>
                                                        ) : (
                                                            <code className="bg-muted-foreground/20 rounded px-1 py-0.5 font-mono text-xs" {...props}>
                                                                {children}
                                                            </code>
                                                        )
                                                    }
                                                }}
                                            >
                                                {message.content}
                                            </ReactMarkdown>
                                        </div>
                                    )}
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
                {activeModel && (
                    <div className="text-[10px] text-muted-foreground/50 text-center mt-1">
                        Using {activeModel.name}
                    </div>
                )}
            </div>
        </Card>
    );
}
