import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Plus, FileText, Youtube, FolderOpen } from "lucide-react";
import { Article } from "../../types";
import { NewArticleForm } from "./NewArticleForm";
import { YouTubeImportForm } from "./YouTubeImportForm";
import { cn } from "../../lib/utils";

import { LocalVideoImportForm } from "./LocalVideoImportForm";

type MaterialType = "article" | "youtube" | "local";

interface NewMaterialDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSave?: (article: Article) => void;
}

export function NewMaterialDialog({ isOpen, onClose, onSave }: NewMaterialDialogProps) {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<MaterialType>("article");

    const handleClose = () => {
        onClose();
    };

    const handleSave = (article: Article) => {
        onSave?.(article);
        handleClose();
    };

    return (
        <Dialog
            isOpen={isOpen}
            onClose={handleClose}
            title={t("header.newMaterial")}
            className="md:max-w-3xl !p-0 overflow-hidden flex flex-col h-[600px]"
        >
            <div className="flex flex-1 h-full overflow-hidden">
                {/* Left Sidebar - Tabs */}
                <div className="w-48 bg-muted/30 border-r border-border p-4 flex flex-col gap-2">
                    <h3 className="text-sm font-medium text-muted-foreground mb-2 px-2">
                        {t("header.newMaterial")}
                    </h3>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "article"
                                ? "bg-primary/10 text-primary"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground"
                        )}
                        onClick={() => setActiveTab("article")}
                    >
                        <FileText size={18} />
                        {t("newArticle.title")}
                    </button>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "youtube"
                                ? "bg-red-500/10 text-red-500"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground"
                        )}
                        onClick={() => setActiveTab("youtube")}
                    >
                        <Youtube size={18} />
                        {t("youtubeImport.title")}
                    </button>

                    <button
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            activeTab === "local"
                                ? "bg-blue-500/10 text-blue-500"
                                : "hover:bg-muted text-muted-foreground hover:text-foreground"
                        )}
                        onClick={() => setActiveTab("local")}
                    >
                        <FolderOpen size={18} />
                        {t("localImport.title")}
                    </button>
                </div>

                {/* Right Content */}
                <div className="flex-1 p-6 overflow-hidden">
                    {/* Remove DialogContent wrapper here since we are handling layout manually inside the dialog container */}
                    <div className="h-full">
                        {activeTab === "article" && (
                            <NewArticleForm onSave={handleSave} onCancel={handleClose} />
                        )}
                        {activeTab === "youtube" && (
                            <YouTubeImportForm onSave={handleSave} onCancel={handleClose} />
                        )}
                        {activeTab === "local" && (
                            <LocalVideoImportForm onSave={handleSave} onCancel={handleClose} />
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
