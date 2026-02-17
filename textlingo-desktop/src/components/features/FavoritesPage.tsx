import { useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { save } from "@tauri-apps/plugin-dialog";
import { useTranslation } from "react-i18next";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Button } from "../ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { ArrowLeft, BookOpen, Check, Copy, Download, ExternalLink, FileDown, Loader2, MoreHorizontal, SpellCheck, Trash2, Upload } from "lucide-react";
import type { Article, FavoriteGrammar, FavoriteVocabulary, WordPack } from "../../types";
import { WordPackManager } from "./WordPackManager";
import { WordRecitePanel } from "./WordRecitePanel";

interface FavoritesPageProps {
  onBack: () => void;
  onSelectArticle: (article: Article) => void;
}

interface ExportWordPackResult {
  file_name: string;
  json_content: string;
}

interface ImportWordPackResult {
  created_pack_id: string;
  total: number;
  imported: number;
  skipped: number;
  errors: string[];
}

function formatLocalDate(dateString?: string): string {
  if (!dateString) return "-";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("zh-CN");
}

export function FavoritesPage({ onBack, onSelectArticle }: FavoritesPageProps) {
  const { t } = useTranslation();
  const [vocabularies, setVocabularies] = useState<FavoriteVocabulary[]>([]);
  const [grammars, setGrammars] = useState<FavoriteGrammar[]>([]);
  const [packs, setPacks] = useState<WordPack[]>([]);
  const [activeTab, setActiveTab] = useState("vocabulary");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPackId, setSelectedPackId] = useState("all");
  const [articles, setArticles] = useState<Map<string, Article>>(new Map());
  const [copySuccess, setCopySuccess] = useState(false);
  const [isReciteOpen, setIsReciteOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedPackName = useMemo(() => {
    if (selectedPackId === "all") return t("favorites.allPacks", "全部单词");
    return packs.find((pack) => pack.id === selectedPackId)?.name ?? t("favorites.unknownPack", "未知合集");
  }, [selectedPackId, packs, t]);

  const vocabularyCountByPack = useMemo(() => {
    const map = new Map<string, number>();
    for (const vocab of vocabularies) {
      for (const packId of vocab.pack_ids ?? []) {
        map.set(packId, (map.get(packId) ?? 0) + 1);
      }
    }
    return map;
  }, [vocabularies]);

  const filteredVocabularies = useMemo(() => {
    if (selectedPackId === "all") return vocabularies;
    return vocabularies.filter((vocab) => vocab.pack_ids?.includes(selectedPackId));
  }, [selectedPackId, vocabularies]);

  const loadFavorites = async () => {
    setIsLoading(true);
    try {
      const [vocabList, grammarList, packList] = await Promise.all([
        invoke<FavoriteVocabulary[]>("list_favorite_vocabularies_cmd"),
        invoke<FavoriteGrammar[]>("list_favorite_grammars_cmd"),
        invoke<WordPack[]>("list_word_packs_cmd"),
      ]);

      setVocabularies(vocabList);
      setGrammars(grammarList);
      setPacks(packList);

      const articleIds = new Set<string>();
      vocabList.forEach((v) => v.source_article_id && articleIds.add(v.source_article_id));
      grammarList.forEach((g) => g.source_article_id && articleIds.add(g.source_article_id));

      const map = new Map<string, Article>();
      for (const id of articleIds) {
        try {
          const article = await invoke<Article>("get_article", { id });
          map.set(id, article);
        } catch {
          // ignore deleted article
        }
      }
      setArticles(map);
    } catch (error) {
      console.error("Failed to load favorites:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadFavorites();
  }, []);

  useEffect(() => {
    if (selectedPackId === "all") return;
    if (!packs.some((pack) => pack.id === selectedPackId)) {
      setSelectedPackId("all");
    }
  }, [packs, selectedPackId]);

  const handleDeleteVocabulary = async (id: string) => {
    try {
      await invoke("delete_favorite_vocabulary_cmd", { id });
      setVocabularies((prev) => prev.filter((item) => item.id !== id));
    } catch (error) {
      console.error("Failed to delete vocabulary:", error);
    }
  };

  const handleDeleteGrammar = async (id: string) => {
    try {
      await invoke("delete_favorite_grammar_cmd", { id });
      setGrammars((prev) => prev.filter((item) => item.id !== id));
    } catch (error) {
      console.error("Failed to delete grammar:", error);
    }
  };

  const handleGoToArticle = (articleId: string) => {
    const article = articles.get(articleId);
    if (article) {
      onSelectArticle(article);
    }
  };

  const handleCreatePack = async () => {
    const name = window.prompt(t("favorites.newPackPrompt", "输入新合集名称"));
    if (!name || !name.trim()) return;
    try {
      await invoke<WordPack>("create_word_pack_cmd", {
        name: name.trim(),
        description: null,
        coverUrl: null,
        author: null,
        languageFrom: null,
        languageTo: null,
        tags: [],
        version: "1.0.0",
      });
      await loadFavorites();
    } catch (error) {
      console.error("Failed to create pack:", error);
    }
  };

  const handleDeletePack = async (pack: WordPack) => {
    if (!window.confirm(t("favorites.deletePackConfirm", `确定删除合集「${pack.name}」吗？`))) {
      return;
    }
    try {
      await invoke("delete_word_pack_cmd", { id: pack.id });
      await loadFavorites();
    } catch (error) {
      console.error("Failed to delete pack:", error);
    }
  };

  const getPlainTextExport = (): string => filteredVocabularies.map((v) => v.word).join("\n");

  const handleCopyToClipboard = async () => {
    if (filteredVocabularies.length === 0) return;
    try {
      await navigator.clipboard.writeText(getPlainTextExport());
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 1500);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const handleDownloadTxt = async () => {
    if (filteredVocabularies.length === 0) return;
    const defaultPath = `${selectedPackName}.txt`;
    const filePath = await save({
      defaultPath,
      filters: [{ name: "TXT", extensions: ["txt"] }],
    });
    if (!filePath) return;
    try {
      await invoke("write_text_file", { path: filePath, content: getPlainTextExport() });
    } catch (error) {
      console.error("Failed to write txt file:", error);
    }
  };

  const handleExportWordPack = async () => {
    if (selectedPackId === "all") {
      alert(t("favorites.selectPackForExport", "请先选择一个具体合集再导出"));
      return;
    }

    try {
      const result = await invoke<ExportWordPackResult>("export_word_pack_cmd", {
        packId: selectedPackId,
      });
      const filePath = await save({
        defaultPath: result.file_name,
        filters: [{ name: "OpenKoto Pack", extensions: ["okpack.json", "json"] }],
      });
      if (!filePath) return;
      await invoke("write_text_file", { path: filePath, content: result.json_content });
    } catch (error) {
      console.error("Failed to export word pack:", error);
    }
  };

  const handleImportWordPack = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const jsonContent = String(e.target?.result ?? "");
        const result = await invoke<ImportWordPackResult>("import_word_pack_cmd", { jsonContent });
        await loadFavorites();
        alert(
          t(
            "favorites.importPackSuccess",
            `导入完成：新增 ${result.imported}，跳过 ${result.skipped}，总数 ${result.total}`
          )
        );
      } catch (error) {
        console.error("Failed to import word pack:", error);
        alert(t("favorites.importError", "导入失败"));
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  const renderVocabularyActions = () => (
    <div className="flex items-center gap-2">
      <input
        ref={fileInputRef}
        className="hidden"
        type="file"
        accept=".json,.okpack.json"
        onChange={handleImportWordPack}
      />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <MoreHorizontal size={16} />
            {t("favorites.actions", "管理")}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-72">
          {filteredVocabularies.length > 0 && (
            <>
              <DropdownMenuLabel>{t("favorites.exportWordList", "导出单词列表")}</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => void handleCopyToClipboard()}>
                <Copy className="mr-2 h-4 w-4" />
                <span>{copySuccess ? t("favorites.copied", "已复制") : t("favorites.copyToClipboard", "复制到剪贴板")}</span>
                {copySuccess && <Check className="ml-auto h-4 w-4 text-green-500" />}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => void handleDownloadTxt()}>
                <FileDown className="mr-2 h-4 w-4" />
                <span>{t("favorites.downloadTxt", "下载 TXT 文件")}</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
            </>
          )}

          <DropdownMenuLabel>{t("favorites.packTrade", "单词包")}</DropdownMenuLabel>
          <DropdownMenuItem onClick={() => void handleExportWordPack()}>
            <Download className="mr-2 h-4 w-4" />
            <span>{t("favorites.exportWordPack", "导出单词包")}</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => fileInputRef.current?.click()}>
            <Upload className="mr-2 h-4 w-4" />
            <span>{t("favorites.importWordPack", "导入单词包")}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );

  return (
    <div className="h-full max-w-6xl mx-auto p-8 flex flex-col bg-background/50">
      <div className="flex items-center gap-4 mb-8">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft size={20} />
        </Button>
        <div>
          <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
            {t("favorites.title", "我的收藏")}
          </h2>
          <p className="text-sm text-muted-foreground/80 mt-1">
            {t("favorites.subtitle", "管理您收藏的单词与语法")}
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col space-y-6">
        <TabsList className="w-fit bg-muted/50 border border-border/50 p-1">
          <TabsTrigger value="vocabulary" className="gap-2 px-4">
            <BookOpen size={14} />
            {t("favorites.vocabulary", "单词收藏")}
            <span className="text-xs opacity-70 ml-1">{vocabularies.length}</span>
          </TabsTrigger>
          <TabsTrigger value="grammar" className="gap-2 px-4">
            <SpellCheck size={14} />
            {t("favorites.grammar", "语法收藏")}
            <span className="text-xs opacity-70 ml-1">{grammars.length}</span>
          </TabsTrigger>
        </TabsList>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="animate-spin text-primary" size={32} />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto pr-2 min-h-0">
            <TabsContent value="vocabulary" className="mt-0 h-full flex flex-col">
              <div className="flex justify-end mb-5">{renderVocabularyActions()}</div>

              <div className="flex gap-4 min-h-0 pb-8">
                <WordPackManager
                  packs={packs}
                  selectedPackId={selectedPackId}
                  vocabularyCountByPack={vocabularyCountByPack}
                  onSelectPack={setSelectedPackId}
                  onCreatePack={() => void handleCreatePack()}
                  onDeletePack={(pack) => void handleDeletePack(pack)}
                  onStartReview={() => setIsReciteOpen(true)}
                />

                <div className="flex-1">
                  {filteredVocabularies.length === 0 ? (
                    <EmptyState
                      icon={<BookOpen size={48} />}
                      title={t("favorites.noVocabulary", "暂无单词收藏")}
                      description={t("favorites.noVocabularyDesc", "在文章学习中点击单词旁的收藏按钮即可添加")}
                    />
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filteredVocabularies.map((vocab) => (
                        <VocabularyCard
                          key={vocab.id}
                          vocab={vocab}
                          article={vocab.source_article_id ? articles.get(vocab.source_article_id) : undefined}
                          onDelete={() => void handleDeleteVocabulary(vocab.id)}
                          onGoToArticle={
                            vocab.source_article_id
                              ? () => handleGoToArticle(vocab.source_article_id as string)
                              : undefined
                          }
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="grammar" className="mt-0 h-full flex flex-col">
              {grammars.length === 0 ? (
                <EmptyState
                  icon={<SpellCheck size={48} />}
                  title={t("favorites.noGrammar", "暂无语法收藏")}
                  description={t("favorites.noGrammarDesc", "在文章学习中点击语法点旁的收藏按钮即可添加")}
                />
              ) : (
                <div className="space-y-4 pb-8">
                  {grammars.map((grammar) => (
                    <GrammarCard
                      key={grammar.id}
                      grammar={grammar}
                      article={grammar.source_article_id ? articles.get(grammar.source_article_id) : undefined}
                      onDelete={() => void handleDeleteGrammar(grammar.id)}
                      onGoToArticle={
                        grammar.source_article_id
                          ? () => handleGoToArticle(grammar.source_article_id as string)
                          : undefined
                      }
                    />
                  ))}
                </div>
              )}
            </TabsContent>
          </div>
        )}
      </Tabs>

      <WordRecitePanel
        open={isReciteOpen}
        onOpenChange={setIsReciteOpen}
        packId={selectedPackId}
        packName={selectedPackName}
        onReviewed={loadFavorites}
      />
    </div>
  );
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-6 p-6 rounded-full bg-muted/30 text-muted-foreground/50 border border-border/50">
        {icon}
      </div>
      <h3 className="text-lg font-semibold mb-2 text-foreground">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed">{description}</p>
    </div>
  );
}

