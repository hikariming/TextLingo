import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Loader2, Globe, Check, Eye } from "lucide-react";
import { getApiClient } from "../../lib/api";
import { Article } from "../../types";

interface WebImportFormProps {
  onSave?: (article: Article) => void;
  onCancel: () => void;
}

interface FetchedContent {
  title: string;
  content: string;
}

export function WebImportForm({ onSave, onCancel }: WebImportFormProps) {
  const { t } = useTranslation();
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isFetching, setIsFetching] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [fetchSource, setFetchSource] = useState<"local" | "backend" | null>(null);

  const isValidUrl = (value: string) =>
    value.startsWith("http://") || value.startsWith("https://");

  const canImport = !!previewLoaded && content.trim().length >= 10 && isValidUrl(url.trim());

  const fetchWithLocalFirst = async (sourceUrl: string): Promise<FetchedContent> => {
    try {
      const local = await invoke<FetchedContent>("fetch_url_content", { url: sourceUrl });
      setFetchSource("local");
      return local;
    } catch (localErr) {
      const config = (await invoke("get_config")) as any;
      const apiClient = getApiClient(config);
      if (!apiClient.isBackendConfigured()) {
        throw localErr;
      }

      const backend = await apiClient.fetchUrlContent(sourceUrl);
      setFetchSource("backend");
      return backend;
    }
  };

  const handleFetchPreview = async () => {
    const normalizedUrl = url.trim();
    if (!normalizedUrl) {
      setError(t("webImport.errors.urlRequired"));
      return;
    }
    if (!isValidUrl(normalizedUrl)) {
      setError(t("webImport.errors.urlInvalid"));
      return;
    }

    setIsFetching(true);
    setError(null);
    setPreviewLoaded(false);
    setFetchSource(null);

    try {
      const fetched = await fetchWithLocalFirst(normalizedUrl);
      const nextTitle = fetched.title?.trim() || "";
      const nextContent = fetched.content?.trim() || "";

      setTitle(nextTitle);
      setContent(nextContent);
      setPreviewLoaded(true);

      if (nextContent.length < 10) {
        setError(t("webImport.errors.contentTooShort"));
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setIsFetching(false);
    }
  };

  const handleImport = async () => {
    const normalizedUrl = url.trim();
    if (!canImport) {
      setError(t("webImport.errors.contentTooShort"));
      return;
    }

    setIsImporting(true);
    setError(null);
    try {
      const article = await invoke<Article>("import_web_material_cmd", {
        url: normalizedUrl,
        title: title.trim() || undefined,
        content,
      });
      onSave?.(article);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm break-words">
            {error}
          </div>
        )}

        <div className="flex gap-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-foreground/90">
          <Globe className="w-5 h-5 shrink-0 text-blue-500 mt-0.5" />
          <p>{t("webImport.hint")}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            {t("webImport.urlLabel")}
          </label>
          <div className="flex gap-2">
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t("webImport.urlPlaceholder")}
              disabled={isFetching || isImporting}
            />
            <Button
              onClick={handleFetchPreview}
              disabled={isFetching || isImporting}
              className="gap-2"
            >
              {isFetching ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
              {isFetching ? t("webImport.fetching") : t("webImport.fetchPreview")}
            </Button>
          </div>
          {fetchSource && (
            <p className="text-xs text-muted-foreground mt-2">
              {fetchSource === "local"
                ? t("webImport.previewSourceLocal")
                : t("webImport.previewSourceBackend")}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            {t("webImport.titleLabel")}
          </label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t("webImport.titlePlaceholder")}
            disabled={isImporting}
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-foreground">
              {t("webImport.contentLabel")}
            </label>
            <span className="text-xs text-muted-foreground">
              {t("webImport.wordCount", { count: content.trim().length })}
            </span>
          </div>
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={t("webImport.contentPlaceholder")}
            className="min-h-[220px]"
            disabled={isImporting}
          />
        </div>
      </div>

      <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
        <Button variant="secondary" onClick={onCancel} disabled={isImporting || isFetching}>
          {t("common.cancel")}
        </Button>
        <Button onClick={handleImport} disabled={!canImport || isImporting || isFetching} className="gap-2">
          {isImporting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              {t("webImport.importing")}
            </>
          ) : (
            <>
              <Check size={16} />
              {t("webImport.import")}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
