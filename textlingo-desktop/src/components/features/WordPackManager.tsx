import { Plus, Trash2, Play } from "lucide-react";
import type { WordPack } from "../../types";
import { Button } from "../ui/button";

interface WordPackManagerProps {
  packs: WordPack[];
  selectedPackId: string;
  vocabularyCountByPack: Map<string, number>;
  onSelectPack: (packId: string) => void;
  onCreatePack: () => void;
  onDeletePack: (pack: WordPack) => void;
  onStartReview: () => void;
}

export function WordPackManager({
  packs,
  selectedPackId,
  vocabularyCountByPack,
  onSelectPack,
  onCreatePack,
  onDeletePack,
  onStartReview,
}: WordPackManagerProps) {
  return (
    <div className="w-72 shrink-0 rounded-xl border border-border/50 bg-card p-3">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">单词合集</h3>
        <Button size="sm" variant="outline" onClick={onCreatePack}>
          <Plus size={14} className="mr-1" />
          新建
        </Button>
      </div>

      <div className="space-y-1">
        <button
          className={`flex w-full items-center justify-between rounded-md px-2 py-2 text-sm transition-colors ${
            selectedPackId === "all" ? "bg-primary/10 text-primary" : "hover:bg-muted/70"
          }`}
          onClick={() => onSelectPack("all")}
        >
          <span>全部单词</span>
          <span className="text-xs text-muted-foreground">
            {Array.from(vocabularyCountByPack.values()).reduce((acc, curr) => acc + curr, 0)}
          </span>
        </button>

        {packs.map((pack) => {
          const count = vocabularyCountByPack.get(pack.id) ?? 0;
          return (
            <div key={pack.id} className="group flex items-center gap-1">
              <button
                className={`flex-1 rounded-md px-2 py-2 text-left text-sm transition-colors ${
                  selectedPackId === pack.id ? "bg-primary/10 text-primary" : "hover:bg-muted/70"
                }`}
                onClick={() => onSelectPack(pack.id)}
              >
                <div className="truncate">{pack.name}</div>
                <div className="text-xs text-muted-foreground">{count} 词</div>
              </button>
              {!pack.is_system && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={() => onDeletePack(pack)}
                >
                  <Trash2 size={14} />
                </Button>
              )}
            </div>
          );
        })}
      </div>

      <Button className="mt-4 w-full" onClick={onStartReview}>
        <Play size={14} className="mr-2" />
        开始复习
      </Button>
    </div>
  );
}
