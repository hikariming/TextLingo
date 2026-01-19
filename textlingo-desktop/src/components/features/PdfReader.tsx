/**
 * PDF 阅读器组件
 * 使用 react-pdf 库渲染 PDF 文件
 * 支持清晰显示、文本选择联动、翻页、进度跳转、缩放
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { Document, Page } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
// 使用统一的 PDF.js worker 配置
import "../../lib/pdfConfig";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import {
    ChevronLeft,
    ChevronRight,
    Loader2,
    AlertCircle,
    Maximize2,
    Minimize2,
    RotateCcw,
    Minus,
    Plus,
} from "lucide-react";



interface PdfReaderProps {
    /** PDF 文件的 URL */
    bookPath: string;
    /** 书籍标题 */
    title?: string;
    /** 选中文本时的回调 */
    onTextSelect?: (text: string) => void;
    /** 返回按钮回调 */
    onBack?: () => void;
}

export function PdfReader({
    bookPath,
    title,
    onTextSelect,
    onBack,
}: PdfReaderProps) {
    const { t } = useTranslation();
    const containerRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    // PDF 状态
    const [numPages, setNumPages] = useState<number>(0);
    const [pageNumber, setPageNumber] = useState<number>(1);

    // 加载状态
    const [isLoading, setIsLoading] = useState(true);
    // 错误信息
    const [error, setError] = useState<string | null>(null);
    // 全屏模式
    const [isFullscreen, setIsFullscreen] = useState(false);
    // 缩放比例 (百分比)
    const [scale, setScale] = useState(100);

    // PDF 加载成功回调
    const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
        setIsLoading(false);
        setError(null);

        // 恢复上次阅读进度
        if (bookPath) {
            const savedPage = localStorage.getItem(`pdf-page-${bookPath}`);
            if (savedPage) {
                const parsed = parseInt(savedPage);
                if (parsed > 0 && parsed <= numPages) {
                    setPageNumber(parsed);
                }
            }
        }
    }, [bookPath]);

    // PDF 加载失败回调
    const onDocumentLoadError = useCallback((err: Error) => {
        console.error("PDF load error:", err);
        setIsLoading(false);
        setError(t("pdfReader.loadError", "PDF加载失败"));
    }, [t]);

    // 处理文本选择
    const handleTextSelection = useCallback(() => {
        const selection = window.getSelection();
        if (selection) {
            const text = selection.toString().trim();
            if (text.length > 0) {
                onTextSelect?.(text);
            }
        }
    }, [onTextSelect]);

    // 翻页
    const goToPrevPage = useCallback(() => {
        setPageNumber((prev) => Math.max(prev - 1, 1));
    }, []);

    const goToNextPage = useCallback(() => {
        setPageNumber((prev) => Math.min(prev + 1, numPages));
    }, [numPages]);

    // 进度条变化
    const handleProgressChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const newPage = parseInt(e.target.value);
        setPageNumber(newPage);
    }, []);

    // 缩放控制
    const zoomIn = useCallback(() => {
        setScale((prev) => Math.min(prev + 20, 300));
    }, []);

    const zoomOut = useCallback(() => {
        setScale((prev) => Math.max(prev - 20, 50));
    }, []);

    // 全屏切换
    const toggleFullscreen = useCallback(() => {
        if (!document.fullscreenElement) {
            containerRef.current?.requestFullscreen();
            setIsFullscreen(true);
        } else {
            document.exitFullscreen();
            setIsFullscreen(false);
        }
    }, []);

    // 刷新 PDF
    const handleRefresh = useCallback(() => {
        setIsLoading(true);
        setError(null);
        // 强制重新加载 - 通过临时清空再恢复来触发
        setPageNumber(1);
    }, []);

    // 监听全屏状态变化
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };

        document.addEventListener("fullscreenchange", handleFullscreenChange);
        return () => {
            document.removeEventListener("fullscreenchange", handleFullscreenChange);
        };
    }, []);

    // 保存阅读进度
    useEffect(() => {
        if (bookPath && pageNumber > 0) {
            localStorage.setItem(`pdf-page-${bookPath}`, pageNumber.toString());
        }
    }, [bookPath, pageNumber]);

    // 键盘快捷键
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement) return;

            switch (e.key) {
                case "ArrowLeft":
                case "ArrowUp":
                    goToPrevPage();
                    break;
                case "ArrowRight":
                case "ArrowDown":
                case " ":
                    goToNextPage();
                    break;
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [goToPrevPage, goToNextPage]);

    // 计算页面宽度
    const getPageWidth = useCallback(() => {
        if (contentRef.current) {
            const containerWidth = contentRef.current.clientWidth - 48; // 减去 padding
            return Math.min(containerWidth, 800) * (scale / 100);
        }
        return 600 * (scale / 100);
    }, [scale]);

    return (
        <div
            ref={containerRef}
            className="h-full flex flex-col bg-background"
        >
            {/* 工具栏 */}
            <div className="flex items-center justify-between p-3 border-b border-border bg-card/50 backdrop-blur-sm gap-4 shrink-0">
                <div className="flex items-center gap-2 shrink-0">
                    {onBack && (
                        <Button variant="ghost" size="sm" onClick={onBack}>
                            <ChevronLeft size={18} />
                        </Button>
                    )}
                    <h2 className="text-sm font-medium truncate max-w-[150px]">
                        {title || t("pdfReader.untitled", "未命名PDF")}
                    </h2>
                </div>

                {/* 进度条滑块 */}
                {numPages > 0 && (
                    <div className="flex-1 max-w-md flex items-center gap-2 mx-2">
                        <span className="text-xs text-muted-foreground w-12 text-right">
                            {pageNumber}/{numPages}
                        </span>
                        <input
                            type="range"
                            min="1"
                            max={numPages}
                            value={pageNumber}
                            onChange={handleProgressChange}
                            className="flex-1 h-1.5 bg-muted rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                            style={{
                                backgroundSize: `${((pageNumber - 1) / (numPages - 1)) * 100}% 100%`,
                                backgroundImage: `linear-gradient(var(--primary), var(--primary))`,
                                backgroundRepeat: 'no-repeat'
                            }}
                        />
                    </div>
                )}

                <div className="flex items-center gap-2 shrink-0">
                    {/* 缩放控制 */}
                    <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1 border border-border">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={zoomOut}
                            className="h-7 w-7 p-0"
                            title={t("pdfReader.zoomOut", "缩小")}
                        >
                            <Minus size={14} />
                        </Button>
                        <span className="text-xs text-muted-foreground w-10 text-center">
                            {scale}%
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={zoomIn}
                            className="h-7 w-7 p-0"
                            title={t("pdfReader.zoomIn", "放大")}
                        >
                            <Plus size={14} />
                        </Button>
                    </div>

                    {/* 刷新按钮 */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isLoading}
                        className="h-8 w-8 p-0"
                        title={t("pdfReader.refresh", "刷新")}
                    >
                        <RotateCcw size={16} />
                    </Button>

                    {/* 全屏按钮 */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={toggleFullscreen}
                        className="h-8 w-8 p-0"
                        title={isFullscreen
                            ? t("pdfReader.exitFullscreen", "退出全屏")
                            : t("pdfReader.fullscreen", "全屏")
                        }
                    >
                        {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </Button>
                </div>
            </div>

            {/* PDF 内容区域 */}
            <div
                ref={contentRef}
                className="flex-1 relative overflow-auto flex flex-col items-center"
                onMouseUp={handleTextSelection}
            >
                {/* 翻页按钮 - 左 */}
                <button
                    onClick={goToPrevPage}
                    disabled={pageNumber <= 1}
                    className="fixed left-4 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-background/80 border border-border shadow-sm hover:bg-muted transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    title={t("pdfReader.prevPage", "上一页")}
                >
                    <ChevronLeft size={20} />
                </button>

                {/* 加载状态 */}
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-background z-10">
                        <div className="flex flex-col items-center gap-3 text-muted-foreground">
                            <Loader2 size={32} className="animate-spin" />
                            <span>{t("pdfReader.loading", "加载中...")}</span>
                        </div>
                    </div>
                )}

                {/* 错误状态 */}
                {error && (
                    <div className="absolute inset-0 flex items-center justify-center bg-background z-10">
                        <div className="flex flex-col items-center gap-3 text-destructive">
                            <AlertCircle size={32} />
                            <span>{error}</span>
                            <Button variant="outline" size="sm" onClick={handleRefresh}>
                                {t("pdfReader.retry", "重试")}
                            </Button>
                        </div>
                    </div>
                )}

                {/* PDF 渲染 */}
                <div className="py-6">
                    <Document
                        file={bookPath}
                        onLoadSuccess={onDocumentLoadSuccess}
                        onLoadError={onDocumentLoadError}
                        loading={null}
                        className="flex flex-col items-center"
                    >
                        <Page
                            pageNumber={pageNumber}
                            width={getPageWidth()}
                            renderTextLayer={true}
                            renderAnnotationLayer={true}
                            className="shadow-lg"
                        />
                    </Document>
                </div>

                {/* 翻页按钮 - 右 */}
                <button
                    onClick={goToNextPage}
                    disabled={pageNumber >= numPages}
                    className="fixed right-4 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-background/80 border border-border shadow-sm hover:bg-muted transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    title={t("pdfReader.nextPage", "下一页")}
                >
                    <ChevronRight size={20} />
                </button>
            </div>
        </div>
    );
}
