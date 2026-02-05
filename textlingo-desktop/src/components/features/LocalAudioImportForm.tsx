import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Loader2, FolderOpen, Import } from "lucide-react";
import { Article } from "../../types";

interface LocalAudioImportFormProps {
    onSave?: (article: Article) => void;
    onCancel: () => void;
}

export function LocalAudioImportForm({ onSave, onCancel }: LocalAudioImportFormProps) {
    const { t } = useTranslation();
    const [filePath, setFilePath] = useState("");
    const [isImporting, setIsImporting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSelectFile = async () => {
        try {
            const selected = await open({
                multiple: false,
                filters: [{
                    name: 'Audio',
                    extensions: ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'wma']
                }]
            });

            if (selected) {
                setFilePath(selected as string);
                setError(null);
            }
        } catch (err) {
            console.error("Failed to open file dialog:", err);
            setError("Failed to open file dialog");
        }
    };

    const handleImport = async () => {
        if (!filePath) {
            setError(t("audioImport.errors.fileRequired"));
            return;
        }

        setIsImporting(true);
        setError(null);

        try {
            const article = await invoke<Article>("import_local_video_cmd", { filePath });
            onSave?.(article);
        } catch (err) {
            console.error("Audio import failed:", err);
            setError(String(err));
        } finally {
            setIsImporting(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex-1 space-y-4">
                {error && (
                    <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm break-all">
                        {error}
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                        {t("audioImport.fileLabel")}
                    </label>
                    <div className="flex gap-2">
                        <Input
                            value={filePath}
                            readOnly
                            placeholder={t("audioImport.filePlaceholder")}
                            disabled={isImporting}
                            className="text-muted-foreground"
                        />
                        <Button
                            variant="secondary"
                            onClick={handleSelectFile}
                            disabled={isImporting}
                            title="Select File"
                        >
                            <FolderOpen size={18} />
                        </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                        {t("audioImport.description")}
                    </p>
                </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
                <Button variant="secondary" onClick={onCancel} disabled={isImporting}>
                    {t("common.cancel")}
                </Button>
                <Button onClick={handleImport} disabled={isImporting || !filePath} className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground">
                    {isImporting ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            {t("audioImport.importing")}
                        </>
                    ) : (
                        <>
                            <Import size={16} />
                            {t("audioImport.import")}
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
}
