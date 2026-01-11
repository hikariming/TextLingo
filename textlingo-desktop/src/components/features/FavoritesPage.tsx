import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import { BookOpen, SpellCheck, Trash2, ExternalLink, Loader2, ArrowLeft, Download, Upload, Copy, FileDown, Check } from "lucide-react";
import type { FavoriteVocabulary, FavoriteGrammar, Article } from "../../types";

interface FavoritesPageProps {
    onBack: () => void;
    onSelectArticle: (article: Article) => void;
}

export function FavoritesPage({ onBack, onSelectArticle }: FavoritesPageProps) {
    const { t } = useTranslation();
    const [vocabularies, setVocabularies] = useState<FavoriteVocabulary[]>([]);
    const [grammars, setGrammars] = useState<FavoriteGrammar[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState("vocabulary");
    const [articles, setArticles] = useState<Map<string, Article>>(new Map());
    const [showExportMenu, setShowExportMenu] = useState(false);
    const [copySuccess, setCopySuccess] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Load favorites data
    const loadFavorites = async () => {
        setIsLoading(true);
        try {
            const [vocabList, grammarList] = await Promise.all([
                invoke<FavoriteVocabulary[]>("list_favorite_vocabularies_cmd"),
                invoke<FavoriteGrammar[]>("list_favorite_grammars_cmd"),
            ]);
            setVocabularies(vocabList);
            setGrammars(grammarList);

            // Load associated article info (for navigation)
            const articleIds = new Set<string>();
            vocabList.forEach(v => v.source_article_id && articleIds.add(v.source_article_id));
            grammarList.forEach(g => g.source_article_id && articleIds.add(g.source_article_id));

            const articleMap = new Map<string, Article>();
            for (const id of articleIds) {
                try {
                    const article = await invoke<Article>("get_article", { id });
                    articleMap.set(id, article);
                } catch {
                    // Article might be deleted, ignore error
                }
            }
            setArticles(articleMap);
        } catch (err) {
            console.error("Failed to load favorites:", err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadFavorites();
    }, []);

    // Delete vocabulary favorite
    const handleDeleteVocabulary = async (id: string) => {
        try {
            await invoke("delete_favorite_vocabulary_cmd", { id });
            setVocabularies(prev => prev.filter(v => v.id !== id));
        } catch (err) {
            console.error("Failed to delete vocabulary favorite:", err);
        }
    };

    // Delete grammar favorite
    const handleDeleteGrammar = async (id: string) => {
        try {
            await invoke("delete_favorite_grammar_cmd", { id });
            setGrammars(prev => prev.filter(g => g.id !== id));
        } catch (err) {
            console.error("Failed to delete grammar favorite:", err);
        }
    };

    // Navigate to source article
    const handleGoToArticle = (articleId: string) => {
        const article = articles.get(articleId);
        if (article) {
            onSelectArticle(article);
        }
    };

    // --- Export/Import Handlers ---

    // 导出纯文本（每行一个单词）
    const getPlainTextExport = (): string => {
        return vocabularies.map(v => v.word).join("\n");
    };

    // 复制到剪贴板
    const handleCopyToClipboard = async () => {
        if (vocabularies.length === 0) return;
        const text = getPlainTextExport();
        try {
            await navigator.clipboard.writeText(text);
            setCopySuccess(true);
            setTimeout(() => setCopySuccess(false), 2000);
        } catch (err) {
            console.error("Failed to copy to clipboard:", err);
        }
        setShowExportMenu(false);
    };

    // 下载 TXT 文件
    const handleDownloadTxt = () => {
        if (vocabularies.length === 0) return;
        const text = getPlainTextExport();
        const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "textlingo_vocabulary.txt";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        setShowExportMenu(false);
    };

    // 导出 JSON 文件
    const handleExportJson = () => {
        if (vocabularies.length === 0) return;
        // 导出时去掉 id 和 source_article_id，因为这些是本地数据
        const exportData = vocabularies.map(({ id, source_article_id, ...rest }) => rest);
        const json = JSON.stringify(exportData, null, 2);
        const blob = new Blob([json], { type: "application/json;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "textlingo_vocabulary.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // 导入 JSON 文件
    const handleImportJson = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const jsonStr = e.target?.result as string;
                const importedData = JSON.parse(jsonStr) as Partial<FavoriteVocabulary>[];

                let importedCount = 0;
                for (const item of importedData) {
                    // 检查是否已存在相同单词
                    const exists = vocabularies.some(v => v.word === item.word);
                    if (!exists && item.word && item.meaning) {
                        try {
                            await invoke("add_favorite_vocabulary_cmd", {
                                word: item.word,
                                meaning: item.meaning,
                                usage: item.usage || "",
                                example: item.example || null,
                                reading: item.reading || null,
                                sourceArticleId: null,
                                sourceArticleTitle: item.source_article_title || null,
                            });
                            importedCount++;
                        } catch (err) {
                            console.error("Failed to import vocabulary:", item.word, err);
                        }
                    }
                }

                // 重新加载数据
                await loadFavorites();
                alert(t("favorites.importSuccess", { count: importedCount }));
            } catch (err) {
                console.error("Failed to parse JSON:", err);
                alert(t("favorites.importError", "导入失败"));
            }
        };
        reader.readAsText(file);
        // 清空 input 以便再次选择同一文件
        event.target.value = "";
    };

    return (
        <div className="h-full max-w-4xl mx-auto p-6 flex flex-col">
            <div className="flex items-center gap-4 mb-6">
                <Button variant="ghost" size="icon" onClick={onBack}>
                    <ArrowLeft size={20} />
                </Button>
                <div>
                    <h2 className="text-xl font-semibold">{t("favorites.title", "我的收藏")}</h2>
                    <p className="text-sm text-muted-foreground">{t("favorites.subtitle", "管理您收藏的单词与语法")}</p>
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
                <TabsList className="mb-4">
                    <TabsTrigger value="vocabulary" className="gap-2">
                        <BookOpen size={14} />
                        {t("favorites.vocabulary", "单词收藏")}
                        <span className="text-xs text-muted-foreground">({vocabularies.length})</span>
                    </TabsTrigger>
                    <TabsTrigger value="grammar" className="gap-2">
                        <SpellCheck size={14} />
                        {t("favorites.grammar", "语法收藏")}
                        <span className="text-xs text-muted-foreground">({grammars.length})</span>
                    </TabsTrigger>
                </TabsList>

                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="animate-spin text-muted-foreground" size={24} />
                    </div>
                ) : (
                    <div className="flex-1 overflow-y-auto pr-2">
                        <TabsContent value="vocabulary" className="mt-0 h-full">
                            {/* 导入/导出工具栏 */}
                            {vocabularies.length > 0 && (
                                <div className="flex items-center justify-end gap-2 mb-4 pb-3 border-b border-border/50">
                                    {/* 导出纯文本下拉菜单 */}
                                    <div className="relative">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => setShowExportMenu(!showExportMenu)}
                                            className="gap-1.5"
                                        >
                                            <Download size={14} />
                                            {t("favorites.exportPlainText", "导出纯文本")}
                                        </Button>
                                        {showExportMenu && (
                                            <div className="absolute right-0 top-full mt-1 z-50 bg-popover border border-border rounded-lg shadow-lg py-1 min-w-[160px]">
                                                <button
                                                    className="w-full px-3 py-2 text-sm text-left hover:bg-accent flex items-center gap-2"
                                                    onClick={handleCopyToClipboard}
                                                >
                                                    {copySuccess ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                                                    {copySuccess ? t("favorites.copied", "已复制") : t("favorites.copyToClipboard", "复制到剪贴板")}
                                                </button>
                                                <button
                                                    className="w-full px-3 py-2 text-sm text-left hover:bg-accent flex items-center gap-2"
                                                    onClick={handleDownloadTxt}
                                                >
                                                    <FileDown size={14} />
                                                    {t("favorites.downloadTxt", "下载 TXT 文件")}
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* 导出 JSON */}
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={handleExportJson}
                                        className="gap-1.5"
                                    >
                                        <Download size={14} />
                                        {t("favorites.exportJson", "导出 JSON")}
                                    </Button>

                                    {/* 导入 JSON */}
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="gap-1.5"
                                    >
                                        <Upload size={14} />
                                        {t("favorites.importJson", "导入 JSON")}
                                    </Button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        accept=".json"
                                        onChange={handleImportJson}
                                        className="hidden"
                                    />
                                </div>
                            )}

                            {/* 空列表时也显示导入按钮 */}
                            {vocabularies.length === 0 && (
                                <div className="flex justify-end mb-4">
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="gap-1.5"
                                    >
                                        <Upload size={14} />
                                        {t("favorites.importJson", "导入 JSON")}
                                    </Button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        accept=".json"
                                        onChange={handleImportJson}
                                        className="hidden"
                                    />
                                </div>
                            )}

                            {vocabularies.length === 0 ? (
                                <EmptyState
                                    icon={<BookOpen size={40} />}
                                    title={t("favorites.noVocabulary", "暂无单词收藏")}
                                    description={t("favorites.noVocabularyDesc", "在文章学习中点击单词旁的收藏按钮即可添加")}
                                />
                            ) : (
                                <div className="space-y-3 pb-6">
                                    {vocabularies.map(vocab => (
                                        <VocabularyCard
                                            key={vocab.id}
                                            vocab={vocab}
                                            article={vocab.source_article_id ? articles.get(vocab.source_article_id) : undefined}
                                            onDelete={() => handleDeleteVocabulary(vocab.id)}
                                            onGoToArticle={vocab.source_article_id ? () => handleGoToArticle(vocab.source_article_id!) : undefined}
                                        />
                                    ))}
                                </div>
                            )}
                        </TabsContent>

                        <TabsContent value="grammar" className="mt-0 h-full">
                            {grammars.length === 0 ? (
                                <EmptyState
                                    icon={<SpellCheck size={40} />}
                                    title={t("favorites.noGrammar", "暂无语法收藏")}
                                    description={t("favorites.noGrammarDesc", "在文章学习中点击语法点旁的收藏按钮即可添加")}
                                />
                            ) : (
                                <div className="space-y-3 pb-6">
                                    {grammars.map(grammar => (
                                        <GrammarCard
                                            key={grammar.id}
                                            grammar={grammar}
                                            article={grammar.source_article_id ? articles.get(grammar.source_article_id) : undefined}
                                            onDelete={() => handleDeleteGrammar(grammar.id)}
                                            onGoToArticle={grammar.source_article_id ? () => handleGoToArticle(grammar.source_article_id!) : undefined}
                                        />
                                    ))}
                                </div>
                            )}
                        </TabsContent>
                    </div>
                )}
            </Tabs>
        </div>
    );
}

// Empty State Component
function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-center text-muted-foreground">
            <div className="mb-4 opacity-50">{icon}</div>
            <h3 className="text-lg font-medium mb-2">{title}</h3>
            <p className="text-sm">{description}</p>
        </div>
    );
}

