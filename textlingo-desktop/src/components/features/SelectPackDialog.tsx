import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { WordPack } from "../../types";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Input } from "../ui/input";

interface SelectPackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (packIds: string[]) => Promise<void> | void;
  initialSelectedPackIds?: string[];
}

export function SelectPackDialog({
  open,
  onOpenChange,
  onConfirm,
  initialSelectedPackIds,
}: SelectPackDialogProps) {
  const [packs, setPacks] = useState<WordPack[]>([]);
  const [selectedPackIds, setSelectedPackIds] = useState<Set<string>>(new Set());
  const [newPackName, setNewPackName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const defaultPackId = useMemo(
    () => packs.find((pack) => pack.is_system)?.id ?? packs[0]?.id,
    [packs]
  );

  useEffect(() => {
    if (!open) return;
    void loadPacks();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (initialSelectedPackIds && initialSelectedPackIds.length > 0) {
      setSelectedPackIds(new Set(initialSelectedPackIds));
      return;
    }
    if (defaultPackId) {
      setSelectedPackIds(new Set([defaultPackId]));
    }
  }, [open, initialSelectedPackIds, defaultPackId]);

  const loadPacks = async () => {
    setIsLoading(true);
    try {
      const list = await invoke<WordPack[]>("list_word_packs_cmd");
      setPacks(list);
    } catch (error) {
      console.error("Failed to load packs:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const togglePack = (packId: string) => {
    setSelectedPackIds((prev) => {
      const next = new Set(prev);
      if (next.has(packId)) {
        next.delete(packId);
      } else {
        next.add(packId);
      }
      return next;
    });
  };

  const handleCreatePack = async () => {
    const trimmedName = newPackName.trim();
    if (!trimmedName) return;
    try {
      setIsSaving(true);
      const created = await invoke<WordPack>("create_word_pack_cmd", {
        name: trimmedName,
        description: null,
        coverUrl: null,
        author: null,
        languageFrom: null,
        languageTo: null,
        tags: [],
        version: "1.0.0",
      });
      setPacks((prev) => [...prev, created]);
      setSelectedPackIds((prev) => new Set(prev).add(created.id));
      setNewPackName("");
    } catch (error) {
      console.error("Failed to create pack:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirm = async () => {
    const ids = Array.from(selectedPackIds);
    await onConfirm(ids);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>选择单词合集</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2 max-h-56 overflow-y-auto rounded-md border border-border p-3">
            {isLoading ? (
              <div className="text-sm text-muted-foreground">加载中...</div>
            ) : packs.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无合集</div>
            ) : (
              packs.map((pack) => (
                <label key={pack.id} className="flex cursor-pointer items-center gap-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedPackIds.has(pack.id)}
                    onChange={() => togglePack(pack.id)}
                  />
                  <span className="truncate">{pack.name}</span>
                </label>
              ))
            )}
          </div>

          <div className="flex items-center gap-2">
            <Input
              value={newPackName}
              onChange={(e) => setNewPackName(e.target.value)}
              placeholder="新建合集名称"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void handleCreatePack();
                }
              }}
            />
            <Button
              variant="outline"
              onClick={() => void handleCreatePack()}
              disabled={isSaving || !newPackName.trim()}
            >
              新建
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={() => void handleConfirm()}>确认</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
