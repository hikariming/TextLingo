import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent, DialogFooter } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Youtube, Loader2, Download } from "lucide-react";
import { Article } from "../../types";

interface YouTubeImportDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSave?: (article: Article) => void;
}

export function YouTubeImportDialog({ isOpen, onClose, onSave }: YouTubeImportDialogProps) {
    const { t } = useTranslation();
    const [url, setUrl] = useState("");
    const [isImporting, setIsImporting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleImport = async () => {
        if (!url.trim()) {
            setError(t("youtubeImport.errors.urlRequired"));
            return;
        }

        if (!url.includes("youtube.com") && !url.includes("youtu.be")) {
            setError(t("youtubeImport.errors.urlInvalid"));
            return;
        }

        setIsImporting(true);
        setError(null);

        try {
            const article = await invoke<Article>("import_youtube_video_cmd", { url: url.trim() });
            onSave?.(article);
            handleClose();
        } catch (err) {
            console.error("YouTube import failed:", err);
            setError(String(err)); // Show exact error from backend
        } finally {
            setIsImporting(false);
        }
    };

    const handleClose = () => {
        setUrl("");
        setError(null);
        onClose();
    };

    return (
        <Dialog isOpen={isOpen} onClose={handleClose} title={t("youtubeImport.title")}>
            <DialogContent>
                {error && (
                    <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm break-all">
                        {error}
                    </div>
                )}

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            {t("youtubeImport.urlLabel")}
                        </label>
                        <div className="flex gap-2">
                            <Input
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder={t("youtubeImport.urlPlaceholder")}
                                disabled={isImporting}
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            {t("youtubeImport.processing")} (Downloads video & subtitles)
                        </p>
                    </div>
                </div>
            </DialogContent>

            <DialogFooter>
                <Button variant="secondary" onClick={handleClose} disabled={isImporting}>
                    {t("youtubeImport.cancel")}
                </Button>
                <Button onClick={handleImport} disabled={isImporting} className="gap-2 bg-red-600 hover:bg-red-700 text-white">
                    {isImporting ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            {t("youtubeImport.importing")}
                        </>
                    ) : (
                        <>
                            <Download size={16} />
                            {t("youtubeImport.import")}
                        </>
                    )}
                </Button>
            </DialogFooter>
        </Dialog>
    );
}

interface YouTubeImportButtonProps {
    onSave?: (article: Article) => void;
}

export function YouTubeImportButton({ onSave }: YouTubeImportButtonProps) {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <Button
                onClick={() => setIsOpen(true)}
                className="gap-2 bg-red-600 hover:bg-red-700 text-white"
                title={t("youtubeImport.title")}
            >
                <Youtube size={16} />
                <span className="hidden sm:inline">YouTube</span>
            </Button>
            <YouTubeImportDialog
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                onSave={(article) => {
                    onSave?.(article);
                    setIsOpen(false);
                }}
            />
        </>
    );
}
