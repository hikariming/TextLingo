/**
 * VideoSubtitlePlayer - 视频字幕播放器组件
 * 
 * 功能：
 * 1. 视频播放器（sticky 定位在顶部）
 * 2. 当前字幕显示（sticky 紧贴视频下方）
 * 3. 可折叠的完整字幕列表
 * 4. 迷你播放器模式（浮层显示，不隐藏主内容）
 * 5. SRT 字幕导出
 */

import React, { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "../ui/Button";
import { ChevronDown, ChevronUp, Loader2, FileText, Minimize2, Download, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ArticleSegment } from "../../types";

// 播放位置存储的 key 前缀
const PLAYBACK_POSITION_KEY_PREFIX = "textlingo_video_position_";

interface VideoSubtitlePlayerProps {
    /** 视频URL */
    videoUrl: string;
    /** 字幕段落数组 */
    segments: ArticleSegment[];
    /** 当前选中的段落ID */
    selectedSegmentId: string | null;
    /** 点击段落的回调 */
    onSegmentClick: (id: string) => void;
    /** 视频时间更新回调 (可选) */
    onTimeUpdate?: (time: number) => void;
    /** 字体大小 */
    fontSize: number;
    /** 是否显示翻译 */
    showTranslation: boolean;
    /** 是否正在提取字幕 */
    isExtractingSubtitles?: boolean;
    /** 提取字幕回调 */
    onExtractSubtitles?: () => void;
    /** 文章标题（用于导出文件名） */
    articleTitle?: string;
    /** 文章ID（用于记忆播放位置） */
    articleId?: string;
}

export function VideoSubtitlePlayer({
    videoUrl,
    segments,
    selectedSegmentId,
    onSegmentClick,
    onTimeUpdate,
    fontSize,
    showTranslation,
    isExtractingSubtitles = false,
    onExtractSubtitles,
    articleTitle = "subtitles",
    articleId,
}: VideoSubtitlePlayerProps) {
    const { t } = useTranslation();
    const videoRef = useRef<HTMLVideoElement>(null);
    const videoContainerRef = useRef<HTMLDivElement>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [showFullSubtitles, setShowFullSubtitles] = useState(false);
    const [isMiniMode, setIsMiniMode] = useState(false);
    const activeSegmentRef = useRef<HTMLDivElement>(null);
    const hasRestoredPosition = useRef(false);

    // 获取播放位置存储的 key
    const getStorageKey = useCallback(() => {
        return `${PLAYBACK_POSITION_KEY_PREFIX}${articleId || videoUrl}`;
    }, [articleId, videoUrl]);

    // 保存播放位置
    const savePlaybackPosition = useCallback((time: number) => {
        if (time > 0) {
            try {
                localStorage.setItem(getStorageKey(), time.toString());
            } catch (e) {
                console.warn("Failed to save playback position:", e);
            }
        }
    }, [getStorageKey]);

    // 恢复播放位置
    const restorePlaybackPosition = useCallback(() => {
        if (hasRestoredPosition.current) return;

        try {
            const savedTime = localStorage.getItem(getStorageKey());
            if (savedTime && videoRef.current) {
                const time = parseFloat(savedTime);
                if (!isNaN(time) && time > 0) {
                    videoRef.current.currentTime = time;
                    setCurrentTime(time);
                    hasRestoredPosition.current = true;
                }
            }
        } catch (e) {
            console.warn("Failed to restore playback position:", e);
        }
    }, [getStorageKey]);

    // 视频加载完成后恢复播放位置
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        const handleLoadedMetadata = () => {
            restorePlaybackPosition();
        };

        video.addEventListener("loadedmetadata", handleLoadedMetadata);

        // 如果视频已经加载，直接恢复
        if (video.readyState >= 1) {
            restorePlaybackPosition();
        }

        return () => {
            video.removeEventListener("loadedmetadata", handleLoadedMetadata);
        };
    }, [restorePlaybackPosition]);

    // 定期保存播放位置（每5秒）
    useEffect(() => {
        const interval = setInterval(() => {
            if (videoRef.current && !videoRef.current.paused) {
                savePlaybackPosition(videoRef.current.currentTime);
            }
        }, 5000);

        return () => clearInterval(interval);
    }, [savePlaybackPosition]);

    // 组件卸载时保存播放位置
    useEffect(() => {
        return () => {
            if (videoRef.current) {
                savePlaybackPosition(videoRef.current.currentTime);
            }
        };
    }, [savePlaybackPosition]);

    // 处理视频时间更新
    const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
        const time = e.currentTarget.currentTime;
        setCurrentTime(time);
        onTimeUpdate?.(time);
    };

    // 视频暂停时保存播放位置
    const handlePause = (e: React.SyntheticEvent<HTMLVideoElement>) => {
        savePlaybackPosition(e.currentTarget.currentTime);
    };

    // 辅助函数：格式化时间为 MM:SS
    const formatTime = (seconds?: number): string => {
        if (seconds === undefined || seconds === null) return "--:--";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    // 辅助函数：格式化时间为 SRT 格式 (HH:MM:SS,mmm)
    const formatSrtTime = (seconds?: number): string => {
        if (seconds === undefined || seconds === null) return "00:00:00,000";
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
    };

    // 导出 SRT 字幕
    const handleExportSrt = () => {
        const sortedSegs = [...segments].sort((a, b) => a.order - b.order);
        let srtContent = "";

        sortedSegs.forEach((seg, index) => {
            const startTime = formatSrtTime(seg.start_time);
            const endTime = formatSrtTime(seg.end_time);
            srtContent += `${index + 1}\n`;
            srtContent += `${startTime} --> ${endTime}\n`;
            srtContent += `${seg.text}\n`;
            if (showTranslation && seg.translation) {
                srtContent += `${seg.translation}\n`;
            }
            srtContent += "\n";
        });

        // 创建并下载文件
        const blob = new Blob([srtContent], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${articleTitle.replace(/[/\\?%*:|"<>]/g, "-")}.srt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // 找到当前时间对应的字幕
    const currentSubtitle = segments.find(
        s => s.start_time !== undefined && s.end_time !== undefined &&
            currentTime >= s.start_time && currentTime < s.end_time
    );

    // 点击字幕跳转视频
    const handleSubtitleClick = (segment: ArticleSegment) => {
        onSegmentClick(segment.id);
        if (videoRef.current && segment.start_time !== undefined) {
            videoRef.current.currentTime = segment.start_time;
            videoRef.current.play().catch(() => { });
        }
    };

    // 排序后的字幕列表
    const sortedSegments = [...segments].sort((a, b) => a.order - b.order);

    // 无字幕时显示提取按钮
    if (segments.length === 0) {
        return (
            <div className="max-w-3xl mx-auto">
                {/* 视频播放器 */}
                <div
                    ref={videoContainerRef}
                    className="rounded-lg overflow-hidden bg-black/5 border border-border shadow-lg mb-4"
                >
                    <video
                        ref={videoRef}
                        controls
                        playsInline
                        className="w-full aspect-video bg-black"
                        src={videoUrl}
                        onTimeUpdate={handleTimeUpdate}
                        onSeeked={handleTimeUpdate}
                        onPause={handlePause}
                        onError={(e) => {
                            console.error("Video playback error:", e);
                        }}
                    />
                </div>

                {/* 字幕提取提示 */}
                {onExtractSubtitles && (
                    <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex flex-col sm:flex-row items-start sm:items-center gap-3">
                        <div className="flex-1">
                            <p className="text-foreground font-medium">{t("subtitleExtraction.noSubtitles")}</p>
                            <p className="text-sm text-muted-foreground mt-1">{t("subtitleExtraction.geminiRequired")}</p>
                        </div>
                        <Button
                            onClick={onExtractSubtitles}
                            disabled={isExtractingSubtitles}
                            className="gap-2 shrink-0"
                        >
                            {isExtractingSubtitles ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    {t("subtitleExtraction.extracting")}
                                </>
                            ) : (
                                <>
                                    <FileText size={16} />
                                    {t("subtitleExtraction.extractButton")}
                                </>
                            )}
                        </Button>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto">
            {/* 迷你播放器浮层（不替换主内容，只是额外的浮层） */}
            {isMiniMode && (
                <div className="fixed bottom-4 right-4 z-50 w-80 bg-background rounded-xl border border-border shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4 duration-300">
                    {/* 迷你视频 */}
                    <div className="relative">
                        <video
                            ref={videoRef}
                            controls
                            playsInline
                            className="w-full aspect-video bg-black"
                            src={videoUrl}
                            onTimeUpdate={handleTimeUpdate}
                            onSeeked={handleTimeUpdate}
                            onPause={handlePause}
                        />
                        {/* 退出迷你模式按钮 */}
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setIsMiniMode(false)}
                            className="absolute top-2 right-2 h-7 w-7 p-0 bg-black/50 hover:bg-black/70 border-0"
                            title={t("videoPlayer.exitMiniMode")}
                        >
                            <X size={14} className="text-white" />
                        </Button>
                    </div>
                    {/* 迷你字幕 */}
                    {currentSubtitle && (
                        <div className="p-2 bg-card border-t border-border">
                            <p className="text-sm font-medium line-clamp-2">{currentSubtitle.text}</p>
                            {showTranslation && currentSubtitle.translation && (
                                <p className="text-xs text-blue-500 mt-1 line-clamp-1">{currentSubtitle.translation}</p>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* 正常视频区域（迷你模式时隐藏） */}
            {!isMiniMode && (
                <div className="sticky top-0 z-20 bg-background pb-2">
                    <div
                        ref={videoContainerRef}
                        className="rounded-lg overflow-hidden bg-black/5 border border-border shadow-lg relative"
                    >
                        <video
                            ref={videoRef}
                            controls
                            playsInline
                            className="w-full aspect-video bg-black"
                            src={videoUrl}
                            onTimeUpdate={handleTimeUpdate}
                            onSeeked={handleTimeUpdate}
                            onPause={handlePause}
                            onError={(e) => {
                                console.error("Video playback error:", e);
                            }}
                        />
                        {/* 迷你模式按钮 */}
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setIsMiniMode(true)}
                            className="absolute top-2 right-2 h-8 w-8 p-0 bg-black/50 hover:bg-black/70 border-0"
                            title={t("videoPlayer.miniMode")}
                        >
                            <Minimize2 size={16} className="text-white" />
                        </Button>
                    </div>
                </div>
            )}

            {/* 当前字幕卡片 - 始终显示 */}
            <div className={`${isMiniMode ? 'mt-0' : 'mt-3'} space-y-3`}>
                {currentSubtitle ? (
                    <>
                        {/* 原文区域 */}
                        <div
                            className="p-4 bg-card rounded-xl border-2 border-red-500/30 shadow-sm cursor-pointer hover:border-red-500/50 transition-colors"
                            onClick={() => handleSubtitleClick(currentSubtitle)}
                        >
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-medium text-red-500/80 uppercase tracking-wider">
                                    {t("videoPlayer.original")}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                    {formatTime(currentSubtitle.start_time)} - {formatTime(currentSubtitle.end_time)}
                                </span>
                            </div>
                            <p
                                className="text-foreground font-medium leading-relaxed"
                                style={{ fontSize: `${fontSize}px` }}
                            >
                                {currentSubtitle.text}
                            </p>
                            {/* 注音/读法 */}
                            {currentSubtitle.reading_text && (
                                <p
                                    className="text-muted-foreground mt-2 font-mono"
                                    style={{ fontSize: `${fontSize * 0.8}px` }}
                                >
                                    {currentSubtitle.reading_text}
                                </p>
                            )}
                        </div>

                        {/* 译文区域 */}
                        {showTranslation && currentSubtitle.translation && (
                            <div className="p-4 bg-blue-500/5 rounded-xl border-2 border-blue-500/30">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-xs font-medium text-blue-500/80 uppercase tracking-wider">
                                        {t("videoPlayer.translation")}
                                    </span>
                                </div>
                                <p
                                    className="text-blue-600 dark:text-blue-400 leading-relaxed"
                                    style={{ fontSize: `${fontSize * 0.95}px` }}
                                >
                                    {currentSubtitle.translation}
                                </p>
                            </div>
                        )}

                        {/* 如果没有译文，显示提示 */}
                        {!currentSubtitle.translation && !currentSubtitle.explanation && (
                            <div className="p-3 bg-muted/30 rounded-xl border border-border">
                                <p className="text-sm text-muted-foreground text-center">
                                    {t("videoPlayer.noTranslationYet")}
                                </p>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="p-4 bg-muted/30 rounded-xl border border-border text-center text-muted-foreground">
                        <p>{t("videoPlayer.playToShowSubtitle")}</p>
                    </div>
                )}
            </div>

            {/* 操作按钮行 */}
            <div className="mt-4 mb-2 flex gap-2 flex-wrap">
                {/* 展开/折叠字幕 */}
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setShowFullSubtitles(!showFullSubtitles)}
                    className="flex-1 justify-center gap-2"
                >
                    {showFullSubtitles ? (
                        <>
                            <ChevronUp size={16} />
                            {t("videoPlayer.hideSubtitles")}
                        </>
                    ) : (
                        <>
                            <ChevronDown size={16} />
                            {t("videoPlayer.showAllSubtitles")} ({segments.length})
                        </>
                    )}
                </Button>

                {/* 导出 SRT */}
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExportSrt}
                    className="gap-2 shrink-0"
                    title={t("videoPlayer.exportSrt")}
                >
                    <Download size={16} />
                    <span className="hidden sm:inline">{t("videoPlayer.exportSrt")}</span>
                </Button>

                {/* 重新提取字幕按钮 */}
                {onExtractSubtitles && (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onExtractSubtitles}
                        disabled={isExtractingSubtitles}
                        className="gap-2 shrink-0"
                        title={t("subtitleExtraction.reExtract")}
                    >
                        {isExtractingSubtitles ? (
                            <Loader2 size={16} className="animate-spin" />
                        ) : (
                            <FileText size={16} />
                        )}
                        <span className="hidden sm:inline">{t("subtitleExtraction.reExtract")}</span>
                    </Button>
                )}
            </div>

            {/* 完整字幕列表 - 可折叠 */}
            {showFullSubtitles && (
                <div className="bg-muted/20 rounded-xl border border-border overflow-hidden animate-in slide-in-from-top-2 duration-200">
                    <div className="max-h-[400px] overflow-y-auto divide-y divide-border">
                        {sortedSegments.map((segment) => {
                            const isActive = (() => {
                                if (segment.start_time === undefined || segment.end_time === undefined) return false;
                                return currentTime >= segment.start_time && currentTime < segment.end_time;
                            })();
                            const isExplained = !!segment.explanation;
                            const hasTranslation = !!segment.translation && !isExplained;
                            const isSelected = segment.id === selectedSegmentId;

                            return (
                                <div
                                    key={segment.id}
                                    ref={isActive ? activeSegmentRef : undefined}
                                    className={`p-3 cursor-pointer transition-colors ${isActive
                                        ? "bg-primary/10 border-l-4 border-l-primary"
                                        : isSelected
                                            ? "bg-accent/50"
                                            : "hover:bg-muted/50"
                                        }`}
                                    onClick={() => handleSubtitleClick(segment)}
                                >
                                    <div className="flex items-start gap-3">
                                        {/* 时间标签 */}
                                        <span className="text-xs text-muted-foreground font-mono whitespace-nowrap pt-0.5">
                                            {formatTime(segment.start_time)}
                                        </span>

                                        {/* 内容区域 */}
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-sm leading-relaxed ${isActive ? "text-foreground font-medium" : "text-foreground"}`}>
                                                {segment.text}
                                            </p>
                                            {showTranslation && segment.translation && (
                                                <p className="text-xs text-blue-500 mt-1 leading-relaxed">
                                                    {segment.translation}
                                                </p>
                                            )}
                                        </div>

                                        {/* 状态标记 */}
                                        <div className="flex items-center gap-1 shrink-0">
                                            {isExplained && (
                                                <span className="w-2 h-2 rounded-full bg-green-500" title="已解析" />
                                            )}
                                            {hasTranslation && (
                                                <span className="w-2 h-2 rounded-full bg-yellow-500" title="已翻译" />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
