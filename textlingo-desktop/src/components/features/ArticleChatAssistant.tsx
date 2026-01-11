import React, { useState, useEffect, useRef } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import {
    Send, Bot, User, Sparkles, Languages, X,
    Loader2, Copy
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";
import {
    getApiClient,
    NovelSession,
    QuickAction
} from "../../lib/api";

// Simple Card component since we don't have one in UI
const Card = ({ className, children }: { className?: string; children: React.ReactNode }) => (
    <div className={cn("bg-gray-900 border border-gray-800 rounded-lg", className)}>
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
    };
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
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

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
    }, [messages]);

    const initializeSession = async () => {
        try {
            setIsInitializing(true);
            const api = getApiClient();
            if (!api.isBackendConfigured()) {
                // Fallback if backend not ready - show error in chat?
                setMessages([{
                    id: 'error',
                    role: 'assistant',
                    content: t("novelChat.backendNotConfigured") || "Please configure backend API settings to use AI assistant.",
                    timestamp: new Date()
                }]);
                setIsInitializing(false);
                return;
            }

            const response = await api.createNovelSession({
                novel_id: articleId,
                user_language: targetLanguage,
                novel_language: sourceLanguage,
                title: `${articleTitle} - Assistant`
            });
            setSession(response.session);
            setQuickActions(response.quick_actions);

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
            setMessages([{
                id: 'error',
                role: 'assistant',
                content: `${t("novelChat.initFailed") || "Failed to initialize AI assistant"}: ${error}`,
                timestamp: new Date()
            }]);
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

    const handleSendMessage = async (message?: string, actionType?: string) => {
        const messageToSend = message || input.trim();
        if (!messageToSend || !session || isLoading) return;

        if (!message) setInput("");

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: messageToSend,
            timestamp: new Date(),
            metadata: {
                selected_text: selectedText,
                action_type: actionType
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

        try {
            setIsLoading(true);
            abortControllerRef.current = new AbortController();
            const api = getApiClient();

            await api.streamNovelChat(
                {
                    session_id: session.id,
                    message: messageToSend,
                    selected_text: selectedText,
                    current_segment: currentSegment,
                    reading_progress: readingProgress,
                },
                (chunk) => {
                    if (chunk.type === 'message' || (chunk.type as any) === 'content') {
                        // Handle both 'message' (standard) and 'content' (legacy/web) types just in case
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
                    console.error('Stream error:', error);
                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastMessage = newMessages[newMessages.length - 1];
                        if (lastMessage.role === 'assistant') {
                            lastMessage.content += `\n[Error: ${error.message}]`;
                            lastMessage.isStreaming = false;
                        }
                        return newMessages;
                    });
                },
                abortControllerRef.current.signal
            );
        } catch (error: any) {
            if (error.name !== 'AbortError') {
                console.error('Failed to send message:', error);
            }
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
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
                <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                <span className="ml-2 text-gray-400">{t("novelChat.initializing") || "Initializing..."}</span>
            </Card>
        );
    }

    return (
        <Card className={cn("flex flex-col h-full", className)}>
            {/* Header */}
            <div className="border-b border-gray-800 p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-white">
                        <Sparkles className="h-5 w-5 text-blue-500" />
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
                    <div className="mt-2 p-2 bg-gray-800 rounded text-sm text-gray-300">
                        <div className="flex items-start justify-between">
                            <span className="text-gray-500 text-xs">{t("novelChat.selectedText") || "Selected text"}:</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 px-1"
                                onClick={() => navigator.clipboard.writeText(selectedText)}
                            >
                                <Copy className="h-3 w-3" />
                            </Button>
                        </div>
                        <p className="mt-1 line-clamp-2 italic">"{selectedText}"</p>
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
                        <div className="text-gray-500 flex items-center justify-center flex-1">
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
                                    <div className="h-8 w-8 rounded-full bg-blue-600/10 flex items-center justify-center shrink-0">
                                        <Bot className="h-5 w-5 text-blue-500" />
                                    </div>
                                )}

                                <div className={cn(
                                    "max-w-[85%] rounded-lg p-3 text-sm",
                                    message.role === 'user'
                                        ? "bg-blue-600 text-white"
                                        : "bg-gray-800 text-gray-200"
                                )}>
                                    <div className="whitespace-pre-wrap leading-relaxed">
                                        {message.content}
                                        {message.isStreaming && (
                                            <span className="inline-block w-1 h-4 ml-1 bg-current animate-pulse align-middle" />
                                        )}
                                    </div>
                                </div>

                                {message.role === 'user' && (
                                    <div className="h-8 w-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0">
                                        <User className="h-5 w-5 text-gray-300" />
                                    </div>
                                )}
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="mt-auto flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                            placeholder={t("novelChat.inputPlaceholder") || "Ask a question..."}
                            disabled={isLoading}
                            className="flex-1 bg-gray-950 border-gray-800"
                        />
                        {isLoading ? (
                            <Button onClick={stopStreaming} variant="danger" size="sm" className="w-10 px-0">
                                <X className="h-4 w-4" />
                            </Button>
                        ) : (
                            <Button onClick={() => handleSendMessage()} disabled={!input.trim()} size="sm" className="w-10 px-0">
                                <Send className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </TabsContent>
            </Tabs>
        </Card>
    );
}
