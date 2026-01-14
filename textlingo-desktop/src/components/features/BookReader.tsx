/**
 * 书籍阅读器包装组件
 * 左侧是 EPUB/TXT 阅读器，右侧是 AI 助手面板
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import { Button } from "../ui/Button";
import { ChevronLeft, BookOpen, PanelRightClose, PanelRightOpen } from "lucide-react";
import { Article } from "../../types";
import { EpubReader } from "./EpubReader";
import { TxtReader } from "./TxtReader";
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

    // 判断书籍类型
    const isEpub = article.book_type === "epub";
    const isTxt = article.book_type === "txt";

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