function VocabularyCard({
  vocab,
  article,
  onDelete,
  onGoToArticle,
}: {
  vocab: FavoriteVocabulary;
  article?: Article;
  onDelete: () => void;
  onGoToArticle?: () => void;
}) {
  return (
    <div className="group relative bg-card hover:bg-gradient-to-br hover:from-card hover:to-primary/5 border border-border/50 hover:border-primary/20 p-5 rounded-xl transition-all duration-300 shadow-sm hover:shadow-md">
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-baseline gap-2">
          <span className="font-bold text-lg text-primary">{vocab.word}</span>
          {vocab.reading && <span className="text-xs text-muted-foreground/80 font-mono">{vocab.reading}</span>}
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onGoToArticle && article && (
            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary" onClick={onGoToArticle} title={article.title}>
              <ExternalLink size={14} />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={onDelete}>
            <Trash2 size={14} />
          </Button>
        </div>
      </div>

      <div className="space-y-2 mb-3">
        <div className="text-sm text-foreground/90 leading-relaxed font-medium">{vocab.meaning}</div>
        {vocab.usage && (
          <div className="inline-block text-xs text-primary/80 bg-primary/5 px-2 py-1 rounded-md border border-primary/10">
            {vocab.usage}
          </div>
        )}
        {vocab.explanation && <div className="text-xs text-muted-foreground line-clamp-3">{vocab.explanation}</div>}
      </div>

      <div className="mt-2 rounded-md bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground">
        状态: {vocab.srs_state ?? "new"} | 到期: {vocab.due_date ?? "-"} | 复习: {vocab.review_count ?? 0}
      </div>

      {vocab.source_article_title && (
        <div className="pt-3 mt-2 border-t border-border/30 text-[10px] text-muted-foreground/60 flex items-center gap-1.5 truncate">
          <BookOpen size={10} />
          <span className="truncate">
            {article ? vocab.source_article_title : <span className="line-through decoration-muted-foreground/50 opacity-70">{vocab.source_article_title} (已删除)</span>}
          </span>
        </div>
      )}
    </div>
  );
}

function GrammarCard({
  grammar,
  article,
  onDelete,
  onGoToArticle,
}: {
  grammar: FavoriteGrammar;
  article?: Article;
  onDelete: () => void;
  onGoToArticle?: () => void;
}) {
  return (
    <div className="group relative bg-card hover:bg-primary/[0.02] border border-border/60 hover:border-primary/20 p-5 rounded-xl transition-all duration-300 shadow-sm hover:shadow-md">
      <div className="absolute left-0 top-4 bottom-4 w-1 bg-primary/40 rounded-r-lg group-hover:bg-primary transition-colors"></div>
      <div className="pl-4 flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <h5 className="font-bold text-base text-foreground">{grammar.point}</h5>
          <p className="text-sm text-muted-foreground leading-relaxed">{grammar.explanation}</p>
          {grammar.example && (
            <div className="bg-muted/30 p-3 rounded-lg border border-border/50 text-sm text-foreground/80 italic relative mt-3">
              <span className="relative z-10">{grammar.example}</span>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onGoToArticle && article && (
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-primary" onClick={onGoToArticle} title={article.title}>
              <ExternalLink size={16} />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={onDelete}>
            <Trash2 size={16} />
          </Button>
        </div>
      </div>

      {grammar.source_article_title && (
        <div className="pl-4 mt-4 pt-3 border-t border-border/30 text-[10px] text-muted-foreground/60 flex items-center gap-1.5">
          <BookOpen size={10} />
          <span>{article ? grammar.source_article_title : <span className="line-through decoration-muted-foreground/50 opacity-70">{grammar.source_article_title} (已删除)</span>}</span>
        </div>
      )}
      <div className="pl-4 mt-2 text-[11px] text-muted-foreground">收藏时间: {formatLocalDate(grammar.created_at)}</div>
    </div>
  );
}
