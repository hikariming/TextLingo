import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { BookOpen, RotateCw, Star, LayoutGrid, List, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ArticleList } from "./components/features/ArticleList";
import { ArticleReader } from "./components/features/ArticleReader";
import { BookReader } from "./components/features/BookReader";
import { NewMaterialDialog } from "./components/features/NewMaterialDialog";
import { FavoritesPage } from "./components/features/FavoritesPage";
import { SettingsButton } from "./components/features/SettingsDialog";
import { ApiQuickSwitcher } from "./components/features/ApiQuickSwitcher";
import { OnboardingDialog } from "./components/features/OnboardingDialog";
import { Button } from "./components/ui/Button";
import { UpdateChecker } from "./components/features/UpdateChecker";
import type { Article, AppConfig } from "./lib/tauri";
import { getApiClient } from "./lib/api";

function App() {
  const { t } = useTranslation();
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showFavorites, setShowFavorites] = useState(false);
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "card">("card");
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Load config and articles on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async (): Promise<Article[]> => {
    setIsLoading(true);
    try {
      const [configResult, articlesResult] = await Promise.all([
        invoke<AppConfig | null>("get_config"),
        invoke<Article[]>("list_articles_cmd"),
      ]);
      setConfig(configResult);
      if (configResult) {
        getApiClient(configResult); // Initialize API client
        // Check if onboarding is needed (no model configs yet)
        if (!configResult.model_configs || configResult.model_configs.length === 0) {
          setShowOnboarding(true);
        }
      } else {
        // No config at all means first time
        setShowOnboarding(true);
      }
      setArticles(articlesResult);
      return articlesResult;
    } catch (err) {
      console.error("Failed to load data:", err);
      return [];
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

  const handleGoHome = () => {
    setSelectedArticle(null);
    setShowFavorites(false);
  };

  const handleToggleFavorites = () => {
    setShowFavorites(true);
    setSelectedArticle(null);
  };

  const handleBackFromFavorites = () => {
    setShowFavorites(false);
  };

  const handleArticleUpdate = async () => {
    const refreshedArticles = await loadData();
    // 如果当前有选中的文章，用最新数据更新它
    if (selectedArticle) {
      const updatedArticle = refreshedArticles.find(a => a.id === selectedArticle.id);
      if (updatedArticle) {
        console.log("[App] Refreshed selectedArticle with", updatedArticle.segments?.length, "segments");
        setSelectedArticle(updatedArticle);
      }
    }
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

  const handleCreateMaterial = () => {
    setEditingArticle(null);
    setIsEditDialogOpen(true);
  };

  const handleEditArticle = (article: Article) => {
    setEditingArticle(article);
    setIsEditDialogOpen(true);
  };



  const hasConfig = config?.model_configs && config.model_configs.length > 0 && config.active_model_id;
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
      {!selectedArticle && (
        <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm supports-[backdrop-filter]:bg-card/50">
          <div className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity" onClick={handleGoHome}>
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

            <Button
              variant={showFavorites ? "default" : "secondary"}
              onClick={handleToggleFavorites}
              className="gap-2"
            >
              <Star size={16} className={showFavorites ? "fill-current" : ""} />
              {t("header.favorites", "收藏夹")}
            </Button>

            <Button onClick={handleCreateMaterial} className="gap-2">
              <Plus size={16} />
              {t("header.newMaterial")}
            </Button>
            <SettingsButton onSave={handleArticleUpdate} />
          </div>
        </header>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <NewMaterialDialog
          isOpen={isEditDialogOpen}
          onClose={() => { setIsEditDialogOpen(false); setEditingArticle(null) }}
          onSave={handleArticleUpdate}
          editingArticle={editingArticle}
        />
        <OnboardingDialog
          isOpen={showOnboarding}
          onFinish={() => {
            setShowOnboarding(false);
            loadData();
          }}
        />
        <UpdateChecker />
        {selectedArticle ? (
          selectedArticle.book_path ? (
            <BookReader
              article={selectedArticle}
              onBack={handleBackToList}
              onUpdate={handleArticleUpdate}
            />
          ) : (
            <ArticleReader
              article={selectedArticle}
              onBack={handleBackToList}
              onNext={handleNextArticle}
              onPrev={handlePrevArticle}
              hasNext={selectedIndex < articles.length - 1}
              hasPrev={selectedIndex > 0}
              onUpdate={handleArticleUpdate}
            />
          )
        ) : showFavorites ? (
          <FavoritesPage
            onBack={handleBackFromFavorites}
            onSelectArticle={handleSelectArticle}
          />
        ) : (
          <div className="h-full max-w-4xl mx-auto p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">{t("articleList.title").replace("我的文章", "我的素材")}</h2>
              <div className="flex items-center gap-2 bg-muted/50 p-1 rounded-lg border border-border">
                <Button
                  variant={viewMode === "list" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("list")}
                  className="h-7 px-2"
                  title={t("articleList.listView")}
                >
                  <List size={14} />
                </Button>
                <Button
                  variant={viewMode === "card" ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("card")}
                  className="h-7 px-2"
                  title={t("articleList.cardView")}
                >
                  <LayoutGrid size={14} />
                </Button>
              </div>
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
              </div>
            </div>
            <ArticleList
              articles={articles}
              isLoading={isLoading}
              onSelectArticle={handleSelectArticle}
              onDelete={handleDeleteArticle}
              onEdit={handleEditArticle}
              onNewMaterial={handleCreateMaterial}
              onUpdate={handleArticleUpdate}
              selectedId={selectedId}
              viewMode={viewMode}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="px-6 py-3 border-t border-border bg-card/50 text-xs text-muted-foreground">
        <div className="flex items-center justify-between">
          <p>OpenKoto v{__APP_VERSION__}</p>
          <ApiQuickSwitcher config={config} onConfigChange={loadData} />
        </div>
      </footer>
    </div>
  );
}

export default App;
