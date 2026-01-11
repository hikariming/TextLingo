import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent, DialogFooter } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import { Star, BookOpen, SpellCheck, Trash2, ExternalLink, Loader2 } from "lucide-react";
import type { FavoriteVocabulary, FavoriteGrammar, Article } from "../../types";

interface FavoritesDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSelectArticle?: (articleId: string) => void;
}

export function FavoritesDialog({ isOpen, onClose, onSelectArticle }: FavoritesDialogProps) {
    const { t } = useTranslation();
    const [vocabularies, setVocabularies] = useState<FavoriteVocabulary[]>([]);
    const [grammars, setGrammars] = useState<FavoriteGrammar[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState("vocabulary");
    const [articles, setArticles] = useState<Map<string, Article>>(new Map());

    // 加载收藏数据
    const loadFavorites = async () => {
        setIsLoading(true);
        try {
            const [vocabList, grammarList] = await Promise.all([
                invoke<FavoriteVocabulary[]>("list_favorite_vocabularies_cmd"),
                invoke<FavoriteGrammar[]>("list_favorite_grammars_cmd"),
            ]);
            setVocabularies(vocabList);
            setGrammars(grammarList);

            // 加载关联的文章标题（用于跳转）
            const articleIds = new Set<string>();
            vocabList.forEach(v => v.source_article_id && articleIds.add(v.source_article_id));
            grammarList.forEach(g => g.source_article_id && articleIds.add(g.source_article_id));

            const articleMap = new Map<string, Article>();
            for (const id of articleIds) {
                try {
                    const article = await invoke<Article>("get_article", { id });
                    articleMap.set(id, article);
                } catch {
                    // 文章可能已被删除，忽略错误
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
        if (isOpen) {
            loadFavorites();
        }
    }, [isOpen]);

    // 删除单词收藏
    const handleDeleteVocabulary = async (id: string) => {
        try {
            await invoke("delete_favorite_vocabulary_cmd", { id });
            setVocabularies(prev => prev.filter(v => v.id !== id));
        } catch (err) {
            console.error("Failed to delete vocabulary favorite:", err);
        }
    };

    // 删除语法收藏
    const handleDeleteGrammar = async (id: string) => {
        try {
            await invoke("delete_favorite_grammar_cmd", { id });
            setGrammars(prev => prev.filter(g => g.id !== id));
        } catch (err) {
            console.error("Failed to delete grammar favorite:", err);
        }
    };

    // 跳转到来源文章
    const handleGoToArticle = (articleId: string) => {
        if (onSelectArticle) {
            onSelectArticle(articleId);
            onClose();
        }
    };

    return (
        <Dialog isOpen={isOpen} onClose={onClose} title={t("favorites.title", "我的收藏")}>
            <DialogContent className="min-h-[400px]">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList>
                        <TabsTrigger value="vocabulary" className="gap-2">
                            <BookOpen size={14} />
                            {t("favorites.vocabulary", "单词收藏")}
                            <span className="text-xs text-gray-400">({vocabularies.length})</span>
                        </TabsTrigger>
                        <TabsTrigger value="grammar" className="gap-2">
                            <SpellCheck size={14} />
                            {t("favorites.grammar", "语法收藏")}
                            <span className="text-xs text-gray-400">({grammars.length})</span>
                        </TabsTrigger>
                    </TabsList>

                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="animate-spin text-gray-400" size={24} />
                        </div>
                    ) : (
                        <>
                            <TabsContent value="vocabulary" className="mt-4">
                                {vocabularies.length === 0 ? (
                                    <EmptyState
                                        icon={<BookOpen size={40} />}
                                        title={t("favorites.noVocabulary", "暂无单词收藏")}
                                        description={t("favorites.noVocabularyDesc", "在文章学习中点击单词旁的收藏按钮即可添加")}
                                    />
                                ) : (
                                    <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
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

                            <TabsContent value="grammar" className="mt-4">
                                {grammars.length === 0 ? (
                                    <EmptyState
                                        icon={<SpellCheck size={40} />}
                                        title={t("favorites.noGrammar", "暂无语法收藏")}
                                        description={t("favorites.noGrammarDesc", "在文章学习中点击语法点旁的收藏按钮即可添加")}
                                    />
                                ) : (
                                    <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
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
                        </>
                    )}
                </Tabs>
            </DialogContent>

            <DialogFooter>
                <Button variant="secondary" onClick={onClose}>
                    {t("common.close", "关闭")}
                </Button>
            </DialogFooter>
        </Dialog>
    );
}

// 空状态组件
function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-12 text-center text-gray-500">
            <div className="mb-4 opacity-50">{icon}</div>
            <h3 className="text-lg font-medium mb-2">{title}</h3>
            <p className="text-sm">{description}</p>
        </div>
    );
}

// 单词卡片组件
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
        <div className="bg-amber-950/20 p-4 rounded-lg border border-amber-900/30">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <div className="flex items-baseline gap-2 mb-1">
                        <span className="font-bold text-lg text-gray-100">{vocab.word}</span>
                        {vocab.reading && (
                            <span className="text-xs text-gray-400 font-mono">{vocab.reading}</span>
                        )}
                    </div>
                    <div className="text-sm text-gray-300 mb-2">{vocab.meaning}</div>
                    {vocab.usage && (
                        <div className="text-xs text-gray-500 italic">{vocab.usage}</div>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {onGoToArticle && article && (
                        <Button variant="ghost" size="sm" onClick={onGoToArticle} title={article.title}>
                            <ExternalLink size={14} />
                        </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={onDelete} className="text-red-400 hover:text-red-300">
                        <Trash2 size={14} />
                    </Button>
                </div>
            </div>
            {/* 来源文章 */}
            {vocab.source_article_title && (
                <div className="mt-3 pt-2 border-t border-amber-900/20 text-xs text-gray-500">
                    来源: {article ? vocab.source_article_title : <span className="line-through">{vocab.source_article_title} (已删除)</span>}
                </div>
            )}
        </div>
    );
}

// 语法卡片组件
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
        <div className="relative pl-4 border-l-2 border-purple-800 bg-purple-950/10 p-4 rounded-r-lg">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <h5 className="font-semibold text-sm text-gray-100 mb-1">{grammar.point}</h5>
                    <p className="text-sm text-gray-400 leading-relaxed">{grammar.explanation}</p>
                    {grammar.example && (
                        <p className="text-xs text-gray-500 mt-2 italic">例: {grammar.example}</p>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {onGoToArticle && article && (
                        <Button variant="ghost" size="sm" onClick={onGoToArticle} title={article.title}>
                            <ExternalLink size={14} />
                        </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={onDelete} className="text-red-400 hover:text-red-300">
                        <Trash2 size={14} />
                    </Button>
                </div>
            </div>
            {/* 来源文章 */}
            {grammar.source_article_title && (
                <div className="mt-3 pt-2 border-t border-purple-900/20 text-xs text-gray-500">
                    来源: {article ? grammar.source_article_title : <span className="line-through">{grammar.source_article_title} (已删除)</span>}
                </div>
            )}
        </div>
    );
}

// 收藏按钮组件 - 放在 Header 使用
interface FavoritesButtonProps {
    onSelectArticle?: (articleId: string) => void;
}

export function FavoritesButton({ onSelectArticle }: FavoritesButtonProps) {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);

    const handleSelectArticle = (articleId: string) => {
        if (onSelectArticle) {
            onSelectArticle(articleId);
        }
        setIsOpen(false);
    };

    return (
        <>
            <Button variant="secondary" onClick={() => setIsOpen(true)} className="gap-2">
                <Star size={16} />
                {t("header.favorites", "收藏夹")}
            </Button>
            <FavoritesDialog
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                onSelectArticle={handleSelectArticle}
            />
        </>
    );
}
