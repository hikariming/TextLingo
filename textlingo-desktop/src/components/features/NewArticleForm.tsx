import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { FileText, Loader2, Link, Clipboard, Cloud, Info } from "lucide-react";
import { getApiClient } from "../../lib/api";
import { Article } from "../../types";

interface NewArticleFormProps {
    onSave?: (article: Article) => void;
    onCancel: () => void;
    initialArticle?: Article;
}

export function NewArticleForm({ onSave, onCancel, initialArticle }: NewArticleFormProps) {
    const { t } = useTranslation();
    const [title, setTitle] = useState(initialArticle?.title || "");
    const [content, setContent] = useState(initialArticle?.content || "");
    const [sourceUrl, setSourceUrl] = useState(initialArticle?.source_url || "");
    const [isSaving, setIsSaving] = useState(false);
    const [isFetching, setIsFetching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [useBackend, setUseBackend] = useState(false);

    // Load config and check if backend is available
    useEffect(() => {
        const checkBackend = async () => {
            try {
                const config = await invoke("get_config") as any;
                const apiClient = getApiClient(config);
                setUseBackend(apiClient.isBackendConfigured());
            } catch {
                setUseBackend(false);
            }
        };
        checkBackend();
    }, []);

    const handleSave = async () => {
        if (!content.trim()) {
            setError(t("newArticle.errors.contentRequired"));
            return;
        }

        setIsSaving(true);
        setError(null);
        try {
            let article: Article;
            if (initialArticle) {
                // Update existing article
                article = await invoke<Article>("update_article", {
                    id: initialArticle.id,
                    title: title.trim() || t("articleList.untitled"),
                    content,
                    sourceUrl: sourceUrl.trim() || undefined,
                });
            } else {
                // Create new article
                article = await invoke<Article>("create_article", {
                    title: title.trim() || t("articleList.untitled"),
                    content,
                    sourceUrl: sourceUrl.trim() || undefined,
                });
            }
            onSave?.(article);
        } catch (err) {
            setError(err as string);
        } finally {
            setIsSaving(false);
        }
    };

    const handlePaste = async () => {
        try {
            const text = await navigator.clipboard.readText();
            setContent(text);
        } catch (err) {
            setError(t("newArticle.errors.clipboardError"));
        }
    };

    /**
     * Fetch content from URL - tries backend API first, falls back to local
     * Matches Flutter behavior using Dify workflow when available
     */
    const fetchFromUrl = async (url: string): Promise<{ title: string; content: string }> => {
        const config = await invoke("get_config") as any;
        const apiClient = getApiClient(config);

        // Try backend API first (like Flutter does)
        if (apiClient.isBackendConfigured()) {
            try {
                return await apiClient.fetchUrlContent(url);
            } catch (backendError) {
                console.warn("Backend fetch failed, falling back to local:", backendError);
                // Fall through to local fetch
            }
        }

        // Fallback to local Tauri command
        return await invoke("fetch_url_content", { url }) as { title: string; content: string };
    };

    const handleFetchFromUrl = async () => {
        if (!sourceUrl.trim()) {
            setError(t("newArticle.errors.urlRequired"));
            return;
        }

        // Simple URL validation
        const url = sourceUrl.trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            setError(t("newArticle.errors.urlInvalid"));
            return;
        }

        setIsFetching(true);
        setError(null);
        try {
            const fetched = await fetchFromUrl(url);

            // Set title if empty, and set content
            if (!title.trim() && fetched.title) {
                setTitle(fetched.title);
            }
            setContent(fetched.content);

            // Check if content is empty or too short
            if (!fetched.content || fetched.content.trim().length < 10) {
                setError(t("newArticle.errors.noContentExtracted"));
            }
        } catch (err) {
            setError(err as string);
        } finally {
            setIsFetching(false);
        }
    };

    const handlePasteUrlAndFetch = async () => {
        try {
            const url = await navigator.clipboard.readText();
            // Check if it looks like a URL
            if (url.startsWith("http://") || url.startsWith("https://")) {
                setSourceUrl(url);
                // Auto-fetch after pasting URL
                setIsFetching(true);
                setError(null);
                try {
                    const fetched = await fetchFromUrl(url);

                    if (!title.trim() && fetched.title) {
                        setTitle(fetched.title);
                    }
                    setContent(fetched.content);

                    // Check if content is empty or too short
                    if (!fetched.content || fetched.content.trim().length < 10) {
                        setError(t("newArticle.errors.noContentExtracted"));
                    }
                } catch (err) {
                    setError(err as string);
                } finally {
                    setIsFetching(false);
                }
            } else {
                setError(t("newArticle.errors.clipboardNotUrl"));
            }
        } catch (err) {
            setError(t("newArticle.errors.clipboardError"));
        }
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex-1 space-y-4 overflow-y-auto pr-1">
                {error && (
                    <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
                        {error}
                    </div>
                )}
                {/* Hint */}
                <div className="flex gap-3 p-3 bg-primary/10 border border-primary/20 rounded-lg text-sm text-foreground/90 mb-4">
                    <Info className="w-5 h-5 shrink-0 text-primary mt-0.5" />
                    <p>{t("newArticle.hint", "This feature is for sentence-by-sentence intensive reading...")}</p>
                </div>

                {/* Title */}
                <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                        {t("newArticle.titleLabel")} <span className="text-muted-foreground">{t("newArticle.optional")}</span>
                    </label>
                    <Input
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder={t("newArticle.titlePlaceholder")}
                    />
                </div>

                {/* Source URL */}
                <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                        {t("newArticle.sourceUrlLabel")} <span className="text-muted-foreground">{t("newArticle.optional")}</span>
                    </label>
                    <div className="flex gap-2 items-center">
                        <Input
                            value={sourceUrl}
                            onChange={(e) => setSourceUrl(e.target.value)}
                            placeholder={t("newArticle.sourceUrlPlaceholder")}
                            className="flex-1"
                        />
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={handleFetchFromUrl}
                            disabled={isFetching || !sourceUrl.trim()}
                            className="gap-1"
                            title={useBackend ? "Fetch using backend API" : "Fetch using local parser"}
                        >
                            {isFetching ? (
                                <Loader2 size={16} className="animate-spin" />
                            ) : useBackend ? (
                                <Cloud size={16} />
                            ) : (
                                <Link size={16} />
                            )}
                            {t("newArticle.fetch")}
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handlePasteUrlAndFetch}
                            disabled={isFetching}
                            title={t("newArticle.pasteUrlAndFetch")}
                            className="gap-1"
                        >
                            <Clipboard size={16} />
                        </Button>
                    </div>
                    {useBackend && (
                        <p className="text-xs text-muted-foreground mt-1">
                            Using backend API for better content extraction
                        </p>
                    )}
                </div>

                {/* Content */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-medium text-foreground">
                            {t("newArticle.contentLabel")} <span className="text-red-500">{t("newArticle.required")}</span>
                        </label>
                        <Button variant="ghost" size="sm" onClick={handlePaste}>
                            {t("newArticle.pasteFromClipboard")}
                        </Button>
                    </div>
                    <Textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder={t("newArticle.contentPlaceholder")}
                        className="min-h-[300px] font-mono text-sm"
                    />
                </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
                <Button variant="secondary" onClick={onCancel} disabled={isSaving || isFetching}>
                    {t("newArticle.cancel")}
                </Button>
                <Button onClick={handleSave} disabled={isSaving || isFetching} className="gap-2">
                    {isSaving ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            {t("newArticle.saving")}
                        </>
                    ) : (
                        <>
                            <FileText size={16} />
                            {t("newArticle.createArticle")}
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
}
