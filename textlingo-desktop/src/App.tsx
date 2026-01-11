import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { BookOpen, RotateCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ArticleList } from "./components/features/ArticleList";
import { ArticleReader } from "./components/features/ArticleReader";
import { NewArticleButton } from "./components/features/NewArticleDialog";
import { FavoritesButton } from "./components/features/FavoritesDialog";
import { SettingsButton } from "./components/features/SettingsDialog";
import { Button } from "./components/ui/Button";
import type { Article, AppConfig } from "./lib/tauri";
import { getApiClient } from "./lib/api";

function App() {
  const { t } = useTranslation();
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load config and articles on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [configResult, articlesResult] = await Promise.all([
        invoke<AppConfig | null>("get_config"),
        invoke<Article[]>("list_articles_cmd"),
      ]);
      setConfig(configResult);
      if (configResult) {
        getApiClient(configResult); // Initialize API client
      }
      setArticles(articlesResult);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectArticle = (article: Article) => {
    const index = articles.findIndex((a) => a.id === article.id);
    setSelectedIndex(index);
    setSelectedArticle(article);
  };

  const handleNextArticle = () => {
    if (selectedIndex < articles.length - 1) {
      handleSelectArticle(articles[selectedIndex + 1]);
    }
  };

  const handlePrevArticle = () => {
    if (selectedIndex > 0) {
      handleSelectArticle(articles[selectedIndex - 1]);
    }
  };

  const handleBackToList = () => {
    setSelectedArticle(null);
  };

  const handleArticleUpdate = () => {
    loadData();
  };

  const handleNewArticle = () => {
    // Reload full list to ensure sort order and consistency
    loadData();
  };

  const handleDeleteArticle = async (id: string) => {
    console.log("App: handleDeleteArticle called for id:", id);
    try {
      await invoke("delete_article_cmd", { id });
      console.log("App: Article deleted successfully via backend");
      await loadData(); // Reload to refresh list
    } catch (e) {
      console.error("App: Failed to delete article", e);
    }
  };

  // 从收藏夹跳转到文章
  const handleSelectArticleById = async (articleId: string) => {
    try {
      const article = await invoke<Article>("get_article", { id: articleId });
      handleSelectArticle(article);
    } catch (e) {
      console.error("App: Failed to get article by id:", e);
    }
  };

  const hasConfig = config?.model_configs && config.model_configs.length > 0 && config.active_model_id;
  const activeConfig = config?.model_configs?.find(c => c.id === config.active_model_id);
  const selectedId: string | undefined = selectedArticle?.id;

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">{t("app.loading")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm supports-[backdrop-filter]:bg-card/50">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-foreground">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="text-lg font-semibold">{t("app.title")}</h1>
            <p className="text-xs text-muted-foreground">{t("app.subtitle")}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!hasConfig && (
            <div className="px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/50 rounded-lg text-yellow-600 dark:text-yellow-400 text-sm">
              {t("header.configureApiKey")}
            </div>
          )}
          <FavoritesButton onSelectArticle={handleSelectArticleById} />
          <NewArticleButton onSave={() => handleNewArticle()} />
          <SettingsButton onSave={handleArticleUpdate} />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {selectedArticle ? (
          <ArticleReader
            article={selectedArticle}
            onBack={handleBackToList}
            onNext={handleNextArticle}
            onPrev={handlePrevArticle}
            hasNext={selectedIndex < articles.length - 1}
            hasPrev={selectedIndex > 0}
            onUpdate={handleArticleUpdate}
          />
        ) : (
          <div className="h-full max-w-4xl mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">{t("articleList.title")}</h2>
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadData}
                  disabled={isLoading}
                  title={t("common.refresh")}
                >
                  <RotateCw size={16} className={isLoading ? "animate-spin" : ""} />
                </Button>
                <p className="text-sm text-muted-foreground">
                  {t("articleList.count_other", { count: articles.length })}
                </p>
              </div>
            </div>
            <ArticleList
              articles={articles}
              isLoading={isLoading}
              onSelectArticle={handleSelectArticle}
              onDelete={handleDeleteArticle}
              selectedId={selectedId}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="px-6 py-3 border-t border-border bg-card/50 text-xs text-muted-foreground">
        <div className="flex items-center justify-between">
          <p>TextLingo Desktop {t("app.version")}</p>
          <div className="flex items-center gap-4">
            <span>{t("footer.provider")}: {activeConfig?.api_provider || t("app.notConfigured")}</span>
            <span>{t("footer.model")}: {activeConfig?.model || t("app.notConfigured")}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