// Vocabulary Card Component
function VocabularyCard({
    vocab,
    article,
    onDelete,
    onGoToArticle,
}: {
    vocab: FavoriteVocabulary;
    article?: Article;
    onDelete: () => void;
    onGoToArticle?: () => void;
}) {
    return (
        <div className="bg-card border border-border p-4 rounded-lg hover:border-primary/30 transition-colors">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <div className="flex items-baseline gap-2 mb-1">
                        <span className="font-bold text-lg text-foreground">{vocab.word}</span>
                        {vocab.reading && (
                            <span className="text-xs text-muted-foreground font-mono">{vocab.reading}</span>
                        )}
                    </div>
                    <div className="text-sm text-foreground/90 mb-2">{vocab.meaning}</div>
                    {vocab.usage && (
                        <div className="text-xs text-muted-foreground italic bg-muted/30 p-2 rounded">{vocab.usage}</div>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {onGoToArticle && article && (
                        <Button variant="ghost" size="sm" onClick={onGoToArticle} title={article.title}>
                            <ExternalLink size={14} />
                        </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={onDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10">
                        <Trash2 size={14} />
                    </Button>
                </div>
            </div>
            {/* Source Article */}
            {vocab.source_article_title && (
                <div className="mt-3 pt-2 border-t border-border/50 text-xs text-muted-foreground flex items-center gap-1">
                    <BookOpen size={10} />
                    <span>来源: {article ? vocab.source_article_title : <span className="line-through opacity-70">{vocab.source_article_title} (已删除)</span>}</span>
                </div>
            )}
        </div>
    );
}

// Grammar Card Component
function GrammarCard({
    grammar,
    article,
    onDelete,
    onGoToArticle,
}: {
    grammar: FavoriteGrammar;
    article?: Article;
    onDelete: () => void;
    onGoToArticle?: () => void;
}) {
    return (
        <div className="relative pl-4 border-l-2 border-primary/50 bg-card border-y border-r border-border p-4 rounded-r-lg hover:border-r-primary/30 hover:border-y-primary/30 transition-colors">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <h5 className="font-semibold text-sm text-foreground mb-1">{grammar.point}</h5>
                    <p className="text-sm text-muted-foreground leading-relaxed">{grammar.explanation}</p>
                    {grammar.example && (
                        <div className="text-xs text-muted-foreground mt-2 italic bg-muted/30 p-2 rounded">例: {grammar.example}</div>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {onGoToArticle && article && (
                        <Button variant="ghost" size="sm" onClick={onGoToArticle} title={article.title}>
                            <ExternalLink size={14} />
                        </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={onDelete} className="text-destructive hover:text-destructive hover:bg-destructive/10">
                        <Trash2 size={14} />
                    </Button>
                </div>
            </div>
            {/* Source Article */}
            {grammar.source_article_title && (
                <div className="mt-3 pt-2 border-t border-border/50 text-xs text-muted-foreground flex items-center gap-1">
                    <BookOpen size={10} />
                    <span>来源: {article ? grammar.source_article_title : <span className="line-through opacity-70">{grammar.source_article_title} (已删除)</span>}</span>
                </div>
            )}
        </div>
    );
}
