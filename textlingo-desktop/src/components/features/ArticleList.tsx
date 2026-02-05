import React, { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  FileText,
  Clock,
  Trash2,
  ExternalLink,
  Book,
  Video,
  FileType,
  Pencil,
  Eye,
  Plus,
  MoreVertical,
  Music
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/DropdownMenu";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { formatDate, truncateText } from "../../lib/utils";
import { Article } from "../../types";
import { Document, Page } from "react-pdf";
import ePub from "epubjs";
// 使用统一的 PDF.js worker 配置
import "../../lib/pdfConfig";



// EPUB 封面组件
function EpubCover({ url, title, className, typeIcon }: { url: string; title: string, className: string, typeIcon: React.ReactNode }) {
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  // const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const loadCover = async () => {
      try {
        const book = ePub(url);
        const cover = await book.coverUrl();
        if (mounted && cover) {
          setCoverUrl(cover);
        }
      } catch (err) {
        console.warn("Failed to load epub cover:", err);
      }
    };
    loadCover();
    return () => { mounted = false; };
  }, [url]);

  if (coverUrl) {
    return (
      <div className={`w-full h-full relative ${className}`}>
        <img src={coverUrl} alt={title} className="w-full h-full object-cover" />
      </div>
    );
  }

  // Fallback to styled cover
  return (
    <div className={`flex flex-col items-center justify-center w-full h-full relative ${className}`}>
      {/* 装饰性背景 */}
      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-black to-transparent dark:from-white" />

      <div className="relative z-10 p-4 flex flex-col items-center text-center max-w-[80%]">
        <div className="p-3 bg-white/50 dark:bg-black/20 backdrop-blur-md rounded-xl shadow-sm mb-2 group-hover:scale-110 transition-transform duration-300">
          {typeIcon}
        </div>
        <div className="text-[10px] text-foreground/50 leading-tight line-clamp-3 font-serif opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-2 w-full px-4">
          {title}
        </div>
        <span className="text-xs font-medium text-foreground/60 tracking-wider font-mono opacity-80 group-hover:opacity-0 transition-opacity">
          EPUB
        </span>
      </div>
    </div>
  );
}

interface ArticleListProps {
  articles: Article[];
  isLoading: boolean;
  onSelectArticle: (article: Article) => void;
  onDelete: (id: string) => Promise<void>;
  onEdit: (article: Article) => void;
  onNewMaterial?: () => void;
  selectedId?: string;
  viewMode: "list" | "card";
  onUpdate?: () => void;
}

