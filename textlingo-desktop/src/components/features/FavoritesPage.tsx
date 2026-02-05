import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/tabs";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger
} from "../ui/dropdown-menu";
import {
    BookOpen,
    SpellCheck,
    Trash2,
    ExternalLink,
    Loader2,
    ArrowLeft,
    Download,
    Upload,
    Copy,
    FileDown,
    Check,
    MoreHorizontal
} from "lucide-react";
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
    };

    // 下载 TXT 文件
    const handleDownloadTxt = () => {
        if (vocabularies.length === 0) return;
        const text = getPlainTextExport();
        const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "openkoto_vocabulary.txt";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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
        a.download = "openkoto_vocabulary.json";
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

    const renderImportExportButtons = () => (
        <div className="flex items-center gap-2">
            <input
                type="file"
                ref={fileInputRef}
                accept=".json"
                onChange={handleImportJson}
                className="hidden"
            />

            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-2 text-primary hover:text-primary hover:bg-primary/5 border-primary/20">
                        <MoreHorizontal size={16} />
                        {t("favorites.actions", "管理列表")}
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                    {vocabularies.length > 0 && (
                        <>
                            <DropdownMenuLabel>{t("favorites.exportWordList", "导出单词列表")}</DropdownMenuLabel>
                            <DropdownMenuItem onClick={handleCopyToClipboard} className="cursor-pointer">
                                <Copy className="mr-2 h-4 w-4" />
                                <div className="flex flex-col gap-0.5">
                                    <span>{copySuccess ? t("favorites.copied", "已复制") : t("favorites.copyToClipboard", "复制到剪贴板")}</span>
                                    <span className="text-[10px] text-muted-foreground">{t("favorites.exportWordListDesc", "导入任意背单词软件")}</span>
                                </div>
                                {copySuccess && <Check className="ml-auto h-4 w-4 text-green-500" />}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleDownloadTxt} className="cursor-pointer">
                                <FileDown className="mr-2 h-4 w-4" />
                                <div className="flex flex-col gap-0.5">
                                    <span>{t("favorites.downloadTxt", "下载 TXT 文件")}</span>
                                    <span className="text-[10px] text-muted-foreground">{t("favorites.exportWordListDesc", "导入任意背单词软件")}</span>
                                </div>
                            </DropdownMenuItem>

                            <DropdownMenuSeparator />

                            <DropdownMenuLabel>{t("favorites.backupAndShare", "备份与共享")}</DropdownMenuLabel>
                            <DropdownMenuItem onClick={handleExportJson} className="cursor-pointer">
                                <Download className="mr-2 h-4 w-4" />
                                <div className="flex flex-col gap-0.5">
                                    <span>{t("favorites.exportJson", "导出 JSON")}</span>
                                    <span className="text-[10px] text-muted-foreground">{t("favorites.shareDesc", "本软件之间共享")}</span>
                                </div>
                            </DropdownMenuItem>
                        </>
                    )}

                    <DropdownMenuItem onClick={() => fileInputRef.current?.click()} className="cursor-pointer">
                        <Upload className="mr-2 h-4 w-4" />
                        <div className="flex flex-col gap-0.5">
                            <span>{t("favorites.importJson", "导入 JSON")}</span>
                            <span className="text-[10px] text-muted-foreground">{t("favorites.shareDesc", "本软件之间共享")}</span>
                        </div>
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    );

    return (
        <div className="h-full max-w-5xl mx-auto p-8 flex flex-col bg-background/50">
            <div className="flex items-center gap-4 mb-8">
                <Button variant="ghost" size="icon" onClick={onBack} className="hover:bg-primary/10 hover:text-primary transition-colors">
                    <ArrowLeft size={20} />
                </Button>
                <div>
                    <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
                        {t("favorites.title", "我的收藏")}
                    </h2>
                    <p className="text-sm text-muted-foreground/80 mt-1">
                        {t("favorites.subtitle", "管理您收藏的单词与语法")}
                    </p>
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col space-y-6">
                <TabsList className="w-fit bg-muted/50 border border-border/50 p-1">
                    <TabsTrigger
                        value="vocabulary"
                        className="gap-2 px-4 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all"
                    >
                        <BookOpen size={14} />
                        {t("favorites.vocabulary", "单词收藏")}
                        <span className="text-xs opacity-60 ml-1 bg-primary/10 px-1.5 py-0.5 rounded-full">
                            {vocabularies.length}
                        </span>
                    </TabsTrigger>
                    <TabsTrigger
                        value="grammar"
                        className="gap-2 px-4 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all"
                    >
                        <SpellCheck size={14} />
                        {t("favorites.grammar", "语法收藏")}
                        <span className="text-xs opacity-60 ml-1 bg-primary/10 px-1.5 py-0.5 rounded-full">
                            {grammars.length}
                        </span>
                    </TabsTrigger>
                </TabsList>

                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="animate-spin text-primary" size={32} />
                    </div>
                ) : (
                    <div className="flex-1 overflow-y-auto pr-2 min-h-0">
                        <TabsContent value="vocabulary" className="mt-0 h-full flex flex-col">
                            {/* 工具栏 */}
                            <div className="flex justify-end mb-6 pb-2 border-b border-border/40">
                                {renderImportExportButtons()}
                            </div>

                            {vocabularies.length === 0 ? (
                                <EmptyState
                                    icon={<BookOpen size={48} />}
                                    title={t("favorites.noVocabulary", "暂无单词收藏")}
                                    description={t("favorites.noVocabularyDesc", "在文章学习中点击单词旁的收藏按钮即可添加")}
                                />
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
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

                        <TabsContent value="grammar" className="mt-0 h-full flex flex-col">
                            {grammars.length === 0 ? (
                                <EmptyState
                                    icon={<SpellCheck size={48} />}
                                    title={t("favorites.noGrammar", "暂无语法收藏")}
                                    description={t("favorites.noGrammarDesc", "在文章学习中点击语法点旁的收藏按钮即可添加")}
                                />
                            ) : (
                                <div className="space-y-4 pb-8">
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
        <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="mb-6 p-6 rounded-full bg-muted/30 text-muted-foreground/50 border border-border/50">
                {icon}
            </div>
            <h3 className="text-lg font-semibold mb-2 text-foreground">{title}</h3>
            <p className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed">{description}</p>
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
        <div className="group relative bg-card hover:bg-gradient-to-br hover:from-card hover:to-primary/5 border border-border/50 hover:border-primary/20 p-5 rounded-xl transition-all duration-300 shadow-sm hover:shadow-md">
            <div className="flex justify-between items-start mb-3">
                <div className="flex items-baseline gap-2">
                    <span className="font-bold text-lg text-primary">{vocab.word}</span>
                    {vocab.reading && (
                        <span className="text-xs text-muted-foreground/80 font-mono tracking-wide">{vocab.reading}</span>
                    )}
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onGoToArticle && article && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-primary"
                            onClick={onGoToArticle}
                            title={article.title}
                        >
                            <ExternalLink size={14} />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        onClick={onDelete}
                    >
                        <Trash2 size={14} />
                    </Button>
                </div>
            </div>

            <div className="space-y-2 mb-3">
                <div className="text-sm text-foreground/90 leading-relaxed font-medium">{vocab.meaning}</div>
                {vocab.usage && (
                    <div className="inline-block text-xs text-primary/80 bg-primary/5 px-2 py-1 rounded-md border border-primary/10">
                        {vocab.usage}
                    </div>
                )}
            </div>

            {/* Source Article */}
            {vocab.source_article_title && (
                <div className="pt-3 mt-1 border-t border-border/30 text-[10px] text-muted-foreground/60 flex items-center gap-1.5 truncate">
                    <BookOpen size={10} />
                    <span className="truncate">
                        {article ? vocab.source_article_title : <span className="line-through decoration-muted-foreground/50 opacity-70">{vocab.source_article_title} (已删除)</span>}
                    </span>
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
        <div className="group relative bg-card hover:bg-primary/[0.02] border border-border/60 hover:border-primary/20 p-5 rounded-xl transition-all duration-300 shadow-sm hover:shadow-md">
            <div className="absolute left-0 top-4 bottom-4 w-1 bg-primary/40 rounded-r-lg group-hover:bg-primary transition-colors"></div>

            <div className="pl-4 flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                    <h5 className="font-bold text-base text-foreground group-hover:text-primary transition-colors flex items-center gap-2">
                        {grammar.point}
                    </h5>
                    <p className="text-sm text-muted-foreground leading-relaxed">{grammar.explanation}</p>
                    {grammar.example && (
                        <div className="bg-muted/30 p-3 rounded-lg border border-border/50 text-sm text-foreground/80 italic relative mt-3">
                            <span className="absolute top-2 left-2 text-primary/10 font-serif text-4xl leading-none">"</span>
                            <span className="relative z-10">{grammar.example}</span>
                        </div>
                    )}
                </div>

                <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onGoToArticle && article && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-primary"
                            onClick={onGoToArticle}
                            title={article.title}
                        >
                            <ExternalLink size={16} />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        onClick={onDelete}
                    >
                        <Trash2 size={16} />
                    </Button>
                </div>
            </div>

            {/* Source Article */}
            {grammar.source_article_title && (
                <div className="pl-4 mt-4 pt-3 border-t border-border/30 text-[10px] text-muted-foreground/60 flex items-center gap-1.5">
                    <BookOpen size={10} />
                    <span>
                        {article ? grammar.source_article_title : <span className="line-through decoration-muted-foreground/50 opacity-70">{grammar.source_article_title} (已删除)</span>}
                    </span>
                </div>
            )}
        </div>
    );
}
