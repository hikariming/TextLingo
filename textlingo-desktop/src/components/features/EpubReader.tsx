/**
 * EPUB 阅读器组件
 * 使用 react-reader 库渲染 EPUB 文件
 * 支持目录导航、翻页、文本选择、进度跳转
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { ReactReader } from "react-reader";
import type { Contents, Rendition, NavItem } from "epubjs";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../ui/button";
import {
    ChevronLeft,
    ChevronRight,
    List,
    Minus,
    Plus,
    X,
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

interface EpubReaderProps {
    /** EPUB 文件的 URL 或本地路径 */
    bookPath: string;
    /** 书籍标题 */
    title?: string;
    /** 选中文本时的回调 */
    onTextSelect?: (text: string) => void;
    /** 字体大小 */
    fontSize?: number;
    /** 返回按钮回调 */
    onBack?: () => void;
}

export function EpubReader({
    bookPath,
    title,
    onTextSelect,
    fontSize: initialFontSize = 100,
    onBack,
}: EpubReaderProps) {
    const { t } = useTranslation();

    // 阅读进度位置 (CFI 字符串)
    const [location, setLocation] = useState<string | number>(0);

    // 目录数据
    const [toc, setToc] = useState<NavItem[]>([]);

    // 显示目录面板
    const [showToc, setShowToc] = useState(false);

    // 字体大小百分比
    const [fontSize, setFontSize] = useState(initialFontSize);

    // Rendition 引用
    const renditionRef = useRef<Rendition | null>(null);

    // 选中的文本
    const [, setSelectedText] = useState("");

    // 进度百分比 (0-100)
    const [progress, setProgress] = useState(0);
    // 是否正在拖动进度条
    const isSeeking = useRef(false);
    // 是否已准备好位置信息
    const [locationsReady, setLocationsReady] = useState(false);

    // 书签相关状态
    const [isBookmarkSidebarOpen, setIsBookmarkSidebarOpen] = useState(false);
    const [isAddBookmarkDialogOpen, setIsAddBookmarkDialogOpen] = useState(false);
    const [bookmarkTitle, setBookmarkTitle] = useState("");
    const [bookmarkNote, setBookmarkNote] = useState("");
    const [bookmarkSelectedText, setBookmarkSelectedText] = useState("");
    // 处理位置变化
    const handleLocationChange = useCallback((epubcifi: string) => {
        setLocation(epubcifi);

        // 如果不在拖动中，且位置信息已准备好，更新进度条
        if (!isSeeking.current && renditionRef.current && locationsReady) {
            try {
                // @ts-ignore - ebookjs 类型定义可能不完整
                const currentLocation = renditionRef.current.currentLocation();
                if (currentLocation && (currentLocation as any).start) {
                    // @ts-ignore
                    const percentage = renditionRef.current.book.locations.percentageFromCfi((currentLocation as any).start.cfi);
                    setProgress(Math.round(percentage * 100));
                }
            } catch (e) {
                console.warn("Failed to get progress:", e);
            }
        }

        // 可以在这里保存阅读进度到 localStorage
        if (bookPath) {
            localStorage.setItem(`epub-location-${bookPath}`, epubcifi);
        }
    }, [bookPath, locationsReady]);

    // 加载保存的阅读进度
    useEffect(() => {
        if (bookPath) {
            const savedLocation = localStorage.getItem(`epub-location-${bookPath}`);
            if (savedLocation) {
                setLocation(savedLocation);
            }
        }
    }, [bookPath]);

    // 应用字体大小
    useEffect(() => {
        if (renditionRef.current) {
            renditionRef.current.themes.fontSize(`${fontSize}%`);
        }
    }, [fontSize]);

    // 获取 Rendition 引用并设置选择处理
    const handleRendition = useCallback((rendition: Rendition) => {
        renditionRef.current = rendition;

        // 设置初始字体大小
        rendition.themes.fontSize(`${fontSize}%`);

        // 设置主题样式
        rendition.themes.default({
            body: {
                fontFamily: '"Source Han Sans SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif',
                lineHeight: "1.8",
                color: "var(--foreground, #1a1a1a)",
                background: "var(--background, #ffffff)",
            },
            "a": {
                color: "var(--primary, #3b82f6)",
            },
        });

        // 监听文本选择
        rendition.on("selected", (_cfiRange: string, contents: Contents) => {
            const selection = contents.window.getSelection();
            if (selection) {
                const text = selection.toString().trim();
                if (text.length > 0) {
                    setSelectedText(text);
                    onTextSelect?.(text);
                }
            }
        });

        // 生成位置信息以便支持百分比跳转
        // @ts-ignore
        rendition.book.ready.then(() => {
            // @ts-ignore
            rendition.book.locations.generate(1000).then(() => {
                setLocationsReady(true);
                // 初始化当前进度
                try {
                    // @ts-ignore
                    const currentLocation = rendition.currentLocation();
                    if (currentLocation && (currentLocation as any).start) {
                        // @ts-ignore
                        const percentage = rendition.book.locations.percentageFromCfi((currentLocation as any).start.cfi);
                        setProgress(Math.round(percentage * 100));
                    }
                } catch (e) {
                    console.warn("Failed to init progress:", e);
                }
            });
        });

    }, [fontSize, onTextSelect]);

    // 处理进度条变更
    const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newProgress = parseInt(e.target.value);
        setProgress(newProgress);

        if (renditionRef.current && locationsReady) {
            try {
                // @ts-ignore
                const cfi = renditionRef.current.book.locations.cfiFromPercentage(newProgress / 100);
                if (cfi) {
                    renditionRef.current.display(cfi);
                }
            } catch (e) {
                console.error("Failed to seek:", e);
            }
        }
    };

    // 翻页
    const handlePrevPage = () => {
        renditionRef.current?.prev();
    };

    const handleNextPage = () => {
        renditionRef.current?.next();
    };

    // 跳转到目录项
    const handleTocClick = (href: string) => {
        renditionRef.current?.display(href);
        setShowToc(false);
    };

    // 调整字体大小
    const increaseFontSize = () => {
        setFontSize((prev) => Math.min(prev + 10, 200));
    };

    const decreaseFontSize = () => {
        setFontSize((prev) => Math.max(prev - 10, 50));
    };

    // 打开添加书签对话框
    const handleOpenAddBookmark = () => {
        // 获取当前选中的文本
        const selection = window.getSelection();
        const currentSelected = selection ? selection.toString().trim() : "";

        setBookmarkTitle(currentSelected || `书签 ${progress}%`);
        setBookmarkNote("");
        setBookmarkSelectedText(currentSelected);
        setIsAddBookmarkDialogOpen(true);
    };

    // 添加书签
    const handleAddBookmark = async () => {
        if (typeof location !== 'string') {
            console.error("Invalid location for bookmark");
            return;
        }

        try {
            await invoke("add_bookmark_cmd", {
                bookPath,
                bookType: "epub",
                title: bookmarkTitle,
                note: bookmarkNote || null,
                selectedText: bookmarkSelectedText || null,
                pageNumber: null,
                epubCfi: location, // 使用 CFI 位置
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
        if (bookmark.epub_cfi && renditionRef.current) {
            renditionRef.current.display(bookmark.epub_cfi);
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
                        {title || t("epubReader.untitled", "未命名书籍")}
                    </h2>
                </div>

                {/* 进度条滑块 */}
                <div className="flex-1 max-w-md flex items-center gap-2 mx-2">
                    <span className="text-xs text-muted-foreground w-8 text-right">{progress}%</span>
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={progress}
                        onChange={handleProgressChange}
                        onMouseDown={() => isSeeking.current = true}
                        onMouseUp={() => isSeeking.current = false}
                        disabled={!locationsReady}
                        className="flex-1 h-1.5 bg-muted rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary disabled:opacity-50"
                        style={{
                            backgroundSize: `${progress}% 100%`,
                            backgroundImage: `linear-gradient(var(--primary), var(--primary))`,
                            backgroundRepeat: 'no-repeat'
                        }}
                    />
                </div>

                <div className="flex items-center gap-2 shrink-0">
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
                            title={t("epubReader.decreaseFontSize", "减小字体")}
                        >
                            <Minus size={14} />
                        </Button>
                        <span className="text-xs text-muted-foreground w-8 text-center">
                            {fontSize}%
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={increaseFontSize}
                            className="h-7 w-7 p-0"
                            title={t("epubReader.increaseFontSize", "增大字体")}
                        >
                            <Plus size={14} />
                        </Button>
                    </div>

                    {/* 目录按钮 */}
                    <Button
                        variant={showToc ? "default" : "secondary"}
                        size="sm"
                        onClick={() => setShowToc(!showToc)}
                        className="gap-1"
                    >
                        <List size={16} />
                        <span className="hidden sm:inline">
                            {t("epubReader.tableOfContents", "目录")}
                        </span>
                    </Button>
                </div>
            </div>

            {/* 主内容区 */}
            <div className="flex-1 flex overflow-hidden relative">
                {/* EPUB 阅读区 */}
                <div className="flex-1 relative">
                    {/* 翻页按钮 - 左 */}
                    <button
                        onClick={handlePrevPage}
                        className="absolute left-2 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-background/80 border border-border shadow-sm hover:bg-muted transition-colors opacity-0 hover:opacity-100 focus:opacity-100"
                        title={t("epubReader.prevPage", "上一页")}
                    >
                        <ChevronLeft size={20} />
                    </button>

                    {/* EPUB 渲染区 */}
                    <div className="h-full">
                        <ReactReader
                            url={bookPath}
                            location={location}
                            locationChanged={handleLocationChange}
                            tocChanged={setToc}
                            getRendition={handleRendition}
                            epubOptions={{
                                allowScriptedContent: true,
                            }}
                        />
                    </div>

                    {/* 翻页按钮 - 右 */}
                    <button
                        onClick={handleNextPage}
                        className="absolute right-2 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-background/80 border border-border shadow-sm hover:bg-muted transition-colors opacity-0 hover:opacity-100 focus:opacity-100"
                        title={t("epubReader.nextPage", "下一页")}
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>

                {/* 目录侧边栏 */}
                {showToc && (
                    <div className="w-72 border-l border-border bg-card overflow-y-auto animate-in slide-in-from-right absolute right-0 top-0 bottom-0 h-full z-20 shadow-xl">
                        <div className="sticky top-0 bg-card border-b border-border p-3 flex items-center justify-between">
                            <h3 className="font-medium">
                                {t("epubReader.tableOfContents", "目录")}
                            </h3>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowToc(false)}
                                className="h-7 w-7 p-0"
                            >
                                <X size={16} />
                            </Button>
                        </div>
                        <div className="p-2">
                            {toc.map((item, index) => (
                                <TocItem
                                    key={index}
                                    item={item}
                                    onClick={handleTocClick}
                                />
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* 书签侧边栏 */}
            {bookPath && (
                <BookmarkSidebar
                    bookPath={bookPath}
                    bookType="epub"
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
                            将在当前位置（{progress}%）添加书签
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

// 目录项组件（支持嵌套）
interface TocItemProps {
    item: NavItem;
    onClick: (href: string) => void;
    level?: number;
}

function TocItem({ item, onClick, level = 0 }: TocItemProps) {
    return (
        <>
            <button
                onClick={() => onClick(item.href)}
                className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-muted transition-colors"
                style={{ paddingLeft: `${12 + level * 16}px` }}
            >
                <span className="line-clamp-1">{item.label}</span>
            </button>
            {item.subitems?.map((subitem, index) => (
                <TocItem
                    key={index}
                    item={subitem}
                    onClick={onClick}
                    level={level + 1}
                />
            ))}
        </>
    );
}