export function ArticleList({
  articles,
  isLoading,
  onSelectArticle,
  onDelete,
  onEdit,
  onNewMaterial,
  selectedId,
  viewMode,
  onUpdate,
}: ArticleListProps) {
  const { t } = useTranslation();
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    e.preventDefault();
    setPendingDeleteId(id);
    setShowDeleteConfirm(true);
  };

  const executeDelete = async () => {
    if (!pendingDeleteId) return;
    setShowDeleteConfirm(false);
    setIsDeleting(pendingDeleteId);
    try {
      await onDelete(pendingDeleteId);
    } catch (err) {
      console.error("Failed to delete article:", err);
    } finally {
      setIsDeleting(null);
      setPendingDeleteId(null);
    }
  };

  const cancelDelete = () => {
    setShowDeleteConfirm(false);
    setPendingDeleteId(null);
  };

  const executeAction = async (action: string, articleId: string) => {
    try {
      if (action === "delete_subtitles") {
        await invoke("delete_article_subtitles_cmd", { id: articleId });
      } else if (action === "delete_analysis") {
        await invoke("delete_article_analysis_cmd", { id: articleId });
      }
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error(`Failed to execute ${action}:`, err);
    }
  };

  const AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'wma'];

  const getArticleType = (article: Article) => {
    if (article.book_path) {
      return article.book_type?.toUpperCase() || "BOOK";
    }
    if (article.media_path) {
      const ext = article.media_path.split('.').pop()?.toLowerCase() || '';
      if (AUDIO_EXTENSIONS.includes(ext)) {
        return "AUDIO";
      }
      return "VIDEO";
    }
    return "ARTICLE";
  };

  const getTypeIcon = (type: string, size: number = 20) => {
    switch (type) {
      case "EPUB":
      case "BOOK":
        return <Book className="text-primary" size={size} />;
      case "PDF":
        return <FileType className="text-primary" size={size} />;
      case "TXT":
        return <FileText className="text-primary" size={size} />;
      case "VIDEO":
        return <Video className="text-primary" size={size} />;
      case "AUDIO":
        return <Music className="text-primary" size={size} />;
      default:
        return <FileText className="text-primary" size={size} />;
    }
  };

  const getTypeLabelColor = () => {
    return "bg-primary/10 text-primary border-primary/20";
  };

  const getVideoUrl = (mediaPath: string) => {
    const filename = mediaPath.split(/[/\\]/).pop();
    if (filename) {
      return `http://127.0.0.1:19420/video/${encodeURIComponent(filename)}`;
    }
    return "";
  };

  const getBookUrl = (bookPath: string) => {
    // 本地文件服务
    if (bookPath.startsWith("http")) return bookPath;
    const filename = bookPath.split(/[/\\]/).pop();
    if (filename) {
      return `http://127.0.0.1:19420/book/${encodeURIComponent(filename)}`;
    }
    return bookPath;
  };

  const getCoverStyle = (type: string) => {
    switch (type) {
      case 'VIDEO': return 'bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/20';
      case 'AUDIO': return 'bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-900/20 dark:to-emerald-900/20';
      case 'PDF': return 'bg-gradient-to-br from-red-50 to-rose-100 dark:from-red-900/20 dark:to-rose-900/20';
      case 'EPUB':
      case 'BOOK': return 'bg-gradient-to-br from-orange-50 to-amber-100 dark:from-orange-900/20 dark:to-amber-900/20';
      default: return 'bg-gradient-to-br from-gray-50 to-slate-100 dark:from-gray-900/20 dark:to-slate-900/20';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  // If empty and no onNewMaterial passed, show empty state.
  // But since we want to show the "New Card" if viewMode is card, we might want to bypass this check 
  // ONLY if viewMode is card AND onNewMaterial is present.
  // However, the "No Articles" separate screen is nicer for empty states.
  // So I'll keep the empty check, but if viewMode is card, I'll allow rendering the "New Card" even if 0 articles?
  // Let's stick to existing behavior: if 0 articles, show the dedicated Empty State component (which is nicer).
  if (articles.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground flex flex-col items-center">
        <div className="w-16 h-16 bg-muted/50 rounded-full flex items-center justify-center mb-4">
          <Book className="h-8 w-8 opacity-50" />
        </div>
        <p className="text-lg font-medium mb-2">{t("articleList.noArticles")}</p>
        <p className="text-sm">{t("articleList.createFirst")}</p>
      </div>
    );
  }

  return (
    <>
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl p-6 max-w-sm w-full shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {t("articleList.delete") || "Delete Item"}
            </h3>
            <p className="text-sm text-muted-foreground mb-6">
              {t("articleList.deleteConfirm") || "Are you sure you want to delete this item? This action cannot be undone."}
            </p>
            <div className="flex gap-3 justify-end">
              <Button variant="ghost" size="sm" onClick={cancelDelete}>
                {t("articleReader.cancel") || "Cancel"}
              </Button>
              <Button
                size="sm"
                onClick={executeDelete}
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
              >
                {t("articleList.delete") || "Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className={viewMode === "card"
        ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-10"
        : "space-y-3 pb-10"
      }>
        {/* New Material Card (Only in Card View) */}
        {viewMode === "card" && onNewMaterial && (
          <div
            onClick={onNewMaterial}
            className="group relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border hover:border-primary/50 hover:bg-accent/50 cursor-pointer h-[280px] transition-all"
          >
            <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Plus size={24} />
            </div>
            <span className="font-medium text-muted-foreground group-hover:text-primary transition-colors">
              {t("header.newMaterial")}
            </span>
          </div>
        )}

        {articles.map((article) => {
          const type = getArticleType(article);
          const isSelected = selectedId === article.id;

          return viewMode === "card" ? (
            <div
              key={article.id}
              onClick={() => onSelectArticle(article)}
              className={`
                group relative flex flex-col rounded-xl border overflow-hidden transition-all cursor-pointer h-[280px]
                ${isSelected
                  ? "bg-primary/5 border-primary shadow-md ring-1 ring-primary"
                  : "bg-card border-border hover:border-primary/50 hover:bg-accent/50 hover:shadow-lg hover:-translate-y-1"
                }
              `}
            >
              {/* Cover Area */}
              <div className={`h-40 w-full shrink-0 relative overflow-hidden flex items-center justify-center ${getCoverStyle(type)}`}>

                {/* 1. Video Preview */}
                {type === 'VIDEO' && article.media_path ? (
                  <div className="w-full h-full relative">
                    <video
                      src={getVideoUrl(article.media_path)}
                      className="w-full h-full object-cover"
                      muted
                      loop
                      playsInline
                      onMouseEnter={e => e.currentTarget.play()}
                      onMouseLeave={e => {
                        e.currentTarget.pause();
                        e.currentTarget.currentTime = 0;
                      }}
                    />
                    <div className="absolute top-2 right-2 bg-black/50 backdrop-blur-sm text-white p-1 rounded-md">
                      <Video size={14} />
                    </div>
                  </div>
                ) : type === 'PDF' && article.book_path ? (
                  // 2. PDF Preview (Thumbnail)
                  <div className="w-full h-full relative overflow-hidden flex justify-center items-start pt-4 bg-gray-100 dark:bg-gray-800">
                    <div className="w-[120px] shadow-lg origin-top transition-transform group-hover:scale-105">
                      <Document
                        file={getBookUrl(article.book_path)}
                        loading={<div className="h-[160px] bg-white animate-pulse" />}
                        error={<div className="h-[160px] bg-white flex items-center justify-center text-xs text-red-500">Error</div>}
                      >
                        <Page
                          pageNumber={1}
                          width={120}
                          renderTextLayer={false}
                          renderAnnotationLayer={false}
                        />
                      </Document>
                    </div>
                    <div className="absolute top-2 right-2 bg-red-500/80 backdrop-blur-sm text-white px-1.5 py-0.5 rounded text-[10px] font-bold">
                      PDF
                    </div>
                  </div>
                ) : type === 'EPUB' && article.book_path ? (
                  // 3. EPUB Cover
                  <EpubCover
                    url={getBookUrl(article.book_path)}
                    title={article.title}
                    className={getCoverStyle(type)}
                    typeIcon={getTypeIcon(type, 28)}
                  />
                ) : type === 'AUDIO' && article.media_path ? (
                  // Audio Cover
                  <div className="flex flex-col items-center justify-center w-full h-full relative">
                    <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-green-500 to-transparent" />
                    <div className="relative z-10 flex flex-col items-center">
                      <div className="p-4 bg-green-500/20 backdrop-blur-md rounded-full shadow-sm mb-3 group-hover:scale-110 transition-transform duration-300">
                        <Music size={32} className="text-green-500" />
                      </div>
                      <span className="text-xs font-medium text-foreground/60 tracking-wider font-mono">AUDIO</span>
                    </div>
                  </div>
                ) : (
                  // Default / TXT Styled Cover
                  <div className="flex flex-col items-center justify-center w-full h-full relative">
                    {/* 装饰性背景 */}
                    <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-black to-transparent dark:from-white" />

                    <div className="relative z-10 p-4 flex flex-col items-center text-center max-w-[80%]">
                      <div className="p-3 bg-white/50 dark:bg-black/20 backdrop-blur-md rounded-xl shadow-sm mb-2 group-hover:scale-110 transition-transform duration-300">
                        {getTypeIcon(type, 28)}
                      </div>
                      {/* 如果是 TXT 或 EPUB，显示部分标题或内容作为装饰 */}
                      {(type === 'TXT' || type === 'EPUB' || type === "ARTICLE") && (
                        <div className="text-[10px] text-foreground/50 leading-tight line-clamp-3 font-serif opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-2 w-full px-4">
                          {truncateText(article.content || article.title, 60)}
                        </div>
                      )}
                      <span className="text-xs font-medium text-foreground/60 tracking-wider font-mono opacity-80 group-hover:opacity-0 transition-opacity">
                        {type}
                      </span>
                    </div>
                  </div>
                )}

                {/* Overlay Component */}
                <div className="absolute top-2 right-2 flex gap-1 z-20 opacity-0 group-hover:opacity-100 transition-opacity">
                  {/* Open Source URL */}
                  {!article.media_path && article.source_url && (
                    <Button
                      variant="secondary"
                      size="icon"
                      className="h-8 w-8 rounded-full shadow-sm bg-background/80 hover:bg-background"
                      title={t("articleList.openSource")}
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(article.source_url, "_blank");
                      }}
                    >
                      <ExternalLink size={14} />
                    </Button>
                  )}

                  {/* View Button */}
                  <Button
                    variant="secondary"
                    size="icon"
                    className="h-8 w-8 rounded-full shadow-sm bg-background/80 hover:bg-background"
                    title={t("common.view", "查看")}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectArticle(article);
                    }}
                  >
                    <Eye size={14} />
                  </Button>

                  {/* Edit Button */}
                  <Button
                    variant="secondary"
                    size="icon"
                    className="h-8 w-8 rounded-full shadow-sm bg-background/80 hover:bg-background"
                    title={t("common.edit", "编辑")}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(article);
                    }}
                  >
                    <Pencil size={14} />
                  </Button>

                  {/* More Menu (for VIDEO and AUDIO) */}
                  {(type === 'VIDEO' || type === 'AUDIO') && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="secondary"
                          size="icon"
                          className="h-8 w-8 rounded-full shadow-sm bg-background/80 hover:bg-background"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreVertical size={14} />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
                        <DropdownMenuItem onClick={() => onEdit(article)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          <span>{t("common.edit", "编辑信息")}</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => executeAction("delete_subtitles", article.id)}>
                          <span>{t("articleList.deleteSubtitles", "删除字幕")}</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => executeAction("delete_analysis", article.id)}>
                          <span>{t("articleList.deleteAnalysis", "删除翻译解析")}</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}

                  {/* Delete Button */}
                  <Button
                    variant="danger"
                    size="icon"
                    className="h-8 w-8 rounded-full shadow-sm opacity-90 hover:opacity-100"
                    title={t("articleList.delete")}
                    onClick={(e) => handleDeleteClick(e, article.id)}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>

              {/* Info Area */}
              <div className="flex-1 p-4 flex flex-col min-h-0 bg-card">
                <h3 className="font-semibold text-foreground text-base leading-snug line-clamp-2 mb-2 group-hover:text-primary transition-colors">
                  {article.title || t("articleList.untitled")}
                </h3>

                <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded border ${getTypeLabelColor()}`}>
                      {type}
                    </span>
                    {article.translated && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded border bg-green-500/10 text-green-600 border-green-200/50">
                        {t("articleList.translated")}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={12} />
                    <span>{formatDate(article.created_at).split(',')[0]}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            // List View
            <div
              key={article.id}
              onClick={() => onSelectArticle(article)}
              className={`
                group flex items-center gap-4 p-3 rounded-xl border transition-all cursor-pointer bg-card
                ${isSelected
                  ? "bg-primary/5 border-primary shadow-sm"
                  : "border-border hover:border-primary/50 hover:bg-accent/50 hover:shadow-sm"
                }
              `}
            >
              <div className={`
                  flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center
                  ${getCoverStyle(type)}
              `}>
                {getTypeIcon(type, 20)}
              </div>

              <div className="flex-1 min-w-0 grid grid-cols-12 gap-4 items-center">
                <div className="col-span-8 md:col-span-7">
                  <h3 className="font-medium text-sm text-foreground truncate group-hover:text-primary transition-colors">
                    {article.title || t("articleList.untitled")}
                  </h3>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${getTypeLabelColor()}`}>
                      {type}
                    </span>
                    {article.translated && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded border bg-green-500/10 text-green-600 border-green-200/50">
                        {t("articleList.translated")}
                      </span>
                    )}
                    <p className="text-xs text-muted-foreground truncate hidden md:block max-w-[200px]">
                      {truncateText(article.content, 40)}
                    </p>
                  </div>
                </div>

                <div className="col-span-4 md:col-span-3 text-xs text-muted-foreground flex items-end flex-col md:flex-row md:items-center gap-1">
                  <Clock size={12} />
                  {formatDate(article.created_at)}
                </div>

                <div className="col-span-0 md:col-span-2 flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {article.source_url && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      title={t("articleList.openSource")}
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(article.source_url, "_blank");
                      }}
                    >
                      <ExternalLink size={14} />
                    </Button>
                  )}

                  {/* View Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    title={t("common.view", "查看")}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectArticle(article);
                    }}
                  >
                    <Eye size={14} />
                  </Button>

                  {/* Edit Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    title={t("common.edit", "编辑")}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(article);
                    }}
                  >
                    <Pencil size={14} />
                  </Button>

                  {/* More Menu (for VIDEO and AUDIO) */}
                  {(type === 'VIDEO' || type === 'AUDIO') && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreVertical size={14} />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
                        <DropdownMenuItem onClick={() => onEdit(article)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          <span>{t("common.edit", "编辑信息")}</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => executeAction("delete_subtitles", article.id)}>
                          <span>{t("articleList.deleteSubtitles", "删除字幕")}</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => executeAction("delete_analysis", article.id)}>
                          <span>{t("articleList.deleteAnalysis", "删除翻译解析")}</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}

                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                    title={t("articleList.delete")}
                    onClick={(e) => handleDeleteClick(e, article.id)}
                    disabled={isDeleting === article.id}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
