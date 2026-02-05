/**
 * TXT 纯文本阅读器组件
 * 支持分页显示、字体调整、文本选择
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../ui/button";
import {
    ChevronLeft,
    ChevronRight,
    Minus,
    Plus,
    Bookmark as BookmarkIcon,
    BookmarkPlus,
} from "lucide-react";
import { BookmarkSidebar } from "./BookmarkSidebar";
import { Bookmark } from "../../types";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "../ui/dialog";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";

interface TxtReaderProps {
    /** TXT 文件内容 */
    content: string;
    /** 书籍标题 */
    title?: string;
    /** 书籍文件路径 */
    bookPath?: string;
    /** 选中文本时的回调 */
    onTextSelect?: (text: string) => void;
    /** 初始字体大小 */
    fontSize?: number;
    /** 返回按钮回调 */
    onBack?: () => void;
}

// 每页大约显示的字符数
const CHARS_PER_PAGE = 2000;

export function TxtReader({
    content,
    title,
    bookPath,
    onTextSelect,
    fontSize: initialFontSize = 18,
    onBack,
}: TxtReaderProps) {
    const { t } = useTranslation();

    // 当前页码 (0-indexed)
    const [currentPage, setCurrentPage] = useState(0);

    // 字体大小
    const [fontSize, setFontSize] = useState(initialFontSize);

    // 选中的文本
    const [selectedText, setSelectedText] = useState("");

    // 书签相关状态
    const [isBookmarkSidebarOpen, setIsBookmarkSidebarOpen] = useState(false);
    const [isAddBookmarkDialogOpen, setIsAddBookmarkDialogOpen] = useState(false);
    const [bookmarkTitle, setBookmarkTitle] = useState("");
    const [bookmarkNote, setBookmarkNote] = useState("");
    const [bookmarkSelectedText, setBookmarkSelectedText] = useState("");

    // 将内容分页
    const pages = useMemo(() => {
        if (!content) return [""];

        const result: string[] = [];
        const paragraphs = content.split(/\n+/);
        let currentPageContent = "";

        for (const paragraph of paragraphs) {
            if (currentPageContent.length + paragraph.length > CHARS_PER_PAGE) {
                // 当前页已满，保存并开始新页
                if (currentPageContent.trim()) {
                    result.push(currentPageContent.trim());
                }
                currentPageContent = paragraph + "\n\n";
            } else {
                currentPageContent += paragraph + "\n\n";
            }
        }

        // 保存最后一页
        if (currentPageContent.trim()) {
            result.push(currentPageContent.trim());
        }

        return result.length > 0 ? result : [""];
    }, [content]);

    // 总页数
    const totalPages = pages.length;

    // 翻页
    const handlePrevPage = useCallback(() => {
        setCurrentPage((prev) => Math.max(0, prev - 1));
    }, []);

    const handleNextPage = useCallback(() => {
        setCurrentPage((prev) => Math.min(totalPages - 1, prev + 1));
    }, [totalPages]);

    // 键盘翻页支持
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "ArrowLeft" || e.key === "PageUp") {
                handlePrevPage();
            } else if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
                handleNextPage();
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [handlePrevPage, handleNextPage]);

    // 处理文本选择
    const handleMouseUp = useCallback(() => {
        const selection = window.getSelection();
        if (selection) {
            const text = selection.toString().trim();
            if (text.length > 0) {
                setSelectedText(text);
                onTextSelect?.(text);
            }
        }
    }, [onTextSelect]);

    // 调整字体大小
    const increaseFontSize = () => {
        setFontSize((prev) => Math.min(prev + 2, 32));
    };

    const decreaseFontSize = () => {
        setFontSize((prev) => Math.max(prev - 2, 12));
    };

    // 打开添加书签对话框
    const handleOpenAddBookmark = () => {
        // 获取当前选中的文本
        const selection = window.getSelection();
        const currentSelected = selection ? selection.toString().trim() : "";

        setBookmarkTitle(currentSelected || `第 ${currentPage + 1} 页`);
        setBookmarkNote("");
        setBookmarkSelectedText(currentSelected);
        setIsAddBookmarkDialogOpen(true);
    };

    // 添加书签
    const handleAddBookmark = async () => {
        if (!bookPath) {
            console.error("No book path provided");
            return;
        }

        try {
            await invoke("add_bookmark_cmd", {
                bookPath,
                bookType: "txt",
                title: bookmarkTitle,
                note: bookmarkNote || null,
                selectedText: bookmarkSelectedText || null,
                pageNumber: currentPage + 1, // 页码从1开始
                epubCfi: null,
                color: null,
            });
            setIsAddBookmarkDialogOpen(false);
            setBookmarkSelectedText("");
        } catch (error) {
            console.error("Failed to add bookmark:", error);
        }
    };

    // 跳转到书签位置
    const handleJumpToBookmark = (bookmark: Bookmark) => {
        if (bookmark.page_number) {
            setCurrentPage(bookmark.page_number - 1); // 页码从1开始，需要转换为0-indexed
        }
        setIsBookmarkSidebarOpen(false);
    };

    return (
        <div className="h-full flex flex-col bg-background">
            {/* 工具栏 */}
            <div className="flex items-center justify-between p-3 border-b border-border bg-card/50 backdrop-blur-sm gap-4">
                <div className="flex items-center gap-2 shrink-0">
                    {onBack && (
                        <Button variant="ghost" size="sm" onClick={onBack}>
                            <ChevronLeft size={18} />
                        </Button>
                    )}
                    <h2 className="text-sm font-medium truncate max-w-[150px]">
                        {title || t("txtReader.untitled", "未命名文本")}
                    </h2>
                </div>

                {/* 进度条滑块 */}
                <div className="flex-1 max-w-md flex items-center gap-2 mx-2">
                    <span className="text-xs text-muted-foreground w-12 text-right">
                        {currentPage + 1} / {totalPages}
                    </span>
                    <input
                        type="range"
                        min="0"
                        max={Math.max(0, totalPages - 1)}
                        value={currentPage}
                        onChange={(e) => setCurrentPage(parseInt(e.target.value))}
                        className="flex-1 h-1.5 bg-muted rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                        style={{
                            backgroundSize: `${(currentPage / Math.max(1, totalPages - 1)) * 100}% 100%`,
                            backgroundImage: `linear-gradient(var(--primary), var(--primary))`,
                            backgroundRepeat: 'no-repeat'
                        }}
                    />
                </div>

                <div className="flex items-center gap-3 shrink-0">
                    {/* 书签按钮 */}
                    {bookPath && (
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleOpenAddBookmark}
                                className="h-8 px-2"
                                title="添加书签"
                            >
                                <BookmarkPlus size={16} />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setIsBookmarkSidebarOpen(true)}
                                className="h-8 px-2"
                                title="书签列表"
                            >
                                <BookmarkIcon size={16} />
                            </Button>
                        </div>
                    )}

                    {/* 字体大小控制 */}
                    <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1 border border-border">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={decreaseFontSize}
                            className="h-7 w-7 p-0"
                            title={t("txtReader.decreaseFontSize", "减小字体")}
                        >
                            <Minus size={14} />
                        </Button>
                        <span className="text-xs text-muted-foreground w-6 text-center">
                            {fontSize}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={increaseFontSize}
                            className="h-7 w-7 p-0"
                            title={t("txtReader.increaseFontSize", "增大字体")}
                        >
                            <Plus size={14} />
                        </Button>
                    </div>

                    {/* 页码显示 */}
                    <div className="text-sm text-muted-foreground">
                        {currentPage + 1} / {totalPages}
                    </div>
                </div>
            </div>

            {/* 阅读区 */}
            <div className="flex-1 flex overflow-hidden relative">
                {/* 翻页按钮 - 左 */}
                <button
                    onClick={handlePrevPage}
                    disabled={currentPage === 0}
                    className="absolute left-2 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-background/80 border border-border shadow-sm hover:bg-muted transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    title={t("txtReader.prevPage", "上一页")}
                >
                    <ChevronLeft size={20} />
                </button>

                {/* 文本内容 */}
                <div
                    className="flex-1 overflow-y-auto px-12 py-8 md:px-20 lg:px-32"
                    onMouseUp={handleMouseUp}
                >
                    <div
                        className="max-w-3xl mx-auto whitespace-pre-wrap text-foreground leading-relaxed"
                        style={{
                            fontSize: `${fontSize}px`,
                            lineHeight: 2,
                        }}
                    >
                        {pages[currentPage]}
                    </div>
                </div>

                {/* 翻页按钮 - 右 */}
                <button
                    onClick={handleNextPage}
                    disabled={currentPage === totalPages - 1}
                    className="absolute right-2 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-background/80 border border-border shadow-sm hover:bg-muted transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    title={t("txtReader.nextPage", "下一页")}
                >
                    <ChevronRight size={20} />
                </button>
            </div>

            {/* 底部进度条 */}
            <div className="h-1 bg-muted">
                <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${((currentPage + 1) / totalPages) * 100}%` }}
                />
            </div>

            {/* 书签侧边栏 */}
            {bookPath && (
                <BookmarkSidebar
                    bookPath={bookPath}
                    bookType="txt"
                    onJumpToBookmark={handleJumpToBookmark}
                    isOpen={isBookmarkSidebarOpen}
                    onClose={() => setIsBookmarkSidebarOpen(false)}
                />
            )}

            {/* 添加书签对话框 */}
            <Dialog open={isAddBookmarkDialogOpen} onOpenChange={setIsAddBookmarkDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>添加书签</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        {bookmarkSelectedText && (
                            <div className="space-y-2">
                                <Label>选中的文字</Label>
                                <div className="p-3 bg-muted/50 rounded-lg text-sm max-h-24 overflow-y-auto border border-border">
                                    "{bookmarkSelectedText}"
                                </div>
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="bookmark-title">标题</Label>
                            <Input
                                id="bookmark-title"
                                value={bookmarkTitle}
                                onChange={(e) => setBookmarkTitle(e.target.value)}
                                placeholder="书签标题"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="bookmark-note">笔记（可选）</Label>
                            <Textarea
                                id="bookmark-note"
                                value={bookmarkNote}
                                onChange={(e) => setBookmarkNote(e.target.value)}
                                placeholder="添加笔记..."
                                rows={3}
                            />
                        </div>
                        <div className="text-sm text-muted-foreground">
                            将在第 {currentPage + 1} 页添加书签
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsAddBookmarkDialogOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleAddBookmark}>添加</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
