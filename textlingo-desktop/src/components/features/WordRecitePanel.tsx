import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { FavoriteVocabulary } from "../../types";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";

interface WordRecitePanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  packId: string;
  packName: string;
  onReviewed: () => Promise<void> | void;
}

function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function WordRecitePanel({
  open,
  onOpenChange,
  packId,
  packName,
  onReviewed,
}: WordRecitePanelProps) {
  const [queue, setQueue] = useState<FavoriteVocabulary[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const current = useMemo(() => queue[currentIndex], [queue, currentIndex]);

  useEffect(() => {
    if (!open) return;
    setCurrentIndex(0);
    setShowAnswer(false);
    void loadQueue();
  }, [open, packId]);

  const loadQueue = async () => {
    setIsLoading(true);
    try {
      const today = formatLocalDate(new Date());
      const due = await invoke<FavoriteVocabulary[]>("get_due_vocabulary_queue_cmd", {
        packId,
        dateLocal: today,
      });
      setQueue(due);
    } catch (error) {
      console.error("Failed to load due queue:", error);
      setQueue([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGrade = async (grade: "unknown" | "uncertain" | "known") => {
    if (!current) return;
    setIsSubmitting(true);
    try {
      const today = formatLocalDate(new Date());
      await invoke<FavoriteVocabulary>("review_vocabulary_cmd", {
        vocabularyId: current.id,
        grade,
        dateLocal: today,
      });

      setQueue((prev) => prev.filter((item) => item.id !== current.id));
      setCurrentIndex(0);
      setShowAnswer(false);
      await onReviewed();
    } catch (error) {
      console.error("Failed to review vocabulary:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{packName} - 今日复习</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="py-12 text-center text-muted-foreground">加载复习队列中...</div>
        ) : !current ? (
          <div className="space-y-3 py-10 text-center">
            <div className="text-lg font-semibold">今日已完成</div>
            <div className="text-sm text-muted-foreground">当前没有到期卡片</div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              第 {currentIndex + 1} 张 / 共 {queue.length} 张
            </div>
            <div className="rounded-xl border border-border bg-card p-6">
              <div className="mb-3 text-2xl font-bold text-primary">{current.word}</div>
              {current.reading && <div className="mb-2 text-xs text-muted-foreground">{current.reading}</div>}

              {showAnswer ? (
                <div className="space-y-2 text-sm">
                  <div className="font-medium">{current.meaning}</div>
                  {current.usage && <div className="text-muted-foreground">{current.usage}</div>}
                  {current.example && <div className="italic text-muted-foreground">{current.example}</div>}
                  {current.explanation && <div className="text-muted-foreground">{current.explanation}</div>}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">先尝试回忆，再点击“显示答案”</div>
              )}
            </div>

            {!showAnswer ? (
              <Button className="w-full" onClick={() => setShowAnswer(true)}>
                显示答案
              </Button>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                <Button
                  variant="danger"
                  disabled={isSubmitting}
                  onClick={() => void handleGrade("unknown")}
                >
                  不认识
                </Button>
                <Button
                  variant="outline"
                  disabled={isSubmitting}
                  onClick={() => void handleGrade("uncertain")}
                >
                  模糊
                </Button>
                <Button disabled={isSubmitting} onClick={() => void handleGrade("known")}>
                  认识
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
