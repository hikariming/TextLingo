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
import { ChevronDown, ChevronUp, Loader2, FileText, Minimize2, Download, X, FileJson, FileType, Music } from "lucide-react";
import { save } from "@tauri-apps/plugin-dialog";
import { invoke } from "@tauri-apps/api/core";
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuItem,
} from "../ui/DropdownMenu";
import { useTranslation } from "react-i18next";
import { ArticleSegment } from "../../types";

// 播放位置存储的 key 前缀
const PLAYBACK_POSITION_KEY_PREFIX = "textlingo_video_position_";

export type ViewMode = 'original' | 'bilingual' | 'translation';

interface VideoSubtitlePlayerProps {
    /** 媒体URL（视频或音频） */
    videoUrl: string;
    /** 字幕段落数组 */
    segments: ArticleSegment[];
    /** 当前选中的段落ID */
    selectedSegmentId: string | null;
    /** 点击段落的回调 */
    onSegmentClick: (id: string) => void;
    /** 时间更新回调 (可选) */
    onTimeUpdate?: (time: number) => void;
    /** 字体大小 */
    fontSize: number;
    /** 视图模式 */
    viewMode: ViewMode;
    /** 是否正在提取字幕 */
    isExtractingSubtitles?: boolean;
    /** 提取字幕回调 */
    onExtractSubtitles?: () => void;
    /** 文章标题（用于导出文件名） */
    articleTitle?: string;
    /** 文章ID（用于记忆播放位置） */
    articleId?: string;
    /** 提取进度消息 */
    extractionProgress?: string | null;
    /** 是否正在翻译 */
    isTranslating?: boolean;
    /** 快速翻译回调 */
    onQuickTranslate?: () => void;
    /** 翻译进度 */
    translationProgress?: { current: number; total: number } | null;
    /** 是否为音频模式 */
    isAudio?: boolean;
}

