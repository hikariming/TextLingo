import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent, DialogFooter } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Settings, Plus, Trash2, Edit2, Check, RefreshCw, Loader2 } from "lucide-react";
import { useTheme } from "../theme-provider";

interface ModelConfig {
  id: string;
  name: string;
  api_key: string;
  api_provider: string;
  model: string;
  is_default: boolean;
  created_at?: string;
  base_url?: string;
}

interface AppConfig {
  active_model_id?: string;
  model_configs: ModelConfig[];
  target_language: string;
  interface_language: string;
  backend_url?: string;
  auth_token?: string;
}

interface OpenRouterModel {
  id: string;
  name: string;
  description?: string;
  context_length?: number;
  pricing?: {
    prompt?: number;
    completion?: number;
  };
}

const SUPPORTED_PROVIDERS = ["openai", "openrouter", "deepseek", "siliconflow", "302ai", "google", "google-ai-studio", "openai-compatible", "ollama", "lmstudio"] as const;

// Default base URLs for local providers
const DEFAULT_BASE_URLS: Record<string, string> = {
  "ollama": "http://localhost:11434/v1",
  "lmstudio": "http://localhost:1234/v1",
};

// Default preset models
const DEFAULT_MODELS = {
  openai: [
    { value: "gpt-4o", labelKey: "settings.models.openai.gpt-4o" },
    { value: "gpt-4o-mini", labelKey: "settings.models.openai.gpt-4o-mini" },
    { value: "gpt-4-turbo", labelKey: "settings.models.openai.gpt-4-turbo" },
    { value: "gpt-3.5-turbo", labelKey: "settings.models.openai.gpt-3.5-turbo" },
  ],
  openrouter: [
    { value: "openai/gpt-4o", labelKey: "settings.models.openrouter.openai/gpt-4o" },
    { value: "openai/gpt-4o-mini", labelKey: "settings.models.openrouter.openai/gpt-4o-mini" },
    { value: "anthropic/claude-3-haiku", labelKey: "settings.models.openrouter.anthropic/claude-3-haiku" },
    { value: "google/gemini-pro-1.5", labelKey: "settings.models.openrouter.google/gemini-pro-1.5" },
  ],
  deepseek: [
    { value: "deepseek-chat", labelKey: "settings.models.deepseek.deepseek-chat" },
    { value: "deepseek-coder", labelKey: "settings.models.deepseek.deepseek-coder" },
  ],
  siliconflow: [
    { value: "deepseek-ai/DeepSeek-V3", labelKey: "settings.models.siliconflow.deepseek-v3" },
    { value: "deepseek-ai/DeepSeek-R1", labelKey: "settings.models.siliconflow.deepseek-r1" },
  ],
  "302ai": [
    { value: "gpt-4o", labelKey: "settings.models.302ai.gpt-4o" },
    { value: "claude-3-5-sonnet-20241022", labelKey: "settings.models.302ai.claude-3-5-sonnet" },
  ],
  google: [
    { value: "gemini-2.0-flash-exp", labelKey: "settings.models.google.gemini-2.0-flash-exp" },
    { value: "gemini-1.5-pro", labelKey: "settings.models.google.gemini-1.5-pro" },
    { value: "gemini-1.5-flash", labelKey: "settings.models.google.gemini-1.5-flash" },
  ],
  "google-ai-studio": [
    { value: "gemini-2.0-flash-exp", labelKey: "settings.models.google-ai-studio.gemini-2.0-flash-exp" },
    { value: "models/gemini-3-flash-preview", labelKey: "settings.models.google-ai-studio.gemini-3-flash-preview" },
    { value: "models/gemini-3-pro-preview", labelKey: "settings.models.google-ai-studio.gemini-3-pro-preview" },
    { value: "gemini-1.5-pro", labelKey: "settings.models.google-ai-studio.gemini-1.5-pro" },
    { value: "gemini-1.5-flash", labelKey: "settings.models.google-ai-studio.gemini-1.5-flash" },
  ],
  // Providers that require custom model input
  "openai-compatible": [],
  "ollama": [],
  "lmstudio": [],
};

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: () => void;
}

