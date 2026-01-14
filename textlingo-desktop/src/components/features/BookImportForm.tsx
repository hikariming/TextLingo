/**
 * 书籍导入表单组件
 * 支持导入 EPUB 和 TXT 格式的电子书
 */

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { Loader2, BookOpen, FileText, FileType, Info } from "lucide-react";
import { Article } from "../../types";

interface BookImportFormProps {
    onSave?: (article: Article) => void;
    onCancel?: () => void;
}

export function BookImportForm({ onSave, onCancel }: BookImportFormProps) {
    const { t } = useTranslation();

    // 选择的文件路径
    const [filePath, setFilePath] = useState("");

    // 自定义标题（可选）
    const [customTitle, setCustomTitle] = useState("");

    // 加载状态
    const [isImporting, setIsImporting] = useState(false);

    // 错误信息
    const [error, setError] = useState<string | null>(null);

    // 选择文件
    const handleSelectFile = async () => {
        try {
            const selected = await open({
                multiple: false,
                filters: [
                    {
                        name: t("bookImport.fileFilterName", "电子书"),
                        extensions: ["epub", "txt", "pdf"],
                    },
                ],
            });

            if (selected && typeof selected === "string") {
                setFilePath(selected);
                setError(null);

                // 从文件路径提取文件名作为默认标题
                const fileName = selected.split(/[/\\]/).pop()?.replace(/\.(epub|txt|pdf)$/i, "") || "";
                if (!customTitle) {
                    setCustomTitle(fileName);
                }
            }
        } catch (e) {
            console.error("选择文件失败:", e);
            setError(t("bookImport.errors.selectFailed", "选择文件失败"));
        }
    };

    // 导入书籍
    const handleImport = async () => {
        if (!filePath) {
            setError(t("bookImport.errors.fileRequired", "请选择文件"));
            return;
        }

        setIsImporting(true);
        setError(null);

        try {
            const article = await invoke<Article>("import_book_cmd", {
                filePath,
                title: customTitle || null,
            });

            onSave?.(article);
        } catch (e) {
            console.error("导入书籍失败:", e);
            setError(String(e));
        } finally {
            setIsImporting(false);
        }
    };

    // 获取文件类型图标
    const getFileIcon = () => {
        if (!filePath) return <BookOpen size={20} />;
        if (filePath.toLowerCase().endsWith(".epub")) {
            return <BookOpen size={20} className="text-purple-500" />;
        }
        if (filePath.toLowerCase().endsWith(".pdf")) {
            return <FileType size={20} className="text-red-500" />;
        }
        return <FileText size={20} className="text-blue-500" />;
    };

    // 获取文件名显示
    const getFileName = () => {
        if (!filePath) return t("bookImport.filePlaceholder", "选择 EPUB 或 TXT 文件...");
        return filePath.split(/[/\\]/).pop() || filePath;
    };

    return (
        <div className="flex flex-col h-full">
            {/* 描述 */}
            <div className="flex gap-3 p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg text-sm text-purple-200/90 mb-6">
                <Info className="w-5 h-5 shrink-0 text-purple-400 mt-0.5" />
                <p>{t("bookImport.hint", "Supports papers, books, novels, etc...")}</p>
            </div>

            {/* 文件选择 */}
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium mb-2">
                        {t("bookImport.fileLabel", "书籍文件")}
                    </label>
                    <button
                        type="button"
                        onClick={handleSelectFile}
                        className="w-full flex items-center gap-3 px-4 py-3 border-2 border-dashed border-border rounded-lg hover:border-primary/50 hover:bg-muted/50 transition-colors text-left"
                    >
                        {getFileIcon()}
                        <span className={`flex-1 truncate ${filePath ? "text-foreground" : "text-muted-foreground"}`}>
                            {getFileName()}
                        </span>
                    </button>
                </div>

                {/* 自定义标题 */}
                <div>
                    <label className="block text-sm font-medium mb-2">
                        {t("bookImport.titleLabel", "书籍标题")}
                        <span className="text-muted-foreground font-normal ml-1">
                            ({t("newArticle.optional", "可选")})
                        </span>
                    </label>
                    <input
                        type="text"
                        value={customTitle}
                        onChange={(e) => setCustomTitle(e.target.value)}
                        placeholder={t("bookImport.titlePlaceholder", "留空则使用文件名")}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                </div>
            </div>

            {/* 错误提示 */}
            {error && (
                <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
                    {error}
                </div>
            )}

            {/* 按钮组 */}
            <div className="flex justify-end gap-3 mt-auto pt-6">
                <Button variant="ghost" onClick={onCancel}>
                    {t("common.cancel", "取消")}
                </Button>
                <Button
                    onClick={handleImport}
                    disabled={!filePath || isImporting}
                    className="gap-2"
                >
                    {isImporting ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            {t("bookImport.importing", "导入中...")}
                        </>
                    ) : (
                        <>
                            <BookOpen size={16} />
                            {t("bookImport.import", "导入书籍")}
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
}
