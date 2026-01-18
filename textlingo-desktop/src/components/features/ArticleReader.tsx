import React, { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import { Button } from "../ui/Button";
import { Textarea } from "../ui/Textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/Tabs";
import {
  BookOpen,
  Languages,
  Sparkles,
  Loader2,
  FileText,
  ChevronLeft,
  ChevronRight,
  Split,
  PanelRightOpen,
  PanelRightClose,
  Eye,
  EyeOff,
  Minus,
  Plus
} from "lucide-react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import { AnalysisType, AppConfig } from "../../lib/tauri";
import { Article, SegmentExplanation } from "../../types";
import { ArticleChatAssistant } from "./ArticleChatAssistant";
import { ArticleExplanationPanel } from "./ArticleExplanationPanel";
import { VideoSubtitlePlayer } from "./VideoSubtitlePlayer";

interface ArticleReaderProps {
  article: Article;
  onBack?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  hasNext?: boolean;
  hasPrev?: boolean;
  onUpdate?: () => void;
}

export function ArticleReader({
  article,
  onBack,
  onNext,
  onPrev,
  hasNext,
  hasPrev,
  onUpdate,
}: ArticleReaderProps) {
  const { t } = useTranslation();
  const [content, setContent] = useState(article.content);
  const [isEditing, setIsEditing] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isResegmenting, setIsResegmenting] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string>("");
  const [analysisType, setAnalysisType] = useState<AnalysisType>("summary");
  const [error, setError] = useState<string | null>(null);
  const [showAssistant, setShowAssistant] = useState(true);
  const [selectedText, setSelectedText] = useState<string>("");
  const [showTranslation, setShowTranslation] = useState(false);
  const [fontSize, setFontSize] = useState(18);

  // Segment Explorer State
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [isGeneratingExplanation, setIsGeneratingExplanation] = useState(false);
  const [activeTab, setActiveTab] = useState<"explanation" | "chat">("explanation");

  // Video Sync State
  const activeSegmentRef = useRef<HTMLElement>(null);

  // 本地段落状态 - 用于批量处理时的局部刷新
  const [localSegments, setLocalSegments] = useState(article.segments || []);

  // 字幕提取状态
  const [isExtractingSubtitles, setIsExtractingSubtitles] = useState(false);
  const [extractionProgress, setExtractionProgress] = useState<string | null>(null);

  // 成功提示消息状态
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 字幕提取进度事件监听
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;

    const setupListener = async () => {
      unlisten = await listen<{ phase: string; message: string; current?: number; total?: number; count?: number }>(
        `subtitle-extraction-progress://${article.id}`,
        (event) => {
          console.log("[ArticleReader] Progress event:", event.payload);
          const { phase, message, current, total, count } = event.payload;

          if (phase === "chunk" && current !== undefined && total !== undefined) {
            // 分片提取进度
            setExtractionProgress(t("subtitleExtraction.progress.chunk", { current, total }) || `分片提取中: ${current}/${total}`);
          } else if (phase === "audio") {
            setExtractionProgress(t("subtitleExtraction.progress.audio") || "提取音频中...");
          } else if (phase === "transcribe") {
            setExtractionProgress(t("subtitleExtraction.progress.transcribe") || "转录音频中...");
          } else if (phase === "merge") {
            setExtractionProgress(t("subtitleExtraction.progress.merge") || "合并排序去重中...");
          } else if (phase === "done") {
            setExtractionProgress(t("subtitleExtraction.success"));
            setSuccessMessage(t("subtitleExtraction.successMessage", { count: count || 0 }));

            // 3秒后自动刷新页面以显示新字幕
            setTimeout(() => {
              window.location.reload();
            }, 3000);
          } else if (phase === "start" || phase === "chunked") {
            setExtractionProgress(message);
          } else {
            setExtractionProgress(message);
          }
        }
      );
    };

    if (article.media_path) {
      setupListener();
    }

    return () => {
      if (unlisten) {
        unlisten();
      }
    };
  }, [article.id, article.media_path, t]);



  const ANALYSIS_TYPES: { value: AnalysisType; label: string; icon: React.ReactNode }[] = [
    { value: "summary", label: t("articleReader.summary") || "Summary", icon: <FileText size={16} /> },
    { value: "key_points", label: t("articleReader.keyPoints") || "Key Points", icon: <Sparkles size={16} /> },
    { value: "vocabulary", label: t("articleReader.vocabulary") || "Vocabulary", icon: <Languages size={16} /> },
    { value: "grammar", label: t("articleReader.grammar") || "Grammar", icon: <BookOpen size={16} /> },
    { value: "full", label: t("articleReader.fullAnalysis") || "Full Analysis", icon: <Sparkles size={16} /> },
  ];

  useEffect(() => {
    setContent(article.content);
    setAnalysisResult("");
    // 同步外部 article.segments 到本地状态
    setLocalSegments(article.segments || []);
  }, [article]);

  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection();
      if (selection && selection.toString().trim().length > 0) {
        setSelectedText(selection.toString().trim());
      }
    };
    document.addEventListener("mouseup", handleSelection);
    return () => document.removeEventListener("mouseup", handleSelection);
  }, []);

  // 自动滚动到激活的段落（非视频模式）
  useEffect(() => {
    if (selectedSegmentId && activeSegmentRef.current && !article.media_path) {
      activeSegmentRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [selectedSegmentId, article.media_path]);

  // 刷新文章数据
  const refreshArticle = async () => {
    try {
      console.log("[ArticleReader] Refreshing article data...");
      const freshArticle = await invoke<Article>("get_article", { id: article.id });
      if (freshArticle) {
        console.log("[ArticleReader] Article refreshed, segments:", freshArticle.segments?.length);
        setLocalSegments(freshArticle.segments || []);
        setContent(freshArticle.content);
        // 通知父组件更新，但也更新本地状态以确保响应速度
        onUpdate?.();
      }
    } catch (err) {
      console.error("[ArticleReader] Failed to refresh article:", err);
    }
  };

  const handleSaveContent = async () => {
    try {
      await invoke("update_article", {
        id: article.id,
        content,
      });
      setIsEditing(false);
      onUpdate?.();
    } catch (err) {
      setError(err as string);
    }
  };

  const handleTranslate = async () => {
    setIsTranslating(true);
    setError(null);
    try {
      const result = await invoke<Article>("translate_article", {
        articleId: article.id,
        targetLanguage: "zh-CN", // Default, could be from settings
      });
      console.log("[ArticleReader] Translation completed, result segments:", result.segments?.length);

      // 更新本地段落状态，使翻译立即渲染
      if (result.segments && result.segments.length > 0) {
        setLocalSegments(result.segments);
      }
      setContent(result.content);

      // 强制刷新一次以确保状态同步（尤其是VideoSubtitlePlayer）
      await refreshArticle();
    } catch (err) {
      setError(err as string);
    } finally {
      setIsTranslating(false);
    }
  };

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult("");
    try {
      const result = await invoke<string>("analyze_article", {
        articleId: article.id,
        analysisType,
      });
      setAnalysisResult(result);
    } catch (err) {
      setError(err as string);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 字幕提取处理函数
  const handleExtractSubtitles = async () => {
    if (!article.media_path) return;

    setIsExtractingSubtitles(true);
    setError(null);

    try {
      const updatedArticle = await invoke<Article>("extract_subtitles_cmd", {
        articleId: article.id,
      });

      // 更新本地状态
      if (updatedArticle.segments && updatedArticle.segments.length > 0) {
        console.log("[ArticleReader] Subtitles extracted, updating local state:", updatedArticle.segments.length);
        setLocalSegments(updatedArticle.segments);
        setContent(updatedArticle.content);

        // 显示成功提示
        const successMsg = t("subtitleExtraction.successMessage", { count: updatedArticle.segments.length })
          || `成功提取 ${updatedArticle.segments.length} 个字幕片段！`;
        setSuccessMessage(successMsg);

        // 3秒后自动隐藏成功提示
        setTimeout(() => {
          setSuccessMessage(null);
        }, 3000);
      }

      onUpdate?.();
    } catch (err) {
      console.error("[ArticleReader] Subtitle extraction failed:", err);
      setError(t("subtitleExtraction.error") + ": " + String(err));
    } finally {
      setIsExtractingSubtitles(false);
    }
  };

  const handleResegment = async () => {
    if (!confirm(t("articleReader.resegmentConfirm") || "This will replace existing segments. Continue?")) return;

    setIsResegmenting(true);
    try {
      // Temporarily save content if edited before resegmenting
      if (content !== article.content) {
        await invoke("update_article", { id: article.id, content });
      }

      await invoke("resegment_article", { articleId: article.id });
      onUpdate?.();
    } catch (err) {
      setError(err as string);
    } finally {
      setIsResegmenting(false);
    }
  };

  const selectedSegment = localSegments.find(s => s.id === selectedSegmentId) || null;

  const handleSegmentClick = (id: string) => {
    setSelectedSegmentId(id);
    setActiveTab("explanation");
    setShowAssistant(true);

    // Check if we need to auto-generate explanation
    const segment = localSegments.find(s => s.id === id);
    if (segment && !segment.explanation && !isGeneratingExplanation) {
      // Auto-trigger generation
      setTimeout(() => handleGenerateExplanation(id), 0);
    }
  };

  // Batch Translation State
  const [isBatchTranslating, setIsBatchTranslating] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });
  const [showBatchConfirm, setShowBatchConfirm] = useState(false);
  const [pendingBatchCount, setPendingBatchCount] = useState(0);

  // 启动批量分析 - 显示确认对话框
  const handleBatchTranslate = () => {
    console.log("[ArticleReader] handleBatchTranslate clicked!");
    console.log("[ArticleReader] localSegments:", localSegments);
    if (!localSegments || localSegments.length === 0) {
      console.warn("[ArticleReader] No segments, returning early");
      return;
    }

    // Filter segments that need explanation
    const segmentsToProcess = localSegments.filter(s => !s.explanation);
    console.log("[ArticleReader] Segments to process:", segmentsToProcess.length);

    if (segmentsToProcess.length === 0) {
      setError(t("articleReader.allSegmentsAnalyzed") || "All segments already have explanations.");
      return;
    }

    // 显示自定义确认对话框
    setPendingBatchCount(segmentsToProcess.length);
    setShowBatchConfirm(true);
  };

  // 确认后执行批量分析
  const executeBatchTranslate = async () => {
    setShowBatchConfirm(false);
    if (!localSegments || localSegments.length === 0) return;

    // 再次过滤，确保只处理未解析的段落
    const segmentsToProcess = localSegments.filter(s => !s.explanation);
    console.log("[ArticleReader] Starting batch translation for", segmentsToProcess.length, "segments");
    console.log("[ArticleReader] Already parsed:", localSegments.length - segmentsToProcess.length, "segments");

    if (segmentsToProcess.length === 0) {
      setError(t("articleReader.allSegmentsAnalyzed") || "All segments already have explanations.");
      return;
    }

    setIsBatchTranslating(true);
    setBatchProgress({ current: 0, total: segmentsToProcess.length });

    try {
      const appConfig = await invoke<AppConfig>("get_config");
      const targetLang = appConfig?.target_language || "zh-CN";
      const queue = [...segmentsToProcess];
      let completedCount = 0;

      // Worker function to process the queue
      const worker = async () => {
        while (queue.length > 0) {
          const segment = queue.shift();
          if (!segment) break;

          console.log(`[ArticleReader] Processing segment ${segment.id} (${segment.order}/${article.segments?.length})`);

          try {
            const explanation = await invoke<SegmentExplanation>("segment_translate_explain_cmd", {
              text: segment.text,
              targetLanguage: targetLang
            });

            if (explanation) {
              await invoke("update_article_segment", {
                articleId: article.id,
                segmentId: segment.id,
                explanation: explanation,
                reading: explanation.reading_text,
                translation: explanation.translation
              });

              console.log(`[ArticleReader] Segment ${segment.id} saved, updating local state`);

              // 更新本地状态而不是触发整个页面刷新
              setLocalSegments(prev => prev.map(s =>
                s.id === segment.id
                  ? { ...s, explanation, reading_text: explanation.reading_text, translation: explanation.translation }
                  : s
              ));
            }
          } catch (e) {
            console.error(`[ArticleReader] Failed to process segment ${segment.id}`, e);
            // Continue despite error
          } finally {
            completedCount++;
            setBatchProgress(prev => ({ ...prev, current: completedCount }));
          }
        }
      };

      // Run 3 workers concurrently
      await Promise.all([worker(), worker(), worker()]);

      console.log("[ArticleReader] Batch translation completed, syncing to parent");
      // 批量处理完成后，调用 refreshArticle 确保所有状态同步
      await refreshArticle();


    } catch (e) {
      console.error("Batch translation failed", e);
      setError("Batch translation interrupted.");
    } finally {
      setIsBatchTranslating(false);
    }
  };

  const handleGenerateExplanation = async (segmentId?: string) => {
    const targetId = segmentId || selectedSegmentId;
    if (!targetId || !article.id) return;

    setIsGeneratingExplanation(true);
    setError(null);

    // Find segment text
    const segment = localSegments.find(s => s.id === targetId);
    if (!segment) {
      setIsGeneratingExplanation(false);
      return;
    }

    try {
      console.log(`[ArticleReader] Generating explanation for segment ${targetId}...`);
      // Get config for target language
      const appConfig = await invoke<AppConfig>("get_config");
      const targetLang = appConfig?.target_language || "zh-CN";

      // Call local Rust command - Independent App Architecture
      console.log(`[ArticleReader] Invoking segment_translate_explain_cmd with targetLang: ${targetLang}`);
      const explanation = await invoke<SegmentExplanation>("segment_translate_explain_cmd", {
        text: segment.text,
        targetLanguage: targetLang
      });

      console.log(`[ArticleReader] Received explanation response:`, explanation ? "Success" : "Empty");

      if (explanation) {
        await invoke("update_article_segment", {
          articleId: article.id,
          segmentId: targetId,
          explanation: explanation,
          reading: explanation.reading_text,
          translation: explanation.translation
        });
        console.log(`[ArticleReader] Segment updated successfully`);

        // 更新本地状态
        setLocalSegments(prev => prev.map(s =>
          s.id === targetId
            ? { ...s, explanation, reading_text: explanation.reading_text, translation: explanation.translation }
            : s
        ));
      } else {
        throw new Error("No explanation returned from AI service");
      }

    } catch (e: any) {
      console.error("[ArticleReader] Failed to generate explanation", e);
      setError(typeof e === 'string' ? e : (e.message || "Failed to generate explanation. Check AI Model config."));
    } finally {
      setIsGeneratingExplanation(false);
    }
  };

  const hasSegments = localSegments && localSegments.length > 0;

  return (
    <div className="h-full flex overflow-hidden">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-background relative">
        {error && (
          <div className="absolute top-0 left-0 right-0 z-50 bg-destructive/90 border-b border-destructive text-destructive-foreground px-4 py-2 text-sm flex justify-between items-center backdrop-blur-md animate-in slide-in-from-top-full duration-300">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-white/80 hover:text-white">✕</button>
          </div>
        )}

        {/* 成功提示消息 */}
        {successMessage && (
          <div className="absolute top-0 left-0 right-0 z-50 bg-green-500/90 border-b border-green-600 text-white px-4 py-2 text-sm flex justify-between items-center backdrop-blur-md animate-in slide-in-from-top-full duration-300">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
              </svg>
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-white/80 hover:text-white">✕</button>
          </div>
        )}

        {/* Batch Translation Confirmation Dialog */}
        {showBatchConfirm && (
          <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center">
            <div className="bg-card border border-border rounded-2xl p-6 max-w-md mx-4 shadow-2xl animate-in zoom-in-95 duration-200">
              <h3 className="text-lg font-semibold text-foreground mb-3">
                {t("articleReader.analyzeAll") || "Analyze All Segments"}
              </h3>
              <p className="text-muted-foreground mb-4 leading-relaxed">
                {t("articleReader.analyzeAllConfirm", { count: pendingBatchCount }) ||
                  `This will analyze ${pendingBatchCount} segments. This might consume significant tokens. (Processing 3 at a time)`}
              </p>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="ghost"
                  onClick={() => setShowBatchConfirm(false)}
                >
                  {t("articleReader.cancel") || "Cancel"}
                </Button>
                <Button
                  onClick={executeBatchTranslate}
                  className="bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  {t("articleReader.analyze") || "Confirm"}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-card/50 backdrop-blur-sm supports-[backdrop-filter]:bg-card/50">
          <div className="flex items-center gap-4 min-w-0">
            {onBack && (
              <Button variant="ghost" size="sm" onClick={onBack}>
                <ChevronLeft size={18} />
              </Button>
            )}
            <div className="min-w-0 overflow-hidden">
              <h1 className="text-xl font-semibold text-foreground truncate">
                {article.title || t("articleReader.untitled")}
              </h1>
              {hasSegments && (
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex items-center gap-1.5 px-2 py-0.5 bg-muted rounded-md border border-border">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse"></div>
                    <span className="text-xs text-muted-foreground font-medium">
                      {localSegments.filter(s => s.explanation).length} / {localSegments.length}
                    </span>
                    <span className="text-xs text-muted-foreground/80 hidden sm:inline">Parsed</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {onPrev && (
              <Button variant="ghost" size="sm" onClick={onPrev} disabled={!hasPrev} title="Previous Article">
                <ChevronLeft size={18} />
              </Button>
            )}
            {onNext && (
              <Button variant="ghost" size="sm" onClick={onNext} disabled={!hasNext} title="Next Article">
                <ChevronRight size={18} />
              </Button>
            )}

            <div className="w-px h-4 bg-border mx-1" />

            {/* Font Size Control - Compact */}
            <div className="flex items-center gap-0.5 bg-muted/50 rounded-lg p-0.5 mr-2 border border-border">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFontSize(Math.max(12, fontSize - 2))}
                className="h-7 w-7 p-0 hover:bg-background text-foreground"
                title="Decrease font size"
              >
                <Minus size={14} />
              </Button>
              <span className="text-xs text-muted-foreground w-6 text-center">{fontSize}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFontSize(Math.min(32, fontSize + 2))}
                className="h-7 w-7 p-0 hover:bg-background text-foreground"
                title="Increase font size"
              >
                <Plus size={14} />
              </Button>
            </div>

            {hasSegments ? (
              <>
                <Button
                  variant={showTranslation ? "default" : "secondary"}
                  size="sm"
                  onClick={() => setShowTranslation(!showTranslation)}
                  title={showTranslation ? t("articleReader.hideTranslation") : t("articleReader.showTranslation")}
                  className="h-8 md:h-9"
                >
                  {showTranslation ? <EyeOff size={16} /> : <Eye size={16} />}
                  <span className="ml-2 hidden xl:inline">
                    {showTranslation ? t("articleReader.hideTranslation") : t("articleReader.showTranslation")}
                  </span>
                </Button>

                {isBatchTranslating ? (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-md border border-border h-8 md:h-9">
                    <Loader2 size={14} className="animate-spin text-primary" />
                    <span className="text-xs text-muted-foreground font-mono">
                      {Math.round((batchProgress.current / batchProgress.total) * 100)}%
                    </span>
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleBatchTranslate}
                    disabled={isBatchTranslating || !hasSegments}
                    title={t("articleReader.analyzeAll")}
                    className="h-8 md:h-9"
                  >
                    <Sparkles size={16} />
                    <span className="ml-2 hidden xl:inline">{t("articleReader.analyzeAll") || "Analyze All"}</span>
                  </Button>
                )}

                {/* Resegment Button moved here */}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleResegment}
                  disabled={isResegmenting}
                  className="h-8 md:h-9"
                  title={t("articleReader.resegment")}
                >
                  {isResegmenting ? <Loader2 size={16} className="animate-spin" /> : <Split size={16} />}
                  <span className="ml-2 hidden xl:inline">{t("articleReader.segment")}</span>
                </Button>
              </>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleResegment}
                disabled={isResegmenting}
                className="h-8 md:h-9"
              >
                {isResegmenting ? <Loader2 size={16} className="animate-spin" /> : <Split size={16} />}
                <span className="ml-2 hidden xl:inline">{t("articleReader.segment")}</span>
              </Button>
            )}

            <div className="w-px h-4 bg-border mx-1" />

            {/* Edit & Translate */}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsEditing(!isEditing)}
              className="h-8 md:h-9"
              title={t("articleReader.edit")}
            >
              <FileText size={16} />
              <span className="ml-2 hidden xl:inline">{isEditing ? t("articleReader.cancel") : t("articleReader.edit")}</span>
            </Button>

            <Button
              size="sm"
              onClick={handleTranslate}
              disabled={isTranslating}
              className="gap-2 h-8 md:h-9"
              title={t("articleReader.translate")}
              variant="secondary"
            >
              {isTranslating ? <Loader2 size={16} className="animate-spin" /> : <Languages size={16} />}
              <span className="hidden xl:inline">{t("articleReader.translate")}</span>
            </Button>

            <div className="w-px h-4 bg-border mx-1" />

            {/* Assistant Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAssistant(!showAssistant)}
              title={showAssistant ? "Hide Assistant" : "Show Assistant"}
              className="h-8 w-8 p-0"
            >
              {showAssistant ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
            </Button>
          </div>
        </div>

        {error && (
          <div className="mx-4 mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Reader Content */}
        <div className="flex-1 overflow-hidden relative">
          <Tabs defaultValue="content" className="h-full flex flex-col">
            {!hasSegments && ( // only show Content/Analysis tabs if in Markdown mode or maybe always?
              <div className="px-4 py-2 border-b border-border">
                <TabsList>
                  <TabsTrigger value="content">{t("articleReader.content") || "Content"}</TabsTrigger>
                  <TabsTrigger value="analysis">{t("articleReader.analysis") || "Local Analysis"}</TabsTrigger>
                </TabsList>
              </div>
            )}

            <TabsContent value="content" className="flex-1 overflow-hidden outline-none mt-0">
              {isEditing ? (
                <div className="h-full flex flex-col p-4">
                  <Textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="flex-1 font-mono text-sm resize-none bg-background text-foreground"
                  />
                  <div className="flex justify-end gap-2 mt-4">
                    <Button variant="secondary" onClick={() => setIsEditing(false)}>
                      {t("articleReader.cancel")}
                    </Button>
                    <Button onClick={handleSaveContent}>{t("articleReader.save")}</Button>
                  </div>
                </div>
              ) : (
                <div className="h-full overflow-y-auto px-4 py-6 md:px-8 lg:px-12 scroll-smooth">
                  {/* 视频模式：使用 VideoSubtitlePlayer 组件 */}
                  {article.media_path && (() => {
                    const filename = article.media_path.split('/').pop() || article.media_path.split('\\').pop() || '';
                    const videoUrl = `http://127.0.0.1:19420/video/${encodeURIComponent(filename)}`;
                    return (
                      <VideoSubtitlePlayer
                        videoUrl={videoUrl}
                        segments={localSegments}
                        selectedSegmentId={selectedSegmentId}
                        onSegmentClick={handleSegmentClick}
                        fontSize={fontSize}
                        showTranslation={showTranslation}
                        isExtractingSubtitles={isExtractingSubtitles}
                        onExtractSubtitles={handleExtractSubtitles}
                        articleTitle={article.title}
                        articleId={article.id}

                        extractionProgress={extractionProgress}
                        isTranslating={isTranslating}
                        onQuickTranslate={handleTranslate}
                      />
                    );
                  })()}

                  {/* 非视频模式：段落式显示 */}
                  {hasSegments && !article.media_path && (
                    <div className="max-w-3xl mx-auto pb-20">
                      {(() => {
                        const sortedSegments = [...localSegments].sort((a, b) => a.order - b.order);
                        const paragraphGroups: typeof sortedSegments[] = [];
                        let currentGroup: typeof sortedSegments = [];

                        sortedSegments.forEach((segment, index) => {
                          if (segment.is_new_paragraph || index === 0) {
                            if (currentGroup.length > 0) {
                              paragraphGroups.push(currentGroup);
                            }
                            currentGroup = [segment];
                          } else {
                            currentGroup.push(segment);
                          }
                        });

                        if (currentGroup.length > 0) {
                          paragraphGroups.push(currentGroup);
                        }

                        return paragraphGroups.map((group, groupIndex) => (
                          <div key={`group-${groupIndex}`} className="mb-6">
                            <div
                              className="text-foreground"
                              style={{ lineHeight: 2 }}
                            >
                              {group.map((segment, segIndex) => {
                                const isExplained = !!segment.explanation;
                                const hasTranslation = !!segment.translation && !isExplained;
                                const isSelected = segment.id === selectedSegmentId;

                                return (
                                  <React.Fragment key={segment.id}>
                                    <span
                                      ref={isSelected ? activeSegmentRef : null}
                                      onClick={() => handleSegmentClick(segment.id)}
                                      className={`inline decoration-clone rounded-lg border-2 px-1 py-0.5 mx-0.5 transition-all duration-200 cursor-pointer ${isSelected
                                        ? "bg-primary/20 border-primary shadow-sm text-foreground ring-2 ring-primary/20"
                                        : isExplained
                                          ? "hover:bg-accent border-green-500/30 hover:border-green-500/50 text-foreground"
                                          : hasTranslation
                                            ? "hover:bg-accent border-yellow-500/30 hover:border-yellow-500/50 text-foreground"
                                            : "hover:bg-accent border-transparent hover:border-border hover:text-foreground"
                                        }`}
                                      style={{
                                        fontSize: `${fontSize}px`,
                                        WebkitBoxDecorationBreak: 'clone',
                                        boxDecorationBreak: 'clone'
                                      }}
                                    >
                                      {segment.text}
                                    </span>
                                    {segIndex < group.length - 1 && " "}
                                  </React.Fragment>
                                );
                              })}
                            </div>

                            {group.map((segment) => {
                              const isSelected = segment.id === selectedSegmentId;
                              const hasTranslationContent = showTranslation && !!segment.translation;
                              const shouldShow = isSelected || hasTranslationContent;
                              const hasContent = segment.reading_text || hasTranslationContent;

                              if (!shouldShow || !hasContent) return null;

                              return (
                                <div key={`detail-${segment.id}`} className="mt-4 px-4 py-3 bg-muted/30 rounded-xl border border-border animate-in fade-in slide-in-from-top-2">
                                  {segment.reading_text && (
                                    <p
                                      className="text-muted-foreground leading-relaxed mb-2 font-mono"
                                      style={{ fontSize: `${fontSize * 0.85}px` }}
                                    >
                                      {segment.reading_text}
                                    </p>
                                  )}

                                  {showTranslation && segment.translation && (
                                    <div className="text-primary leading-relaxed">
                                      <p style={{ fontSize: `${fontSize * 0.95}px` }}>
                                        {segment.translation}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ));
                      })()}
                    </div>
                  )}

                  {/* 纯文本模式：Markdown 渲染 */}
                  {!hasSegments && !article.media_path && (
                    <article className="prose dark:prose-invert max-w-none pb-20 text-foreground">
                      <ReactMarkdown>{content}</ReactMarkdown>
                    </article>
                  )}
                </div>
              )}
            </TabsContent>

            <TabsContent value="analysis" className="flex-1 overflow-hidden p-4 mt-0">
              <div className="h-full flex flex-col max-w-4xl mx-auto w-full">
                <div className="flex items-center gap-4 mb-4 flex-wrap">
                  <div className="flex gap-2 flex-wrap">
                    {ANALYSIS_TYPES.map((type) => (
                      <Button
                        key={type.value}
                        variant={analysisType === type.value ? "default" : "secondary"}
                        size="sm"
                        onClick={() => setAnalysisType(type.value)}
                        className="gap-2"
                      >
                        {type.icon}
                        {type.label}
                      </Button>
                    ))}
                  </div>
                  <Button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing}
                    className="gap-2 ml-auto"
                  >
                    {isAnalyzing ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                    {t("articleReader.analyze")}
                  </Button>
                </div>
                {/* 
                  Result Display 
                  Using a simple div with whitespace-pre-wrap to show the result.
                */}
                <div className="flex-1 bg-muted/30 rounded-lg p-4 border border-border overflow-y-auto">
                  {isAnalyzing ? (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      <Loader2 className="animate-spin mr-2" />
                      {t("articleReader.analyzing")}
                    </div>
                  ) : analysisResult ? (
                    <div className="prose dark:prose-invert max-w-none">
                      <ReactMarkdown>{analysisResult}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      {t("articleReader.selectAnalysis")}
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Right Sidebar: Assistant / Explanation */}
      {
        showAssistant && (
          <div className="w-[350px] md:w-[400px] border-l border-border bg-card flex flex-col shrink-0 transition-all duration-300">
            <Tabs
              value={activeTab}
              onValueChange={(v) => setActiveTab(v as any)}
              className="flex-1 flex flex-col h-full overflow-hidden"
            >
              <div className="px-4 py-2 border-b border-border bg-card">
                <TabsList className="w-full">
                  <TabsTrigger value="explanation" className="flex-1">
                    {t("articleReader.explanation") || "Explanation"}
                  </TabsTrigger>
                  <TabsTrigger value="chat" className="flex-1">
                    {t("articleReader.chat") || "Chat"}
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="explanation" className="flex-1 overflow-hidden mt-0 relative">
                {selectedSegment ? (
                  <ArticleExplanationPanel
                    segment={selectedSegment}
                    explanation={selectedSegment.explanation || null}
                    isLoading={isGeneratingExplanation}
                    onRegenerate={handleGenerateExplanation}
                  />
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
                    <BookOpen size={48} className="mb-4 opacity-50" />
                    <p>{t("articleReader.selectSegment") || "Select a sentence to see explanation"}</p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="chat" className="flex-1 overflow-hidden mt-0">
                <ArticleChatAssistant
                  articleId={article.id}
                  articleTitle={article.title} // Use correct prop name
                  targetLanguage="zh-CN" // Use required prop
                  selectedText={selectedText || (selectedSegment ? selectedSegment.text : "")}
                />
              </TabsContent>
            </Tabs>
          </div>
        )
      }
    </div >
  );
}