export function SettingsDialog({ isOpen, onClose, onSave }: SettingsDialogProps) {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useTheme();
  const [config, setConfig] = useState<AppConfig>({
    model_configs: [],
    target_language: "zh-CN",
    interface_language: i18n.language,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Model config form state
  const [editingConfig, setEditingConfig] = useState<Partial<ModelConfig> | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [customModelInput, setCustomModelInput] = useState("");
  const [isSyncingModels, setIsSyncingModels] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [dynamicModels, setDynamicModels] = useState<Record<string, { value: string; label: string }[]>>({
    openai: DEFAULT_MODELS.openai.map(m => ({ value: m.value, label: t(m.labelKey) })),
    openrouter: DEFAULT_MODELS.openrouter.map(m => ({ value: m.value, label: t(m.labelKey) })),
    deepseek: DEFAULT_MODELS.deepseek.map(m => ({ value: m.value, label: t(m.labelKey) })),
    siliconflow: DEFAULT_MODELS.siliconflow.map(m => ({ value: m.value, label: t(m.labelKey) })),
    "302ai": DEFAULT_MODELS["302ai"].map(m => ({ value: m.value, label: t(m.labelKey) })),
    google: DEFAULT_MODELS.google.map(m => ({ value: m.value, label: t(m.labelKey) })),
    "google-ai-studio": DEFAULT_MODELS["google-ai-studio"].map(m => ({ value: m.value, label: t(m.labelKey) })),
  });
  const [modelFilter, setModelFilter] = useState("");

  // Load config on mount
  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await invoke<AppConfig | null>("get_config");
      if (result) {
        setConfig(result);
        // Restore interface language from config or use current
        const savedLang = result.interface_language || i18n.language;
        if (savedLang !== i18n.language) {
          await i18n.changeLanguage(savedLang);
        }
      }
    } catch (err) {
      setError(err as string);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewConfig = () => {
    setEditingConfig({
      id: crypto.randomUUID(),
      name: "",
      api_key: "",
      api_provider: "openai",
      model: "gpt-4o-mini",
      is_default: config.model_configs.length === 0,
    });
    setIsEditing(true);
    setUseCustomModel(false);
    setCustomModelInput("");
    setSyncError(null);
  };

  const startEditConfig = (modelConfig: ModelConfig) => {
    setEditingConfig(modelConfig);
    setIsEditing(true);
    // Check if current model is a custom model
    const providerModels = dynamicModels[modelConfig.api_provider];
    const isCustom = !providerModels?.some(m => m.value === modelConfig.model);
    setUseCustomModel(isCustom);
    if (isCustom) {
      setCustomModelInput(modelConfig.model);
    }
    setSyncError(null);
  };

  const cancelEdit = () => {
    setEditingConfig(null);
    setIsEditing(false);
    setUseCustomModel(false);
    setCustomModelInput("");
    setSyncError(null);
  };

  const saveConfig = async () => {
    if (!editingConfig) return;

    if (!editingConfig.name?.trim()) {
      setError(t("settings.errors.configNameRequired"));
      return;
    }
    // API key is optional for local providers (ollama, lmstudio)
    const isLocalProvider = ["ollama", "lmstudio"].includes(editingConfig.api_provider || "");
    if (!isLocalProvider && !editingConfig.api_key?.trim()) {
      setError(t("settings.errors.apiKeyRequired"));
      return;
    }
    if (!useCustomModel && !editingConfig.model) {
      setError(t("settings.errors.modelRequired"));
      return;
    }
    if (useCustomModel && !customModelInput.trim()) {
      setError(t("settings.errors.modelRequired"));
      return;
    }

    const modelToUse = useCustomModel ? customModelInput.trim() : editingConfig.model!;

    const configToSave: ModelConfig = {
      id: editingConfig.id || crypto.randomUUID(),
      name: editingConfig.name.trim(),
      api_key: (editingConfig.api_key || "").trim(),
      api_provider: editingConfig.api_provider || "openai",
      model: modelToUse,
      is_default: editingConfig.is_default || false,
      base_url: editingConfig.base_url?.trim() || undefined,
    };

    setIsSaving(true);
    setError(null);
    try {
      const saved = await invoke<ModelConfig>("save_model_config", { config: configToSave });

      // Update local state
      const existingIndex = config.model_configs.findIndex(c => c.id === saved.id);
      if (existingIndex >= 0) {
        const newConfigs = [...config.model_configs];
        newConfigs[existingIndex] = saved;
        setConfig({ ...config, model_configs: newConfigs });
      } else {
        setConfig({ ...config, model_configs: [...config.model_configs, saved] });
      }

      onSave?.();
      cancelEdit();
    } catch (err) {
      setError(err as string);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteConfig = async (configId: string) => {
    if (config.model_configs.length <= 1) {
      setError(t("settings.errors.cannotDeleteLastConfig"));
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      await invoke("delete_model_config", { configId });
      setConfig({
        ...config,
        model_configs: config.model_configs.filter(c => c.id !== configId),
      });
    } catch (err) {
      setError(err as string);
    } finally {
      setIsSaving(false);
    }
  };

  const setActiveConfig = async (configId: string) => {
    setIsSaving(true);
    setError(null);
    try {
      const active = await invoke<ModelConfig>("set_active_model_config", { configId });
      setConfig({ ...config, active_model_id: active.id });
    } catch (err) {
      setError(err as string);
    } finally {
      setIsSaving(false);
    }
  };

  /* Removed unused handleProviderChange */

  const handleInterfaceLanguageChange = async (lng: string) => {
    setConfig({ ...config, interface_language: lng });
    await i18n.changeLanguage(lng);
  };

  const syncModels = async (isAuto = false) => {
    if (!editingConfig) return;

    const provider = editingConfig.api_provider;
    // Ensure provider is defined and valid
    if (!provider || !["openrouter", "openai", "openai-compatible", "deepseek", "siliconflow", "302ai", "google"].includes(provider)) {
      if (!isAuto) setSyncError(t("settings.syncErrors.providerNotSupported") || "Provider not supported for sync");
      return;
    }

    if (!editingConfig.api_key?.trim()) {
      if (!isAuto) setSyncError(t("settings.syncErrors.apiKeyRequired"));
      return;
    }

    setIsSyncingModels(true);
    setSyncError(null);
    try {
      let url = "";
      let headers: Record<string, string> = {};

      if (provider === "openrouter") {
        url = "https://openrouter.ai/api/v1/models";
        headers = {
          "Authorization": `Bearer ${editingConfig.api_key}`,
          "Content-Type": "application/json",
        };
      } else if (provider === "openai" || provider === "openai-compatible") {
        if (editingConfig.base_url) {
          const baseUrl = editingConfig.base_url.replace(/\/$/, "");
          url = baseUrl.endsWith("/models") ? baseUrl : `${baseUrl}/models`;
        } else {
          url = "https://api.openai.com/v1/models";
        }
        headers = {
          "Authorization": `Bearer ${editingConfig.api_key}`,
          "Content-Type": "application/json",
        };
      } else if (provider === "deepseek") {
        url = "https://api.deepseek.com/models";
        headers = {
          "Authorization": `Bearer ${editingConfig.api_key}`,
          "Content-Type": "application/json",
        };
      } else if (provider === "siliconflow") {
        // Add sub_type=chat to filter if possible, otherwise list all.
        // Docs say querying by sub_type is supported? "You can use it to filter models individually without setting type."
        url = "https://api.siliconflow.cn/v1/models?sub_type=chat";
        headers = {
          "Authorization": `Bearer ${editingConfig.api_key}`,
          "Content-Type": "application/json",
        };
      } else if (provider === "302ai") {
        // 302.ai params from user: ?llm=1&include_custom_models=1
        url = "https://api.302.ai/v1/models?llm=1&include_custom_models=1";
        headers = {
          "Authorization": `Bearer ${editingConfig.api_key}`,
          "Content-Type": "application/json",
        };
      } else if (provider === "google" || provider === "google-ai-studio") {
        url = `https://generativelanguage.googleapis.com/v1beta/models?key=${editingConfig.api_key}`;
        // Google API key is in URL, no auth header needed for this endpoint usually,
        headers = {
          "Content-Type": "application/json",
        };
      }

      const response = await fetch(url, { method: "GET", headers });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      let syncedModels: { value: string; label: string }[] = [];

      if (provider === "openrouter") {
        if (data.data && Array.isArray(data.data)) {
          syncedModels = data.data
            .filter((m: OpenRouterModel) => !m.id.includes(":free"))
            .slice(0, 100)
            .map((m: OpenRouterModel) => ({
              value: m.id,
              label: m.name || m.id,
            }));
        }
      } else if (provider === "openai" || provider === "openai-compatible") {
        if (data.data && Array.isArray(data.data)) {
          syncedModels = data.data
            .filter((m: any) => provider === "openai-compatible" || m.id.includes("gpt") || m.id.includes("o1"))
            .map((m: any) => ({
              value: m.id,
              label: m.id,
            }))
            .sort((a: { value: string }, b: { value: string }) => b.value.localeCompare(a.value));
        }
      } else if (provider === "deepseek") {
        if (data.data && Array.isArray(data.data)) {
          syncedModels = data.data
            .map((m: any) => ({
              value: m.id,
              label: m.id,
            }));
        }
      } else if (provider === "siliconflow") {
        if (data.data && Array.isArray(data.data)) {
          // SiliconFlow format: { data: [{ id: "...", ... }] }
          syncedModels = data.data
            .map((m: any) => ({
              value: m.id,
              label: m.id,
            }));
        }
      } else if (provider === "302ai") {
        if (data.data && Array.isArray(data.data)) {
          // 302.ai format: { data: [{ id: "...", ... }] }
          syncedModels = data.data
            .map((m: any) => ({
              value: m.id,
              label: m.id,
            }));
        }
      } else if (provider === "google") {
        // Google returns { models: [...] }
        if (data.models && Array.isArray(data.models)) {
          syncedModels = data.models
            .map((m: any) => ({
              // Google model names are like "models/gemini-1.5-flash"
              // We usually want just "gemini-1.5-flash" for the value if the client handles the prefix,
              // BUT check how types.rs/ai_service.rs handles it.
              // Usually the user inputs just the model name. Let's strip "models/" if present.
              value: m.name.replace("models/", ""),
              label: m.displayName || m.name.replace("models/", ""),
            }))
            .filter((m: { value: string }) => m.value.includes("gemini"));
        }
      }

      if (syncedModels.length > 0) {
        if (provider) {
          setDynamicModels((prev) => ({
            ...prev,
            [provider]: syncedModels,
          }));
        }

        // If current model is not in list (e.g. initial setup), potentially select first one?
        // Let's NOT auto-select to avoid overwriting user choice unless it's empty.
        if (!editingConfig.model && syncedModels.length > 0) {
          setEditingConfig(prev => ({ ...prev, model: syncedModels[0].value }));
        }
      }

    } catch (err) {
      if (!isAuto) {
        setSyncError(`${t("settings.syncErrors.syncFailed")}: ${err}`);
      }
      console.error("Model sync failed:", err);
    } finally {
      setIsSyncingModels(false);
    }
  };

  const availableModels = (editingConfig?.api_provider
    ? dynamicModels[editingConfig.api_provider] || []
    : []).filter(model => {
      if (!modelFilter) return true;
      try {
        const regex = new RegExp(modelFilter, "i");
        return regex.test(model.value) || regex.test(model.label);
      } catch (e) {
        // Fallback to simple includes if regex is invalid
        const lowerFilter = modelFilter.toLowerCase();
        return model.value.toLowerCase().includes(lowerFilter) ||
          model.label.toLowerCase().includes(lowerFilter);
      }
    });

  // Auto-sync when provider changes (if key exists)
  useEffect(() => {
    if (editingConfig?.api_provider && editingConfig?.api_key) {
      // Debounce or just run? React effects run after render, so state is updated.
      // We only want to run this when provider changes explicitly? 
      // Actually, handleProviderChange updates state. We can trigger it there, 
      // OR here. If here, need to be careful about infinite loops or running on every keystroke.
      // Better to just trigger in handleProviderChange and onBlur.
    }
  }, []); // Keep empty, we handle triggers manually to avoid excessive calls

  const handleDisplayProviderChange = (provider: string) => {
    const models = dynamicModels[provider];

    // Preserve API Key if switching between compatible providers? 
    // Usually NO, keys are provider specific.
    // However, we need to clear key if it's a new provider to avoid confusion?
    // Current logic preserves key in state but maybe it shouldn't.
    // The user asks for auto sync.

    // Check if we have a key for this provider stored previously? 
    // No, existing logic edits a config object. 

    setEditingConfig((prev) => {
      const newConfig = {
        ...prev,
        api_provider: provider,
        model: models?.[0]?.value || "",
        // For local providers, set default base URL
        base_url: DEFAULT_BASE_URLS[provider] || prev?.base_url || undefined,
      };

      return newConfig;
    });
    // For providers without preset models, enable custom model input
    const needsCustomModel = ["openai-compatible", "ollama", "lmstudio"].includes(provider);
    setUseCustomModel(needsCustomModel);
  };

  const INTERFACE_LANGUAGES = [
    { value: "en", label: t("settings.interfaceLanguages.en") },
    { value: "zh", label: t("settings.interfaceLanguages.zh") },
    { value: "ja", label: t("settings.interfaceLanguages.ja") },
  ];

  const TARGET_LANGUAGES = [
    { value: "en", label: t("settings.languages.en") },
    { value: "zh-CN", label: t("settings.languages.zh-CN") },
    { value: "zh-TW", label: t("settings.languages.zh-TW") },
    { value: "ja", label: t("settings.languages.ja") },
    { value: "ko", label: t("settings.languages.ko") },
    { value: "es", label: t("settings.languages.es") },
    { value: "fr", label: t("settings.languages.fr") },
    { value: "de", label: t("settings.languages.de") },
    { value: "ru", label: t("settings.languages.ru") },
    { value: "ar", label: t("settings.languages.ar") },
  ];

  if (isLoading) {
    return (
      <Dialog isOpen={isOpen} onClose={onClose}>
        <DialogContent className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={t("settings.title")}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        {error && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/50 rounded-lg text-destructive text-sm">
            {error}
          </div>
        )}

        <div className="space-y-6">
          {/* Model Configurations Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-medium text-foreground">
                {t("settings.modelConfigs")}
              </h3>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={startNewConfig}
                disabled={isEditing}
                className="gap-1"
              >
                <Plus size={14} />
                {t("settings.addConfig")}
              </Button>
            </div>

            {/* Config List */}
            <div className="space-y-2 mb-4">
              {config.model_configs.length === 0 ? (
                <div className="text-center py-8 text-gray-500 border border-dashed border-gray-700 rounded-lg">
                  {t("settings.noConfigs")}
                </div>
              ) : (
                config.model_configs.map((modelConfig) => (
                  <div
                    key={modelConfig.id}
                    className={`p-3 rounded-lg border flex items-center justify-between gap-3 ${config.active_model_id === modelConfig.id
                      ? "bg-primary/10 border-primary"
                      : "bg-card border-border"
                      }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground truncate">
                          {modelConfig.name}
                        </span>
                        {config.active_model_id === modelConfig.id && (
                          <span className="text-xs px-1.5 py-0.5 bg-primary text-primary-foreground rounded">
                            {t("settings.active")}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {t(`settings.providers.${modelConfig.api_provider}`)} / {modelConfig.model}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {config.active_model_id !== modelConfig.id && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => setActiveConfig(modelConfig.id)}
                          disabled={isSaving}
                          title={t("settings.setAsActive")}
                          className="h-7 w-7 p-0"
                        >
                          <Check size={14} />
                        </Button>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => startEditConfig(modelConfig)}
                        disabled={isEditing || isSaving}
                        title={t("settings.editConfig")}
                        className="h-7 w-7 p-0"
                      >
                        <Edit2 size={14} />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteConfig(modelConfig.id)}
                        disabled={isEditing || isSaving}
                        title={t("settings.deleteConfig")}
                        className="h-7 w-7 p-0 text-destructive hover:text-destructive/80"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Edit Form */}
            {isEditing && editingConfig && (
              <div className="p-4 bg-muted/50 rounded-lg border border-border space-y-4">
                <h4 className="font-medium text-foreground">
                  {editingConfig.id && config.model_configs.some(c => c.id === editingConfig.id)
                    ? t("settings.editConfig")
                    : t("settings.newConfig")}
                </h4>

                {/* Config Name */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {t("settings.configName")}
                  </label>
                  <Input
                    type="text"
                    value={editingConfig.name || ""}
                    onChange={(e) => setEditingConfig({ ...editingConfig, name: e.target.value })}
                    placeholder={t("settings.configNamePlaceholder")}
                  />
                </div>

                {/* Provider */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {t("settings.apiProvider")}
                  </label>
                  <Select
                    value={editingConfig.api_provider || "openai"}
                    onChange={(e) => handleDisplayProviderChange(e.target.value)}
                  >
                    {SUPPORTED_PROVIDERS.map((provider) => (
                      <option key={provider} value={provider}>
                        {t(`settings.providers.${provider}`)}
                      </option>
                    ))}
                  </Select>
                </div>

                {/* Base URL - show for openai-compatible, ollama, lmstudio */}
                {["openai", "openai-compatible", "ollama", "lmstudio"].includes(editingConfig.api_provider || "") && (
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      {t("settings.baseUrl")}
                    </label>
                    <Input
                      type="text"
                      value={editingConfig.base_url || ""}
                      onChange={(e) => setEditingConfig({ ...editingConfig, base_url: e.target.value })}
                      placeholder={t("settings.baseUrlPlaceholder")}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {t("settings.baseUrlHelp")}
                    </p>
                  </div>
                )}

                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {["ollama", "lmstudio"].includes(editingConfig.api_provider || "")
                      ? t("settings.apiKeyOptional")
                      : t("settings.apiKey")}
                  </label>
                  <Input
                    type="password"
                    value={editingConfig.api_key || ""}
                    onChange={(e) => setEditingConfig({ ...editingConfig, api_key: e.target.value })}
                    onBlur={() => syncModels(true)}
                    placeholder={t("settings.apiKeyPlaceholder")}
                  />
                </div>

                {/* Model */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-foreground">
                      {t("settings.model")}
                    </label>
                    {["openrouter", "openai", "deepseek", "google", "google-ai-studio", "302ai", "siliconflow"].includes(editingConfig.api_provider || "") && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => syncModels(false)}
                        disabled={isSyncingModels || !editingConfig.api_key}
                        className="h-6 px-2 text-xs"
                        title={t("settings.syncModelsTooltip")}
                      >
                        <RefreshCw size={12} className={isSyncingModels ? "animate-spin" : ""} />
                        {isSyncingModels ? t("settings.syncing") : t("settings.syncModels")}
                      </Button>
                    )}
                  </div>
                  {!useCustomModel && (
                    <div className="mb-2">
                      <Input
                        type="text"
                        value={modelFilter}
                        onChange={(e) => setModelFilter(e.target.value)}
                        placeholder={t("settings.modelFilterPlaceholder")}
                        className="h-8 text-xs"
                      />
                    </div>
                  )}
                  {!useCustomModel ? (
                    <Select
                      value={editingConfig.model || ""}
                      onChange={(e) => {
                        if (e.target.value === "__custom__") {
                          setUseCustomModel(true);
                        } else {
                          setEditingConfig({ ...editingConfig, model: e.target.value });
                        }
                      }}
                    >
                      {availableModels.map((model) => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                      <option value="__custom__">{t("settings.customModel")}</option>
                    </Select>
                  ) : (
                    <div className="space-y-2">
                      <Input
                        type="text"
                        value={customModelInput}
                        onChange={(e) => setCustomModelInput(e.target.value)}
                        placeholder={t("settings.customModelPlaceholder")}
                        className="w-full"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setUseCustomModel(false)}
                        className="h-6 px-2 text-xs"
                      >
                        {t("settings.usePresetModel")}
                      </Button>
                    </div>
                  )}
                  {syncError && (
                    <div className="mt-2 text-xs text-yellow-400">
                      {syncError}
                    </div>
                  )}
                </div>

                {/* Form Actions */}
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={cancelEdit}
                    disabled={isSaving}
                  >
                    {t("settings.cancel")}
                  </Button>
                  <Button
                    type="button"
                    onClick={saveConfig}
                    disabled={isSaving}
                  >
                    {isSaving ? (
                      <>
                        <Loader2 size={14} className="animate-spin mr-1" />
                        {t("settings.saving")}
                      </>
                    ) : (
                      t("settings.saveConfig")
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Other Settings */}
          <div className="border-t border-border pt-4 space-y-4">

            {/* Theme */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t("Theme")}
              </label>
              <Select
                value={theme}
                onChange={(e) => setTheme(e.target.value as any)}
              >
                <option value="light">{t("settings.theme.light")}</option>
                <option value="dark">{t("settings.theme.dark")}</option>
                <option value="eye-protection">{t("settings.theme.eyeProtection")}</option>
                <option value="system">{t("settings.theme.system")}</option>
              </Select>
            </div>


            {/* Interface Language */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t("settings.interfaceLanguage")}
              </label>
              <Select
                value={config.interface_language}
                onChange={(e) => handleInterfaceLanguageChange(e.target.value)}
              >
                {INTERFACE_LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </Select>
            </div>

            {/* Target Language */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t("settings.targetLanguage")}
              </label>
              <Select
                value={config.target_language}
                onChange={(e) => setConfig({ ...config, target_language: e.target.value })}
              >
                {TARGET_LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </div>
      </DialogContent>

      <DialogFooter>
        <Button variant="secondary" onClick={async () => {
          // Save backend config before closing
          setIsSaving(true);
          try {
            await invoke("save_config_cmd", { config });
            onSave?.();
          } catch (err) {
            setError(err as string);
          } finally {
            setIsSaving(false);
          }
          onClose();
        }} disabled={isSaving}>
          {isSaving ? t("settings.saving") : t("settings.close")}
        </Button>
      </DialogFooter>
    </Dialog >
  );
}

interface SettingsButtonProps {
  onOpen?: () => void;
  onSave?: () => void;
}

export function SettingsButton({ onOpen, onSave }: SettingsButtonProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const handleOpen = () => {
    onOpen?.();
    setIsOpen(true);
  };

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleOpen}
        className="gap-2 text-foreground"
      >
        <Settings size={16} />
        {t("header.settings")}
      </Button>
      <SettingsDialog
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onSave={onSave}
      />
    </>
  );
}
