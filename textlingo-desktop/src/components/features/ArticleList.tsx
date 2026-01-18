import React, { useState } from "react";
import { FileText, Clock, Trash2, ExternalLink } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { formatDate, truncateText } from "../../lib/utils";

import { Article } from "../../types";

interface ArticleListProps {
  articles: Article[];
  isLoading: boolean;
  onSelectArticle: (article: Article) => void;
  onDelete: (id: string) => Promise<void>;
  selectedId?: string;
}

export function ArticleList({
  articles,
  isLoading,
  onSelectArticle,
  onDelete,
  selectedId,
}: ArticleListProps) {
  const { t } = useTranslation();
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  // 删除确认弹窗状态
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  // 点击删除按钮，显示确认弹窗
  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    console.log("Delete clicked for article:", id);
    e.stopPropagation();
    e.preventDefault();
    setPendingDeleteId(id);
    setShowDeleteConfirm(true);
  };

  // 确认删除后执行实际删除操作
  const executeDelete = async () => {
    if (!pendingDeleteId) return;

    console.log("Delete confirmed, proceeding...");
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

  // 取消删除
  const cancelDelete = () => {
    console.log("Delete cancelled");
    setShowDeleteConfirm(false);
    setPendingDeleteId(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
        <p className="text-lg font-medium mb-2">{t("articleList.noArticles")}</p>
        <p className="text-sm">{t("articleList.createFirst")}</p>
      </div>
    );
  }

  return (
    <>
      {/* 删除确认弹窗 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-card border border-border rounded-2xl p-6 max-w-md mx-4 shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-semibold text-foreground mb-3">
              {t("articleList.delete") || "Delete Article"}
            </h3>
            <p className="text-muted-foreground mb-4 leading-relaxed">
              {t("articleList.deleteConfirm") || "Are you sure you want to delete this article?"}
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="ghost"
                onClick={cancelDelete}
              >
                {t("articleReader.cancel") || "Cancel"}
              </Button>
              <Button
                onClick={executeDelete}
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
              >
                {t("articleList.delete") || "Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {articles.map((article) => (
          <div
            key={article.id}
            onClick={() => onSelectArticle(article)}
            className={`
              group p-4 rounded-lg border transition-all cursor-pointer
              ${selectedId === article.id
                ? "bg-primary/10 border-primary"
                : "bg-card border-border hover:border-primary/50 hover:bg-accent/50"
              }
            `}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-foreground truncate">
                  {article.title || t("articleList.untitled")}
                </h3>
                <p className="text-sm text-muted-foreground mt-1 flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {formatDate(article.created_at)}
                  </span>
                  {article.translated && (
                    <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">
                      {t("articleList.translated")}
                    </span>
                  )}
                </p>
                <p className="text-sm text-muted-foreground/80 mt-2 line-clamp-2">
                  {truncateText(article.content, 150)}
                </p>
              </div>

              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {article.source_url && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      window.open(article.source_url, "_blank");
                    }}
                    title={t("articleList.openSource")}
                  >
                    <ExternalLink size={14} />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => handleDeleteClick(e, article.id)}
                  disabled={isDeleting === article.id}
                  title={t("articleList.delete")}
                >
                  <Trash2 size={14} />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
