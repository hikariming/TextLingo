import React, { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { ArticleSegment, SegmentExplanation, VocabularyItem, GrammarPoint } from "../../types";
import { Button } from "../ui/button";
import { RefreshCw, BookOpen, MessageCircle, Languages, SpellCheck, Star, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { SelectPackDialog } from "./SelectPackDialog";

interface ArticleExplanationPanelProps {
    segment: ArticleSegment | null;
    explanation: SegmentExplanation | null;
    isLoading: boolean;
    streamingContent?: string;
    onRegenerate: () => void;
    // 文章信息，用于收藏时保存来源
    articleId?: string;
    articleTitle?: string;
}

export const ArticleExplanationPanel: React.FC<ArticleExplanationPanelProps> = ({
    segment,
    explanation,
    isLoading,
    streamingContent,
    onRegenerate,
    articleId,
    articleTitle,
}) => {
    const { t } = useTranslation();
    // 跟踪已收藏的单词和语法点（仅用于UI反馈）
    const [favoritedVocabs, setFavoritedVocabs] = useState<Set<string>>(new Set());
    const [favoritedGrammars, setFavoritedGrammars] = useState<Set<string>>(new Set());
    const [isPackDialogOpen, setIsPackDialogOpen] = useState(false);
    const [pendingVocabFavorite, setPendingVocabFavorite] = useState<{
        item: VocabularyItem;
        key: string;
    } | null>(null);

    // 收藏单词
    const handleFavoriteVocab = async (item: VocabularyItem, idx: number) => {
        const key = `${item.word}-${idx}`;
        if (favoritedVocabs.has(key)) return;
        setPendingVocabFavorite({ item, key });
        setIsPackDialogOpen(true);
    };

    const handleConfirmVocabPackSelection = async (packIds: string[]) => {
        if (!pendingVocabFavorite) return;
        try {
            await invoke("add_favorite_vocabulary_cmd", {
                word: pendingVocabFavorite.item.word,
                meaning: pendingVocabFavorite.item.meaning,
                usage: pendingVocabFavorite.item.usage || "",
                explanation: null,
                example: pendingVocabFavorite.item.example,
                reading: pendingVocabFavorite.item.reading,
                sourceArticleId: articleId,
                sourceArticleTitle: articleTitle,
                packIds,
            });
            setFavoritedVocabs(prev => new Set(prev).add(pendingVocabFavorite.key));
        } catch (err) {
            console.error("Failed to favorite vocabulary:", err);
        } finally {
            setPendingVocabFavorite(null);
        }
    };

    // 收藏语法点
    const handleFavoriteGrammar = async (point: GrammarPoint, idx: number) => {
        const key = `${point.point}-${idx}`;
        if (favoritedGrammars.has(key)) return;

        try {
            await invoke("add_favorite_grammar_cmd", {
                point: point.point,
                explanation: point.explanation,
                example: point.example,
                sourceArticleId: articleId,
                sourceArticleTitle: articleTitle,
            });
            setFavoritedGrammars(prev => new Set(prev).add(key));
        } catch (err) {
            console.error("Failed to favorite grammar:", err);
        }
    };

    if (!segment) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
                <BookOpen size={48} className="mb-4 opacity-50" />
                <h3 className="text-lg font-medium mb-2">{t("articleReader.selectSegmentHint") || "Select a segment"}</h3>
                <p className="text-sm">{t("articleReader.selectSegmentDesc") || "Click on any sentence in the article to view its detailed explanation."}</p>
            </div>
        );
    }

    const hasContent = explanation || streamingContent;

    return (
        <div className="h-full flex flex-col overflow-hidden bg-background border-l border-border">
            {/* Header */}
            <div className="px-4 py-3 border-b border-border flex justify-between items-center bg-card/50">
                <div className="flex items-center gap-2">
                    <span className="bg-primary/20 text-primary text-xs font-bold px-2 py-0.5 rounded-full">
                        #{segment.order}
                    </span>
                    <span className="font-medium text-sm text-foreground">
                        {t("articleReader.segmentExplanation") || "Segment Explanation"}
                    </span>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onRegenerate}
                    disabled={isLoading}
                    title="Regenerate Explanation"
                >
                    <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
                </Button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">



                {!hasContent && !isLoading && (
                    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                        <Button onClick={onRegenerate}>
                            {t("articleReader.generateExplanation") || "Generate Explanation"}
                        </Button>
                    </div>
                )}

                {/* Loading Skeleton */}
                {isLoading && !hasContent && (
                    <div className="space-y-6 animate-pulse">
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 pb-2 border-b border-border">
                                <div className="h-4 w-4 bg-muted rounded"></div>
                                <div className="h-4 w-24 bg-muted rounded"></div>
                            </div>
                            <div className="space-y-2">
                                <div className="h-4 w-3/4 bg-muted rounded"></div>
                                <div className="h-4 w-1/2 bg-muted rounded"></div>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center gap-2 pb-2 border-b border-border">
                                <div className="h-4 w-4 bg-muted rounded"></div>
                                <div className="h-4 w-24 bg-muted rounded"></div>
                            </div>
                            <div className="space-y-3">
                                <div className="h-20 bg-muted rounded"></div>
                                <div className="h-20 bg-muted rounded"></div>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center gap-2 pb-2 border-b border-border">
                                <div className="h-4 w-4 bg-muted rounded"></div>
                                <div className="h-4 w-24 bg-muted rounded"></div>
                            </div>
                            <div className="space-y-2">
                                <div className="h-4 w-full bg-muted rounded"></div>
                                <div className="h-4 w-full bg-muted rounded"></div>
                                <div className="h-4 w-2/3 bg-muted rounded"></div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Translation */}
                {(explanation?.translation || (isLoading && streamingContent)) && (
                    <Section
                        icon={<Languages size={18} className="text-primary" />}
                        title={t("articleReader.translation") || "Translation"}
                    >
                        <div className="text-foreground leading-relaxed">
                            {explanation?.translation || (
                                isLoading && streamingContent?.includes("Translation") ? (t("articleReader.translating") || "Translating...") : null
                            )}
                            {/* Fallback for streaming raw text if not parsed yet */}
                            {!explanation && streamingContent && (
                                <div className="whitespace-pre-wrap text-sm text-muted-foreground">
                                    {streamingContent}
                                </div>
                            )}
                        </div>
                    </Section>
                )}

                {/* Vocabulary */}
                {explanation?.vocabulary && explanation.vocabulary.length > 0 && (
                    <Section
                        icon={<BookOpen size={18} className="text-amber-500" />}
                        title={t("articleReader.vocabulary") || "Vocabulary"}
                    >
                        <div className="space-y-3">
                            {explanation.vocabulary.map((item, idx) => {
                                const isFavorited = favoritedVocabs.has(`${item.word}-${idx}`);
                                return (
                                    <div key={idx} className="bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
                                        <div className="flex items-baseline justify-between mb-1">
                                            <div className="flex items-baseline gap-2">
                                                <span className="font-bold text-foreground">{item.word}</span>
                                                <span className="text-xs text-muted-foreground font-mono">{item.reading}</span>
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleFavoriteVocab(item, idx)}
                                                className={isFavorited ? "text-amber-500" : "text-muted-foreground hover:text-amber-500"}
                                                title={isFavorited ? t("favorites.favorited") : t("favorites.favoriteWord")}
                                            >
                                                {isFavorited ? <Check size={14} /> : <Star size={14} />}
                                            </Button>
                                        </div>
                                        <div className="text-sm text-muted-foreground mb-1">{item.meaning}</div>
                                    </div>
                                );
                            })}
                        </div>
                    </Section>
                )}

                {/* Grammar */}
                {explanation?.grammar_points && explanation.grammar_points.length > 0 && (
                    <Section
                        icon={<SpellCheck size={18} className="text-purple-500" />}
                        title={t("articleReader.grammar") || "Grammar"}
                    >
                        <div className="space-y-4">
                            {explanation.grammar_points.map((point, idx) => {
                                const isFavorited = favoritedGrammars.has(`${point.point}-${idx}`);
                                return (
                                    <div key={idx} className="relative pl-4 border-l-2 border-purple-500/50">
                                        <div className="flex items-start justify-between">
                                            <h5 className="font-semibold text-sm text-foreground mb-1">{point.point}</h5>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleFavoriteGrammar(point, idx)}
                                                className={isFavorited ? "text-purple-500" : "text-muted-foreground hover:text-purple-500"}
                                                title={isFavorited ? t("favorites.favorited") : t("favorites.favoriteGrammar")}
                                            >
                                                {isFavorited ? <Check size={14} /> : <Star size={14} />}
                                            </Button>
                                        </div>
                                        <p className="text-sm text-muted-foreground leading-relaxed">{point.explanation}</p>
                                    </div>
                                );
                            })}
                        </div>
                    </Section>
                )}

                {/* General Explanation */}
                {explanation?.explanation && (
                    <Section
                        icon={<MessageCircle size={18} className="text-green-500" />}
                        title={t("articleReader.notes") || "Notes"}
                    >
                        <div className="text-sm text-muted-foreground leading-relaxed">
                            <ReactMarkdown>{explanation.explanation}</ReactMarkdown>
                        </div>
                    </Section>
                )}

                <SelectPackDialog
                    open={isPackDialogOpen}
                    onOpenChange={(open) => {
                        setIsPackDialogOpen(open);
                        if (!open) {
                            setPendingVocabFavorite(null);
                        }
                    }}
                    onConfirm={handleConfirmVocabPackSelection}
                />
            </div>
        </div>
    );
};

const Section: React.FC<{ icon: React.ReactNode; title: string; children: React.ReactNode }> = ({ icon, title, children }) => (
    <div className="space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-border">
            {icon}
            <h4 className="font-semibold text-muted-foreground uppercase text-xs tracking-wider">{title}</h4>
        </div>
        {children}
    </div>
);