export function VideoSubtitlePlayer({
    videoUrl,
    segments,
    selectedSegmentId,
    onSegmentClick,
    onTimeUpdate,
    fontSize,
    viewMode,
    isExtractingSubtitles = false,
    onExtractSubtitles,
    articleTitle = "subtitles",
    articleId,
    extractionProgress,
    isTranslating = false,
    onQuickTranslate,
    translationProgress,
    isAudio = false,
}: VideoSubtitlePlayerProps) {
    const { t } = useTranslation();
    const videoRef = useRef<HTMLVideoElement & HTMLAudioElement>(null);
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

    // 处理媒体时间更新
    const handleTimeUpdate = (e: React.SyntheticEvent<HTMLMediaElement>) => {
        const time = e.currentTarget.currentTime;
        setCurrentTime(time);
        onTimeUpdate?.(time);
    };

    // 媒体暂停时保存播放位置
    const handlePause = (e: React.SyntheticEvent<HTMLMediaElement>) => {
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



    // 辅助函数：格式化时间为 VTT 格式 (HH:MM:SS.mmm)
    const formatVttTime = (seconds?: number): string => {
        if (seconds === undefined || seconds === null) return "00:00:00.000";
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
    };

    // 导出字幕通用函数
    const handleExport = async (format: 'srt' | 'vtt' | 'txt' | 'md' | 'json', mode: 'original' | 'translation' | 'bilingual' = 'original') => {
        const sortedSegs = [...segments].sort((a, b) => a.order - b.order);
        let content = "";
        let extension = format;

        // 如果是 JSON 格式，直接导出所有数据
        if (format === 'json') {
            content = JSON.stringify(sortedSegs.map(seg => ({
                start: seg.start_time,
                end: seg.end_time,
                text: seg.text,
                translation: seg.translation
            })), null, 2);
        } else {
            // 其他格式根据模式生成内容
            switch (format) {
                case 'srt':
                    extension = 'srt';
                    sortedSegs.forEach((seg, index) => {
                        const startTime = formatSrtTime(seg.start_time);
                        const endTime = formatSrtTime(seg.end_time);
                        content += `${index + 1}\n`;
                        content += `${startTime} --> ${endTime}\n`;

                        if (mode === 'translation') {
                            content += `${seg.translation || ''}\n`;
                        } else if (mode === 'bilingual') {
                            content += `${seg.text}\n`;
                            content += `${seg.translation || ''}\n`;
                        } else {
                            // original
                            content += `${seg.text}\n`;
                        }
                        content += "\n";
                    });
                    break;
                case 'vtt':
                    content = "WEBVTT\n\n";
                    sortedSegs.forEach((seg) => {
                        const startTime = formatVttTime(seg.start_time);
                        const endTime = formatVttTime(seg.end_time);
                        content += `${startTime} --> ${endTime}\n`;

                        if (mode === 'translation') {
                            content += `${seg.translation || ''}\n`;
                        } else if (mode === 'bilingual') {
                            content += `${seg.text}\n`;
                            if (seg.translation) {
                                content += `${seg.translation}\n`;
                            }
                        } else {
                            // original
                            content += `${seg.text}\n`;
                        }
                        content += "\n";
                    });
                    break;
                case 'txt':
                    sortedSegs.forEach((seg) => {
                        if (mode === 'translation') {
                            if (seg.translation) {
                                content += `${seg.translation}\n`;
                            }
                        } else if (mode === 'bilingual') {
                            content += `${seg.text}\n`;
                            if (seg.translation) {
                                content += `${seg.translation}\n`;
                            }
                        } else {
                            // original
                            content += `${seg.text}\n`;
                        }
                        content += "\n";
                    });
                    break;
                case 'md':
                    content += `# ${articleTitle}\n\n`;
                    sortedSegs.forEach((seg) => {
                        const startTime = formatTime(seg.start_time);

                        if (mode === 'translation') {
                            if (seg.translation) {
                                content += `**[${startTime}]** ${seg.translation}\n`;
                            }
                        } else if (mode === 'bilingual') {
                            content += `**[${startTime}]** ${seg.text}\n`;
                            if (seg.translation) {
                                content += `> ${seg.translation}\n`;
                            }
                        } else {
                            // original
                            content += `**[${startTime}]** ${seg.text}\n`;
                        }
                        content += "\n";
                    });
                    break;
            }
        }

        try {
            // 构建文件名： Title_[Mode].[Ext]
            let filenameMode = "";
            if (format !== 'json') {
                if (mode === 'translation') filenameMode = "_translated";
                else if (mode === 'bilingual') filenameMode = "_bilingual";
            }

            const defaultPath = `${articleTitle.replace(/[/\\?%*:|"<>]/g, "-")}${filenameMode}.${extension}`;
            const filePath = await save({
                defaultPath,
                filters: [{
                    name: format.toUpperCase(),
                    extensions: [extension]
                }]
            });

            if (filePath) {
                await invoke('write_text_file', { path: filePath, content });
            }
        } catch (error) {
            console.error('Failed to export:', error);
        }
    };

    // 找到当前时间对应的字幕
    const currentSubtitle = segments.find(
        s => s.start_time !== undefined && s.end_time !== undefined &&
            currentTime >= s.start_time && currentTime < s.end_time
    );

    // 检查是否有缺失的翻译
    const hasMissingTranslations = segments.some(s => !s.translation || !s.translation.trim());

    // 检查是否应该禁用翻译相关的导出选项
    // 我们总是允许导出，但在没有翻译时可能会导出空内容，这里不做强制禁用，而是依靠 hasMissingTranslations 给用户提示
    const checkAndExport = (format: 'srt' | 'vtt' | 'txt' | 'md', mode: 'original' | 'translation' | 'bilingual') => {
        if ((mode === 'translation' || mode === 'bilingual') && hasMissingTranslations) {
            // 可以在这里加一个确认弹窗，或者只是简单的 toast 提示
            // 目前需求是做二级菜单，并没有明确说要阻断
        }

        // 如果是翻译模式且有缺失，尝试触发快速翻译（可选，保留之前的逻辑）
        if ((mode === 'translation' || mode === 'bilingual') && hasMissingTranslations && onQuickTranslate && segments.every(s => !s.translation)) {
            // 如果完全没有翻译，则引导翻译
            onQuickTranslate();
            return;
        }

        handleExport(format, mode);
    };



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
                {/* 媒体播放器 */}
                <div
                    ref={videoContainerRef}
                    className="rounded-lg overflow-hidden bg-black/5 border border-border shadow-lg mb-4"
                >
                    {isAudio ? (
                        <div className="p-6 bg-gradient-to-br from-green-500/10 to-emerald-500/5 flex flex-col items-center gap-4">
                            <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center">
                                <Music size={36} className="text-green-500" />
                            </div>
                            <audio
                                ref={videoRef}
                                controls
                                preload="auto"
                                className="w-full"
                                src={videoUrl}
                                onTimeUpdate={handleTimeUpdate}
                                onSeeked={handleTimeUpdate}
                                onPause={handlePause}
                                onError={(e) => {
                                    console.error("Audio playback error:", e);
                                }}
                            />
                        </div>
                    ) : (
                        <video
                            ref={videoRef}
                            controls
                            playsInline
                            preload="auto"
                            className="w-full aspect-video bg-black"
                            src={videoUrl}
                            onTimeUpdate={handleTimeUpdate}
                            onSeeked={handleTimeUpdate}
                            onPause={handlePause}
                            onError={(e) => {
                                console.error("Video playback error:", e);
                            }}
                        />
                    )}
                </div>

                {/* 字幕提取提示 */}
                {onExtractSubtitles && (
                    <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex flex-col sm:flex-row items-start sm:items-center gap-3">
                        <div className="flex-1">
                            <p className="text-foreground font-medium">{t("subtitleExtraction.noSubtitles")}</p>
                            {isExtractingSubtitles ? (
                                <div className="mt-2 p-2 bg-background/50 rounded-md border border-yellow-500/20">
                                    <p className="text-sm text-yellow-600 animate-pulse font-mono">
                                        {extractionProgress || t("subtitleExtraction.extracting")}
                                    </p>
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground mt-1">{t("subtitleExtraction.geminiRequired")}</p>
                            )}
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
            {/* 迷你播放器浮层（仅视频模式） */}
            {!isAudio && isMiniMode && (
                <div className="fixed bottom-4 right-4 z-50 w-80 bg-background rounded-xl border border-border shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4 duration-300">
                    {/* 迷你视频 */}
                    <div className="relative">
                        <video
                            ref={videoRef}
                            controls
                            playsInline
                            preload="auto"
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
                            {viewMode === 'translation' && currentSubtitle.translation ? (
                                <p className="text-sm font-medium line-clamp-2">{currentSubtitle.translation}</p>
                            ) : (
                                <p className="text-sm font-medium line-clamp-2">{currentSubtitle.text}</p>
                            )}

                            {viewMode === 'bilingual' && currentSubtitle.translation && (
                                <p className="text-xs text-primary mt-1 line-clamp-1">{currentSubtitle.translation}</p>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* 正常媒体播放区域 */}
            {!(isMiniMode && !isAudio) && (
                <div className="sticky top-0 z-20 bg-background pb-2">
                    <div
                        ref={videoContainerRef}
                        className="rounded-lg overflow-hidden bg-black/5 border border-border shadow-lg relative"
                    >
                        {isAudio ? (
                            <div className="p-6 bg-gradient-to-br from-green-500/10 to-emerald-500/5 flex flex-col items-center gap-4">
                                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center">
                                    <Music size={28} className="text-green-500" />
                                </div>
                                <audio
                                    ref={videoRef}
                                    controls
                                    preload="auto"
                                    className="w-full"
                                    src={videoUrl}
                                    onTimeUpdate={handleTimeUpdate}
                                    onSeeked={handleTimeUpdate}
                                    onPause={handlePause}
                                    onError={(e) => {
                                        console.error("Audio playback error:", e);
                                    }}
                                />
                            </div>
                        ) : (
                            <>
                                <video
                                    ref={videoRef}
                                    controls
                                    playsInline
                                    preload="auto"
                                    className="w-full aspect-video bg-black"
                                    src={videoUrl}
                                    onTimeUpdate={handleTimeUpdate}
                                    onSeeked={handleTimeUpdate}
                                    onPause={handlePause}
                                    onError={(e) => {
                                        console.error("Video playback error:", e);
                                    }}
                                />
                                {/* 迷你模式按钮（仅视频） */}
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setIsMiniMode(true)}
                                    className="absolute top-2 right-2 h-8 w-8 p-0 bg-black/50 hover:bg-black/70 border-0"
                                    title={t("videoPlayer.miniMode")}
                                >
                                    <Minimize2 size={16} className="text-white" />
                                </Button>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* 当前字幕卡片 - 始终显示 */}
            <div className={`${isMiniMode ? 'mt-0' : 'mt-3'} space-y-3`}>
                {currentSubtitle ? (
                    <div
                        className="p-4 bg-card/60 backdrop-blur-sm rounded-xl border border-border shadow-sm cursor-pointer hover:bg-card/80 transition-all active:scale-[0.99]"
                        onClick={() => handleSubtitleClick(currentSubtitle)}
                    >
                        {/* 内容显示：根据视图模式调整 */}
                        {viewMode === 'translation' && currentSubtitle.translation ? (
                            <p
                                className="text-foreground font-medium leading-relaxed"
                                style={{ fontSize: `${fontSize}px` }}
                            >
                                {currentSubtitle.translation}
                            </p>
                        ) : (
                            <p
                                className="text-foreground font-medium leading-relaxed"
                                style={{ fontSize: `${fontSize}px` }}
                            >
                                {currentSubtitle.text}
                            </p>
                        )}

                        {/* 注音/读法 (非纯译文模式显示) */}
                        {viewMode !== 'translation' && currentSubtitle.reading_text && (
                            <p
                                className="text-muted-foreground mt-1.5 font-mono opacity-80"
                                style={{ fontSize: `${fontSize * 0.8}px` }}
                            >
                                {currentSubtitle.reading_text}
                            </p>
                        )}

                        {/* 译文 - 双语模式显示在下方 */}
                        {viewMode === 'bilingual' && currentSubtitle.translation && (
                            <div className="mt-3 pt-3 border-t border-border/40">
                                <p
                                    className="text-primary/90 leading-relaxed font-medium"
                                    style={{ fontSize: `${fontSize * 0.95}px` }}
                                >
                                    {currentSubtitle.translation}
                                </p>
                            </div>
                        )}

                        {/* 如果没有译文，也不显示提示 */}
                    </div>
                ) : (
                    <div className="p-4 bg-muted/30 rounded-xl border border-border text-center text-muted-foreground">
                        <p>{t("videoPlayer.playToShowSubtitle")}</p>
                    </div>
                )}
            </div>

            {/* 操作按钮行 */}
            <div className="mt-4 mb-2 space-y-2">
                <div className="flex gap-2 flex-wrap">
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

                    {/* 导出菜单 */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                className="gap-2 shrink-0"
                                disabled={isTranslating}
                            >
                                {isTranslating ? (
                                    <Loader2 size={16} className="animate-spin" />
                                ) : (
                                    <Download size={16} />
                                )}
                                <span className="hidden sm:inline">
                                    {isTranslating ? (
                                        translationProgress && translationProgress.total > 0 ?
                                            `${t("articleReader.translating") || "翻译中..."} ${Math.round((translationProgress.current / translationProgress.total) * 100)}%`
                                            : (t("articleReader.translating") || "翻译中...")
                                    ) : (t("videoPlayer.exportSubtitles") || "导出字幕")}
                                </span>
                                <ChevronDown size={14} className="opacity-50" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            {/* SRT Export Submenu */}
                            <DropdownMenu>
                                <DropdownMenuTrigger className="flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[state=open]:bg-accent data-[state=open]:text-accent-foreground w-full">
                                    <FileText className="mr-2 h-4 w-4" />
                                    <span className="flex-1 text-left">SRT (.srt)</span>
                                    <ChevronDown className="ml-2 h-4 w-4 -rotate-90" />
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="ml-1">
                                    <DropdownMenuItem onClick={() => checkAndExport('srt', 'original')}>
                                        <span>{t("videoPlayer.exportOptions.original")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('srt', 'translation')}>
                                        <span>{t("videoPlayer.exportOptions.translation")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('srt', 'bilingual')}>
                                        <span>{t("videoPlayer.exportOptions.bilingual")}</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>

                            {/* VTT Export Submenu */}
                            <DropdownMenu>
                                <DropdownMenuTrigger className="flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[state=open]:bg-accent data-[state=open]:text-accent-foreground w-full">
                                    <FileText className="mr-2 h-4 w-4" />
                                    <span className="flex-1 text-left">VTT (.vtt)</span>
                                    <ChevronDown className="ml-2 h-4 w-4 -rotate-90" />
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="ml-1">
                                    <DropdownMenuItem onClick={() => checkAndExport('vtt', 'original')}>
                                        <span>{t("videoPlayer.exportOptions.original")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('vtt', 'translation')}>
                                        <span>{t("videoPlayer.exportOptions.translation")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('vtt', 'bilingual')}>
                                        <span>{t("videoPlayer.exportOptions.bilingual")}</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>

                            {/* Text Export Submenu */}
                            <DropdownMenu>
                                <DropdownMenuTrigger className="flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[state=open]:bg-accent data-[state=open]:text-accent-foreground w-full">
                                    <FileType className="mr-2 h-4 w-4" />
                                    <span className="flex-1 text-left">Text (.txt)</span>
                                    <ChevronDown className="ml-2 h-4 w-4 -rotate-90" />
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="ml-1">
                                    <DropdownMenuItem onClick={() => checkAndExport('txt', 'original')}>
                                        <span>{t("videoPlayer.exportOptions.original")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('txt', 'translation')}>
                                        <span>{t("videoPlayer.exportOptions.translation")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('txt', 'bilingual')}>
                                        <span>{t("videoPlayer.exportOptions.bilingual")}</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>

                            {/* Markdown Export Submenu */}
                            <DropdownMenu>
                                <DropdownMenuTrigger className="flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[state=open]:bg-accent data-[state=open]:text-accent-foreground w-full">
                                    <FileType className="mr-2 h-4 w-4" />
                                    <span className="flex-1 text-left">Markdown (.md)</span>
                                    <ChevronDown className="ml-2 h-4 w-4 -rotate-90" />
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="ml-1">
                                    <DropdownMenuItem onClick={() => checkAndExport('md', 'original')}>
                                        <span>{t("videoPlayer.exportOptions.original")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('md', 'translation')}>
                                        <span>{t("videoPlayer.exportOptions.translation")}</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => checkAndExport('md', 'bilingual')}>
                                        <span>{t("videoPlayer.exportOptions.bilingual")}</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>

                            <DropdownMenuItem onClick={() => handleExport('json')}>
                                <FileJson className="mr-2 h-4 w-4" />
                                <span>JSON (.json)</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>

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

                {/* 重新提取时的日志显示 */}
                {isExtractingSubtitles && onExtractSubtitles && (
                    <div className="p-2 bg-background/50 rounded-md border border-yellow-500/20">
                        <p className="text-sm text-yellow-600 animate-pulse font-mono">
                            {extractionProgress || t("subtitleExtraction.extracting")}
                        </p>
                    </div>
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
                                            {viewMode === 'translation' && segment.translation ? (
                                                <p className={`text-sm leading-relaxed ${isActive ? "text-foreground font-medium" : "text-foreground"}`}>
                                                    {segment.translation}
                                                </p>
                                            ) : (
                                                <p className={`text-sm leading-relaxed ${isActive ? "text-foreground font-medium" : "text-foreground"}`}>
                                                    {segment.text}
                                                </p>
                                            )}

                                            {viewMode === 'bilingual' && segment.translation && (
                                                <p className="text-xs text-primary mt-1 leading-relaxed">
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
