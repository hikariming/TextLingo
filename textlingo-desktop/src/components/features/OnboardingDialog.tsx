import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Select } from "../ui/Select";
import { Input } from "../ui/Input";
import { useTheme } from "../theme-provider";
import { AppConfig, ModelConfig } from "../../lib/tauri";
import { invoke } from "@tauri-apps/api/core";
import { Palette, Sparkles, CheckCircle2, Cpu, Zap, Star, HelpCircle } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../ui/Tooltip";

interface OnboardingDialogProps {
    isOpen: boolean;
    onFinish: () => void;
}

export function OnboardingDialog({ isOpen, onFinish }: OnboardingDialogProps) {
    const { t, i18n } = useTranslation();
    const { themeName, themeMode, setThemeName, setThemeMode } = useTheme();
    const [step, setStep] = useState(1);
    const [targetLanguage, setTargetLanguage] = useState("zh-CN");
    const [apiKey, setApiKey] = useState("");
    const [selectedModel, setSelectedModel] = useState("models/gemini-3-flash-preview");
    const [isFinishing, setIsFinishing] = useState(false);
    // 用户区域选择：global = Google AI Studio, china = 302.ai / Kimi
    const [userRegion, setUserRegion] = useState<"global" | "china">("global");
    // 中国用户的服务商选择：302ai 或 moonshot (Kimi)
    const [chinaProvider, setChinaProvider] = useState<"302ai" | "moonshot">("302ai");

    const INTERFACE_LANGUAGES = [
        { value: "en", label: "English" },
        { value: "zh", label: "中文 (简体)" },
        { value: "ja", label: "日本語" },
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

    const handleLanguageChange = async (lng: string) => {
        await i18n.changeLanguage(lng);
    };

    const handleFinish = async () => {
        setIsFinishing(true);
        try {
            // 1. Create base config
            const initialConfig: AppConfig = {
                model_configs: [],
                target_language: targetLanguage,
                interface_language: i18n.language,
            };

            await invoke("save_config_cmd", { config: initialConfig });

            // 2. If API Key is provided, save the model config
            if (apiKey.trim()) {
                // 根据用户区域选择不同的服务商和模型
                let apiProvider: string;
                let modelId: string;
                let configName: string;

                if (userRegion === "global") {
                    // 全球用户使用 Google AI Studio
                    apiProvider = "google-ai-studio";
                    modelId = selectedModel;
                    configName = "Gemini";
                } else {
                    // 中国用户使用 302.ai 或 Kimi
                    apiProvider = chinaProvider;
                    if (chinaProvider === "302ai") {
                        modelId = selectedModel; // 如 gpt-4o 或 claude-3-5-sonnet
                        configName = "302.AI";
                    } else {
                        modelId = selectedModel; // 如 kimi-k2.5
                        configName = "Kimi";
                    }
                }

                const modelConfig: ModelConfig = {
                    id: crypto.randomUUID(),
                    name: configName,
                    api_key: apiKey.trim(),
                    api_provider: apiProvider,
                    model: modelId,
                    is_default: true,
                };
                await invoke("save_model_config", { config: modelConfig });
                await invoke("set_active_model_config", { configId: modelConfig.id });
            }

            onFinish();
        } catch (error) {
            console.error("Failed to save onboarding config:", error);
        } finally {
            setIsFinishing(false);
        }
    };

    return (
        <Dialog isOpen={isOpen} onClose={() => { }} /* Prevent closing by clicking outside */>
            <DialogContent className="max-w-md p-0 overflow-hidden bg-card border-none shadow-2xl">
                {/* Header Decor */}
                <div className="h-2 bg-gradient-to-r from-primary via-purple-500 to-blue-500" />

                <div className="p-8">
                    {/* Progress Indicator */}
                    <div className="flex justify-center gap-2 mb-8">
                        {[1, 2, 3].map((s) => (
                            <div
                                key={s}
                                className={`h-1.5 w-12 rounded-full transition-all duration-300 ${step >= s ? "bg-primary" : "bg-muted"
                                    }`}
                            />
                        ))}
                    </div>

                    {step === 1 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="text-center space-y-2">
                                <div className="inline-flex p-3 rounded-2xl bg-primary/10 text-primary mb-2">
                                    <Palette size={28} />
                                </div>
                                <h2 className="text-2xl font-bold tracking-tight">{t("onboarding.style.title")}</h2>
                                <p className="text-muted-foreground text-sm">{t("onboarding.style.desc")}</p>
                            </div>

                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold uppercase text-muted-foreground">{t("settings.interfaceLanguage")}</label>
                                        <Select
                                            value={i18n.language}
                                            onChange={(e) => handleLanguageChange(e.target.value)}
                                            className="h-9 text-sm"
                                        >
                                            {INTERFACE_LANGUAGES.map((lang) => (
                                                <option key={lang.value} value={lang.value}>
                                                    {lang.label}
                                                </option>
                                            ))}
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-1.5">
                                            <label className="text-xs font-semibold uppercase text-muted-foreground">{t("settings.targetLanguage")}</label>
                                            <TooltipProvider>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <HelpCircle size={12} className="text-muted-foreground hover:text-primary cursor-help" />
                                                    </TooltipTrigger>
                                                    <TooltipContent>
                                                        <p className="w-60 text-xs">{t("onboarding.style.targetLangTooltip")}</p>
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        </div>
                                        <Select
                                            value={targetLanguage}
                                            onChange={(e) => setTargetLanguage(e.target.value)}
                                            className="h-9 text-sm"
                                        >
                                            {TARGET_LANGUAGES.map((lang) => (
                                                <option key={lang.value} value={lang.value}>
                                                    {lang.label}
                                                </option>
                                            ))}
                                        </Select>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">{t("settings.theme.themeName")}</label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {["seoul", "tokyo", "california"].map((name) => (
                                            <Button
                                                key={name}
                                                variant={themeName === name ? "default" : "outline"}
                                                onClick={() => setThemeName(name as any)}
                                                size="sm"
                                                className="text-xs capitalize h-8"
                                            >
                                                {t(`settings.theme.${name}`)}
                                            </Button>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">{t("settings.theme.themeMode")}</label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {["light", "dark", "system"].map((mode) => (
                                            <Button
                                                key={mode}
                                                variant={themeMode === mode ? "default" : "outline"}
                                                onClick={() => setThemeMode(mode as any)}
                                                size="sm"
                                                className="text-xs h-8"
                                            >
                                                {t(`settings.theme.${mode}`)}
                                            </Button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                            <div className="text-center space-y-2">
                                <div className="inline-flex p-3 rounded-2xl bg-primary/10 text-primary mb-2">
                                    <Cpu size={28} />
                                </div>
                                <h2 className="text-2xl font-bold tracking-tight">{t("onboarding.model.title")}</h2>
                                <p className="text-muted-foreground text-sm">{t("onboarding.model.desc")}</p>
                            </div>

                            <div className="space-y-4">
                                {/* 区域选择器 */}
                                <div className="space-y-3">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">{t("onboarding.model.regionTitle")}</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        <button
                                            onClick={() => {
                                                setUserRegion("global");
                                                setSelectedModel("models/gemini-3-flash-preview");
                                            }}
                                            className={`flex items-center gap-2 p-3 rounded-xl border-2 transition-all ${userRegion === "global"
                                                ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                : "border-border hover:border-primary/50"
                                                }`}
                                        >
                                            <div className={`p-1.5 rounded-lg ${userRegion === "global" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                🌍
                                            </div>
                                            <div className="text-left">
                                                <div className="text-xs font-bold">{t("onboarding.model.globalUser")}</div>
                                                <div className="text-[10px] text-muted-foreground">Google AI Studio</div>
                                            </div>
                                        </button>
                                        <button
                                            onClick={() => {
                                                setUserRegion("china");
                                                setChinaProvider("302ai");
                                                setSelectedModel("gemini-3-flash-preview");
                                            }}
                                            className={`flex items-center gap-2 p-3 rounded-xl border-2 transition-all ${userRegion === "china"
                                                ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                : "border-border hover:border-primary/50"
                                                }`}
                                        >
                                            <div className={`p-1.5 rounded-lg ${userRegion === "china" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                🇨🇳
                                            </div>
                                            <div className="text-left">
                                                <div className="text-xs font-bold">{t("onboarding.model.chinaUser")}</div>
                                                <div className="text-[10px] text-muted-foreground">302.AI / Kimi</div>
                                            </div>
                                        </button>
                                    </div>
                                </div>

                                {/* 全球用户 - Google AI Studio 模型选择 */}
                                {userRegion === "global" && (
                                    <div className="space-y-3">
                                        <label className="text-xs font-semibold uppercase text-muted-foreground">{t("onboarding.model.recommendTitle")}</label>
                                        <div className="space-y-2">
                                            <button
                                                onClick={() => setSelectedModel("models/gemini-3-flash-preview")}
                                                className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${selectedModel === "models/gemini-3-flash-preview"
                                                    ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                    : "border-border hover:border-primary/50"
                                                    }`}
                                            >
                                                <div className={`p-2 rounded-lg ${selectedModel === "models/gemini-3-flash-preview" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                    <Zap size={18} />
                                                </div>
                                                <div className="text-left">
                                                    <div className="text-sm font-bold flex items-center gap-1.5">
                                                        Gemini 3.0 Flash
                                                        {selectedModel === "models/gemini-3-flash-preview" && <Star size={12} className="fill-current text-yellow-500" />}
                                                    </div>
                                                    <div className="text-[11px] text-muted-foreground leading-tight">{t("onboarding.model.recommendFlash")}</div>
                                                </div>
                                            </button>

                                            <button
                                                onClick={() => setSelectedModel("models/gemini-3-pro-preview")}
                                                className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${selectedModel === "models/gemini-3-pro-preview"
                                                    ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                    : "border-border hover:border-primary/50"
                                                    }`}
                                            >
                                                <div className={`p-2 rounded-lg ${selectedModel === "models/gemini-3-pro-preview" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                    <Cpu size={18} />
                                                </div>
                                                <div className="text-left">
                                                    <div className="text-sm font-bold">Gemini 3.0 Pro</div>
                                                    <div className="text-[11px] text-muted-foreground leading-tight">{t("onboarding.model.recommendPro")}</div>
                                                </div>
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* 中国用户 - 服务商选择 */}
                                {userRegion === "china" && (
                                    <div className="space-y-3">
                                        <label className="text-xs font-semibold uppercase text-muted-foreground">{t("onboarding.model.chinaProviderTitle")}</label>
                                        <div className="grid grid-cols-2 gap-2">
                                            <button
                                                onClick={() => {
                                                    setChinaProvider("302ai");
                                                    setSelectedModel("gemini-3-flash-preview");
                                                }}
                                                className={`flex items-center gap-2 p-3 rounded-xl border-2 transition-all ${chinaProvider === "302ai"
                                                    ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                    : "border-border hover:border-primary/50"
                                                    }`}
                                            >
                                                <div className={`p-1.5 rounded-lg ${chinaProvider === "302ai" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                    <Zap size={16} />
                                                </div>
                                                <div className="text-left">
                                                    <div className="text-xs font-bold">302.AI</div>
                                                    <div className="text-[10px] text-muted-foreground">{t("onboarding.model.302aiDesc")}</div>
                                                </div>
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setChinaProvider("moonshot");
                                                    setSelectedModel("kimi-k2.5");
                                                }}
                                                className={`flex items-center gap-2 p-3 rounded-xl border-2 transition-all ${chinaProvider === "moonshot"
                                                    ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                    : "border-border hover:border-primary/50"
                                                    }`}
                                            >
                                                <div className={`p-1.5 rounded-lg ${chinaProvider === "moonshot" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                    <Sparkles size={16} />
                                                </div>
                                                <div className="text-left">
                                                    <div className="text-xs font-bold">Kimi</div>
                                                    <div className="text-[10px] text-muted-foreground">{t("onboarding.model.kimiDesc")}</div>
                                                </div>
                                            </button>
                                        </div>

                                        {/* 302.AI 模型选择 */}
                                        {chinaProvider === "302ai" && (
                                            <div className="space-y-2">
                                                <button
                                                    onClick={() => setSelectedModel("gemini-3-flash-preview")}
                                                    className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${selectedModel === "gemini-3-flash-preview"
                                                        ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                        : "border-border hover:border-primary/50"
                                                        }`}
                                                >
                                                    <div className={`p-2 rounded-lg ${selectedModel === "gemini-3-flash-preview" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                        <Zap size={18} />
                                                    </div>
                                                    <div className="text-left">
                                                        <div className="text-sm font-bold flex items-center gap-1.5">
                                                            Gemini 3.0 Flash
                                                            {selectedModel === "gemini-3-flash-preview" && <Star size={12} className="fill-current text-yellow-500" />}
                                                        </div>
                                                        <div className="text-[11px] text-muted-foreground leading-tight">{t("onboarding.model.302ai.flash")}</div>
                                                    </div>
                                                </button>
                                                <button
                                                    onClick={() => setSelectedModel("gemini-3-pro-preview")}
                                                    className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${selectedModel === "gemini-3-pro-preview"
                                                        ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                        : "border-border hover:border-primary/50"
                                                        }`}
                                                >
                                                    <div className={`p-2 rounded-lg ${selectedModel === "gemini-3-pro-preview" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                        <Cpu size={18} />
                                                    </div>
                                                    <div className="text-left">
                                                        <div className="text-sm font-bold">Gemini 3.0 Pro</div>
                                                        <div className="text-[11px] text-muted-foreground leading-tight">{t("onboarding.model.302ai.pro")}</div>
                                                    </div>
                                                </button>
                                            </div>
                                        )}

                                        {/* Kimi 模型选择 */}
                                        {chinaProvider === "moonshot" && (
                                            <div className="space-y-2">
                                                <button
                                                    onClick={() => setSelectedModel("kimi-k2.5")}
                                                    className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${selectedModel === "kimi-k2.5"
                                                        ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                                                        : "border-border hover:border-primary/50"
                                                        }`}
                                                >
                                                    <div className={`p-2 rounded-lg ${selectedModel === "kimi-k2.5" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                                                        <Sparkles size={18} />
                                                    </div>
                                                    <div className="text-left">
                                                        <div className="text-sm font-bold flex items-center gap-1.5">
                                                            Kimi K2.5
                                                            {selectedModel === "kimi-k2.5" && <Star size={12} className="fill-current text-yellow-500" />}
                                                        </div>
                                                        <div className="text-[11px] text-muted-foreground leading-tight">{t("onboarding.model.kimi.k25")}</div>
                                                    </div>
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* API Key 输入 */}
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold uppercase text-muted-foreground">
                                        {t("onboarding.model.apiKeyLabel")} ({userRegion === "global" ? "Google AI Studio" : chinaProvider === "302ai" ? "302.AI" : "Kimi"})
                                    </label>
                                    <Input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder={t("onboarding.model.apiKeyPlaceholder")}
                                        className="h-10 text-sm font-mono"
                                    />
                                    <div className="flex flex-col gap-1">
                                        <p className="text-[10px] text-muted-foreground italic flex items-center gap-1">
                                            <Sparkles size={10} className="text-primary" />
                                            {t("onboarding.model.tip")}
                                        </p>
                                        <a
                                            href="https://www.openkoto.com/"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-[10px] text-primary/80 hover:text-primary underline decoration-dotted transition-colors self-start"
                                        >
                                            {t("onboarding.model.helpLink")}
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="space-y-6 text-center animate-in zoom-in-95 duration-500">
                            <div className="flex justify-center">
                                <div className="relative">
                                    <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
                                    <div className="relative bg-primary/10 text-primary p-5 rounded-full">
                                        <Sparkles size={48} className="animate-pulse" />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <h2 className="text-3xl font-extrabold tracking-tight text-primary">
                                    {t("onboarding.welcome.title")}
                                </h2>
                                <p className="text-lg font-medium text-foreground">
                                    {t("onboarding.welcome.celebration")}
                                </p>
                                <p className="text-muted-foreground max-w-xs mx-auto text-sm">
                                    {t("onboarding.welcome.desc")}
                                </p>
                            </div>

                            <div className="pt-4 flex justify-center">
                                <div className="flex items-center gap-2 text-green-500 bg-green-500/10 px-4 py-2 rounded-full text-xs font-semibold">
                                    <CheckCircle2 size={14} />
                                    {t("onboarding.welcome.ready")}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Footer Actions */}
                    <div className="mt-10 flex gap-3">
                        {step === 1 && (
                            <Button onClick={() => setStep(2)} className="flex-1 shadow-lg shadow-primary/10">
                                {t("onboarding.next")}
                            </Button>
                        )}
                        {step === 2 && (
                            <>
                                <Button
                                    variant="ghost"
                                    onClick={() => setStep(step - 1)}
                                    disabled={isFinishing}
                                    className="flex-1"
                                >
                                    {t("onboarding.back")}
                                </Button>
                                <Button
                                    onClick={() => setStep(3)}
                                    variant={apiKey.trim() ? "default" : "outline"}
                                    className="flex-1 shadow-lg shadow-primary/5"
                                >
                                    {apiKey.trim() ? t("onboarding.next") : t("onboarding.model.skipButton")}
                                </Button>
                            </>
                        )}
                        {step === 3 && (
                            <>
                                <Button
                                    variant="ghost"
                                    onClick={() => setStep(2)}
                                    disabled={isFinishing}
                                    className="flex-1"
                                >
                                    {t("onboarding.back")}
                                </Button>
                                <Button
                                    onClick={handleFinish}
                                    disabled={isFinishing}
                                    className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground shadow-xl shadow-primary/25 font-bold"
                                >
                                    {isFinishing ? (
                                        <div className="flex items-center justify-center gap-2 text-sm">
                                            <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary-foreground" />
                                            {t("settings.saving")}
                                        </div>
                                    ) : (
                                        t("onboarding.finish")
                                    )}
                                </Button>
                            </>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
