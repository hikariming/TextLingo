import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Plus, FileText, Youtube, FolderOpen, BookOpen, Music } from "lucide-react";
import { Article } from "../../types";
import { NewArticleForm } from "./NewArticleForm";
import { YouTubeImportForm } from "./YouTubeImportForm";
import { LocalVideoImportForm } from "./LocalVideoImportForm";
import { BookImportForm } from "./BookImportForm";
import { LocalAudioImportForm } from "./LocalAudioImportForm";
import { cn } from "../../lib/utils";

const AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'wma'];

function isAudioFile(path: string): boolean {
    const ext = path.split('.').pop()?.toLowerCase() || '';
    return AUDIO_EXTENSIONS.includes(ext);
}

type MaterialType = "article" | "youtube" | "local" | "book" | "audio";

interface NewMaterialDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSave?: (article: Article) => void;
    editingArticle?: Article | null;
}

export function NewMaterialDialog({ isOpen, onClose, onSave, editingArticle }: NewMaterialDialogProps) {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<MaterialType>("article");

    // Initialize/Reset tab when dialog opens or editingArticle changes
    useState(() => {
        if (editingArticle) {
            if (editingArticle.book_path) setActiveTab("book");
            else if (editingArticle.media_path?.includes("http")) setActiveTab("youtube"); // Simple heuristic
            else if (editingArticle.media_path && isAudioFile(editingArticle.media_path)) setActiveTab("audio");
            else if (editingArticle.media_path) setActiveTab("local");
            else setActiveTab("article");
        } else {
            setActiveTab("article");
        }
    });

    const handleClose = () => {
        onClose();
    };

    const handleSave = (article: Article) => {
        onSave?.(article);
        handleClose();
    };

    const isEditing = !!editingArticle;

    return (
        <Dialog
            isOpen={isOpen}
            onClose={handleClose}
            title={isEditing ? t("articleList.edit", "编辑素材") : t("header.newMaterial")}
            className="md:max-w-3xl !p-0 overflow-hidden flex flex-col h-[600px]"
        >
            <div className="flex flex-1 h-full overflow-hidden">
                {/* Left Sidebar - Tabs */}
                <div className="w-48 bg-muted/30 border-r border-border p-4 flex flex-col gap-2">
                    <h3 className="text-sm font-medium text-muted-foreground mb-2 px-2">
                        {isEditing ? t("articleList.edit") : t("header.newMaterial")}
                    </h3>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "article"
                                ? "bg-primary/10 text-primary"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground",
                            isEditing && activeTab !== "article" && "opacity-50 cursor-not-allowed"
                        )}
                        onClick={() => !isEditing && setActiveTab("article")}
                        disabled={isEditing}
                    >
                        <FileText size={18} />
                        {t("newArticle.title")}
                    </button>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "book"
                                ? "bg-purple-500/10 text-purple-500"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground",
                            isEditing && activeTab !== "book" && "opacity-50 cursor-not-allowed"
                        )}
                        onClick={() => !isEditing && setActiveTab("book")}
                        disabled={isEditing}
                    >
                        <BookOpen size={18} />
                        {t("bookImport.title", "导入书籍")}
                    </button>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "youtube"
                                ? "bg-red-500/10 text-red-500"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground",
                            isEditing && activeTab !== "youtube" && "opacity-50 cursor-not-allowed"
                        )}
                        onClick={() => !isEditing && setActiveTab("youtube")}
                        disabled={isEditing}
                    >
                        <Youtube size={18} />
                        {t("youtubeImport.title")}
                    </button>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "local"
                                ? "bg-accent/10 text-accent-foreground"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground",
                            isEditing && activeTab !== "local" && "opacity-50 cursor-not-allowed"
                        )}
                        onClick={() => !isEditing && setActiveTab("local")}
                        disabled={isEditing}
                    >
                        <FolderOpen size={18} />
                        {t("localImport.title")}
                    </button>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "audio"
                                ? "bg-green-500/10 text-green-500"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground",
                            isEditing && activeTab !== "audio" && "opacity-50 cursor-not-allowed"
                        )}
                        onClick={() => !isEditing && setActiveTab("audio")}
                        disabled={isEditing}
                    >
                        <Music size={18} />
                        {t("audioImport.title", "本地音频")}
                    </button>
                </div>

                {/* Right Content */}
                <div className="flex-1 p-6 overflow-hidden">
                    <div className="h-full">
                        {activeTab === "article" && (
                            <NewArticleForm onSave={handleSave} onCancel={handleClose} initialArticle={editingArticle || undefined} />
                        )}
                        {/* Other forms do not support editing yet, so they will behave as 'New' or might just ignore initialArticle since we didn't add it to them.
                            Ideally we should add initialArticle support to them too, or fallback to 'article' form for editing metadata.
                            For now, if it's not 'article', we might just show the 'article' form which allows editing Title/Content.
                            BUT, I forced the tab above.
                            Let's relax the tab force if it's not 'article' type?
                            Or, stick to 'article' form for all edits?
                            Actually, 'book', 'youtube', 'local' tabs are import forms. They don't have fields for Title/Content usually (except import params).
                            So using NewArticleForm for EDITING is probably the correct approach for all types (editing the result).
                        */}
                        {activeTab !== "article" && isEditing ? (
                            // Fallback to NewArticleForm for editing metadata of non-article types
                            <NewArticleForm onSave={handleSave} onCancel={handleClose} initialArticle={editingArticle || undefined} />
                        ) : (
                            <>
                                {activeTab === "book" && <BookImportForm onSave={handleSave} onCancel={handleClose} />}
                                {activeTab === "youtube" && <YouTubeImportForm onSave={handleSave} onCancel={handleClose} />}
                                {activeTab === "local" && <LocalVideoImportForm onSave={handleSave} onCancel={handleClose} />}
                                {activeTab === "audio" && <LocalAudioImportForm onSave={handleSave} onCancel={handleClose} />}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </Dialog>
    );
}

interface NewMaterialButtonProps {
    onSave?: (article: Article) => void;
}

export function NewMaterialButton({ onSave }: NewMaterialButtonProps) {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <Button onClick={() => setIsOpen(true)} className="gap-2">
                <Plus size={16} />
                {t("header.newMaterial")}
            </Button>
            <NewMaterialDialog
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                onSave={onSave}
            />
        </>
    );
}
