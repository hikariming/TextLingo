import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Bookmark } from "../../types";
import { Button } from "../ui/button";
import { ScrollArea } from "../ui/scroll-area";
import {
  Bookmark as BookmarkIcon,
  Trash2,
  Edit2,
  X,
  StickyNote
} from "lucide-react";
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

interface BookmarkSidebarProps {
  bookPath: string;
  bookType: "txt" | "pdf" | "epub";
  onJumpToBookmark: (bookmark: Bookmark) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function BookmarkSidebar({
  bookPath,
  bookType,
  onJumpToBookmark,
  isOpen,
  onClose,
}: BookmarkSidebarProps) {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [editingBookmark, setEditingBookmark] = useState<Bookmark | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editNote, setEditNote] = useState("");

  useEffect(() => {
    if (isOpen && bookPath) {
      loadBookmarks();
    }
  }, [isOpen, bookPath]);

  const loadBookmarks = async () => {
    try {
      const result = await invoke<Bookmark[]>("list_bookmarks_for_book_cmd", {
        bookPath,
      });
      setBookmarks(result);
    } catch (error) {
      console.error("Failed to load bookmarks:", error);
    }
  };

  const handleDeleteBookmark = async (bookmarkId: string) => {
    try {
      await invoke("delete_bookmark_cmd", { id: bookmarkId });
      setBookmarks(bookmarks.filter((b) => b.id !== bookmarkId));
    } catch (error) {
      console.error("Failed to delete bookmark:", error);
    }
  };

  const handleEditBookmark = (bookmark: Bookmark) => {
    setEditingBookmark(bookmark);
    setEditTitle(bookmark.title);
    setEditNote(bookmark.note || "");
  };

  const handleSaveEdit = async () => {
    if (!editingBookmark) return;

    try {
      const updated = await invoke<Bookmark>("update_bookmark_cmd", {
        id: editingBookmark.id,
        title: editTitle,
        note: editNote || null,
        color: null,
      });

      setBookmarks(
        bookmarks.map((b) => (b.id === updated.id ? updated : b))
      );
      setEditingBookmark(null);
    } catch (error) {
      console.error("Failed to update bookmark:", error);
    }
  };

  const formatLocation = (bookmark: Bookmark) => {
    if (bookmark.book_type === "epub" && bookmark.epub_cfi) {
      return "EPUB 位置";
    } else if (bookmark.page_number) {
      return `第 ${bookmark.page_number} 页`;
    }
    return "未知位置";
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed right-0 top-0 h-full w-80 bg-background border-l border-border shadow-lg z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <BookmarkIcon className="h-5 w-5" />
            <h2 className="font-semibold">书签</h2>
            <span className="text-sm text-muted-foreground">
              ({bookmarks.length})
            </span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Bookmarks List */}
        <ScrollArea className="flex-1 p-4">
          {bookmarks.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <BookmarkIcon className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>暂无书签</p>
              <p className="text-sm mt-1">在阅读时添加书签以快速跳转</p>
            </div>
          ) : (
            <div className="space-y-2">
              {bookmarks.map((bookmark) => (
                <div
                  key={bookmark.id}
                  className="p-3 rounded-lg border border-border hover:bg-accent cursor-pointer transition-colors"
                  onClick={() => onJumpToBookmark(bookmark)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-sm flex-1">
                      {bookmark.title}
                    </h3>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditBookmark(bookmark);
                        }}
                      >
                        <Edit2 className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteBookmark(bookmark.id);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground space-y-1">
                    <div>{formatLocation(bookmark)}</div>
                    {bookmark.note && (
                      <div className="flex items-start gap-1 mt-2 p-2 bg-muted/50 rounded">
                        <StickyNote className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <span className="text-xs">{bookmark.note}</span>
                      </div>
                    )}
                    <div className="text-xs opacity-60 mt-2">
                      {formatDate(bookmark.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingBookmark} onOpenChange={() => setEditingBookmark(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑书签</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">标题</Label>
              <Input
                id="title"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="书签标题"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="note">笔记（可选）</Label>
              <Textarea
                id="note"
                value={editNote}
                onChange={(e) => setEditNote(e.target.value)}
                placeholder="添加笔记..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingBookmark(null)}>
              取消
            </Button>
            <Button onClick={handleSaveEdit}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
