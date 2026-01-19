/**
 * 书籍阅读器包装组件
 * 左侧是 EPUB/TXT 阅读器，右侧是 AI 助手面板
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import { Button } from "../ui/Button";
import { ChevronLeft, BookOpen, PanelRightClose, PanelRightOpen, Languages, Loader2 } from "lucide-react";
import { Article } from "../../types";
import { EpubReader } from "./EpubReader";
import { TxtReader } from "./TxtReader";
import { PdfReader } from "./PdfReader";
import { ArticleChatAssistant } from "./ArticleChatAssistant";

interface BookReaderProps {
    article: Article;
    onBack?: () => void;
    onUpdate?: () => void;
}

export function BookReader({ article, onBack }: BookReaderProps) {
    const { t } = useTranslation();

    // 选中的文本（用于 AI 分析）
    const [selectedText, setSelectedText] = useState("");

    // 显示 AI 助手面板
    const [showAssistant, setShowAssistant] = useState(true);

    // 当前活动的助手标签
    const [activeTab, setActiveTab] = useState<"chat">("chat");

    // PDF翻译状态
    const [isTranslating, setIsTranslating] = useState(false);
    const [translationResult, setTranslationResult] = useState<{
        mono_pdf?: string;
        dual_pdf?: string;
    } | null>(null);

    // 判断书籍类型
    const isEpub = article.book_type === "epub";
    const isTxt = article.book_type === "txt";
    const isPdf = article.book_type === "pdf";

    // 处理文本选择
    const handleTextSelect = (text: string) => {
        setSelectedText(text);
        setShowAssistant(true);
    };

    // 获取书籍文件 URL
    const getBookUrl = () => {
        if (!article.book_path) return "";

        // 如果已经是 HTTP URL，直接返回
        if (article.book_path.startsWith("http")) return article.book_path;

        // 对于本地文件，使用本地资源服务器提供
        const filename = article.book_path.split(/[/\\]/).pop();
        if (filename) {
            return `http://127.0.0.1:19420/book/${encodeURIComponent(filename)}`;
        }

        return article.book_path;
    };

    // PDF全文翻译处理
    const handlePdfTranslate = async () => {
        if (!article.book_path || isTranslating) return;

        try {
            setIsTranslating(true);
            setTranslationResult(null);

            // 获取配置
            const config = await invoke<{
                target_language?: string;
                active_model_id?: string;
                model_configs?: Array<{ id: string; api_provider: string; api_key: string; model: string; base_url?: string }>;
            }>("get_config");

            console.log("[PDF Translate] Config loaded:", config);

            const activeModel = config.model_configs?.find(m => m.id === config.active_model_id);
            if (!activeModel) {
                console.error("[PDF Translate] No active model found. Active ID:", config.active_model_id);
                throw new Error(t("pdfTranslate.noActiveModel", "请先在设置中配置并激活一个AI模型"));
            }

            const targetLang = config.target_language || "zh";
            const sourceLang = "en"; // 默认源语言

            console.log("[PDF Translate] Starting with:", {
                provider: activeModel.api_provider,
                model: activeModel.model,
                targetLang,
            });

            const result = await invoke<{
                success: boolean;
                mono_pdf: string;
                dual_pdf: string;
                original_pdf: string;
            }>("translate_pdf_document", {
                pdfPath: article.book_path,
                langIn: sourceLang,
                langOut: targetLang,
                provider: activeModel.api_provider,
                apiKey: activeModel.api_key,
                model: activeModel.model,
                baseUrl: activeModel.base_url,
            });

            if (result.success) {
                setTranslationResult({
                    mono_pdf: result.mono_pdf,
                    dual_pdf: result.dual_pdf,
                });
                alert(t("pdfTranslate.success", "PDF翻译完成！\n\n纯译文: {{mono}}\n双语对照: {{dual}}", {
                    mono: result.mono_pdf,
                    dual: result.dual_pdf,
                }));
            }
        } catch (error) {
            console.error("[PDF Translate] Error:", error);
            alert(t("pdfTranslate.error", "翻译失败: {{error}}", { error: String(error) }));
        } finally {
            setIsTranslating(false);
        }
    };

    return (
        <div className="h-full flex overflow-hidden bg-background">
            {/* 左侧：书籍阅读器 */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* 顶部工具栏 */}
                <div className="flex items-center justify-between p-3 border-b border-border bg-card/50 backdrop-blur-sm">
                    <div className="flex items-center gap-3">
                        {onBack && (
                            <Button variant="ghost" size="sm" onClick={onBack}>
                                <ChevronLeft size={18} />
                            </Button>
                        )}
                        <div className="flex items-center gap-2">
                            <BookOpen size={18} className="text-purple-500" />
                            <h1 className="text-lg font-semibold truncate max-w-[300px]">
                                {article.title || t("articleReader.untitled")}
                            </h1>
                            <span className="text-xs px-2 py-0.5 bg-purple-500/10 text-purple-500 rounded-full uppercase">
                                {article.book_type}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {/* PDF 全文翻译按钮 */}
                        {isPdf && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handlePdfTranslate}
                                disabled={isTranslating}
                                title={t("pdfTranslate.button", "翻译全文")}
                                className="flex items-center gap-1.5"
                            >
                                {isTranslating ? (
                                    <Loader2 size={16} className="animate-spin" />
                                ) : (
                                    <Languages size={16} />
                                )}
                                <span>{isTranslating ? t("pdfTranslate.translating", "翻译中...") : t("pdfTranslate.button", "翻译全文")}</span>
                            </Button>
                        )}

                        {/* 翻译结果查看按钮 */}
                        {translationResult && (
                            <div className="flex items-center gap-1">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => window.open(`file://${translationResult.dual_pdf}`, '_blank')}
                                    title={t("pdfTranslate.viewDual", "查看双语对照")}
                                    className="text-green-600"
                                >
                                    📖 {t("pdfTranslate.dual", "双语")}
                                </Button>
                            </div>
                        )}

                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowAssistant(!showAssistant)}
                            title={showAssistant ? "隐藏助手" : "显示助手"}
                            className="h-8 w-8 p-0"
                        >
                            {showAssistant ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
                        </Button>
                    </div>
                </div>

                {/* 阅读器内容 */}
                <div className="flex-1 overflow-hidden">
                    {isEpub && (
                        <EpubReader
                            bookPath={getBookUrl()}
                            title={article.title}
                            onTextSelect={handleTextSelect}
                        />
                    )}
                    {isTxt && (
                        <TxtReader
                            content={article.content}
                            title={article.title}
                            onTextSelect={handleTextSelect}
                        />
                    )}
                    {isPdf && (
                        <PdfReader
                            bookPath={getBookUrl()}
                            title={article.title}
                            onTextSelect={handleTextSelect}
                        />
                    )}
                </div>
            </div>

            {/* 右侧：AI 助手面板 */}
            {showAssistant && (
                <div className="w-[350px] md:w-[400px] border-l border-border bg-card flex flex-col shrink-0">
                    <Tabs
                        value={activeTab}
                        onValueChange={(v) => setActiveTab(v as "chat")}
                        className="flex-1 flex flex-col h-full overflow-hidden"
                    >
                        <div className="px-4 py-2 border-b border-border bg-card">
                            <TabsList className="w-full">
                                <TabsTrigger value="chat" className="flex-1">
                                    {t("articleReader.chat", "对话")}
                                </TabsTrigger>
                            </TabsList>
                        </div>

                        <TabsContent value="chat" className="flex-1 overflow-hidden mt-0">
                            <ArticleChatAssistant
                                articleId={article.id}
                                articleTitle={article.title}
                                targetLanguage="zh-CN"
                                selectedText={selectedText}
                            />
                        </TabsContent>
                    </Tabs>
                </div>
            )}
        </div>
    );
}
