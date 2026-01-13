import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { ChevronDown, Check, Zap } from "lucide-react";

interface ModelConfig {
    id: string;
    name: string;
    api_provider: string;
    model: string;
}

interface AppConfig {
    active_model_id?: string;
    model_configs?: ModelConfig[];
}

interface ApiQuickSwitcherProps {
    config: AppConfig | null;
    onConfigChange: () => void;
}

export function ApiQuickSwitcher({ config, onConfigChange }: ApiQuickSwitcherProps) {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const [isSwitching, setIsSwitching] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const activeConfig = config?.model_configs?.find(c => c.id === config.active_model_id);
    const hasMultipleConfigs = (config?.model_configs?.length || 0) > 1;

    // Close dropdown on outside click
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleSwitch = async (configId: string) => {
        if (configId === config?.active_model_id) {
            setIsOpen(false);
            return;
        }

        setIsSwitching(true);
        try {
            await invoke("set_active_model_config", { configId });
            onConfigChange();
        } catch (err) {
            console.error("Failed to switch config:", err);
        } finally {
            setIsSwitching(false);
            setIsOpen(false);
        }
    };

    if (!config?.model_configs?.length) {
        return (
            <span className="text-muted-foreground">
                {t("app.notConfigured")}
            </span>
        );
    }

    // If only one config, just display it without dropdown
    if (!hasMultipleConfigs && activeConfig) {
        return (
            <div className="flex items-center gap-2 text-muted-foreground">
                <span>{t(`settings.providers.${activeConfig.api_provider}`)}</span>
                <span className="text-muted-foreground/50">/</span>
                <span className="truncate max-w-[120px]">{activeConfig.model}</span>
            </div>
        );
    }

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={isSwitching}
                className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
            >
                <Zap size={14} className="text-primary" />
                {activeConfig ? (
                    <>
                        <span className="truncate max-w-[100px]">{activeConfig.name}</span>
                        <span className="text-muted-foreground/50 hidden sm:inline">
                            ({t(`settings.providers.${activeConfig.api_provider}`)})
                        </span>
                    </>
                ) : (
                    <span>{t("footer.quickSwitch")}</span>
                )}
                <ChevronDown size={14} className={`transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>

            {isOpen && (
                <div className="absolute bottom-full right-0 mb-2 w-80 bg-popover border border-border rounded-lg shadow-lg py-1 z-50 max-h-64 overflow-y-auto">
                    <div className="px-3 py-2 text-xs font-medium text-muted-foreground border-b border-border">
                        {t("footer.quickSwitch")}
                    </div>
                    {config.model_configs.map((modelConfig) => (
                        <button
                            key={modelConfig.id}
                            onClick={() => handleSwitch(modelConfig.id)}
                            disabled={isSwitching}
                            className={`w-full px-3 py-2 text-left hover:bg-muted/50 flex items-center justify-between gap-2 transition-colors ${modelConfig.id === config.active_model_id ? "bg-primary/10" : ""
                                }`}
                        >
                            <div className="flex-1 min-w-0">
                                <div className="font-medium text-sm truncate">{modelConfig.name}</div>
                                <div className="text-xs text-muted-foreground break-all">
                                    {t(`settings.providers.${modelConfig.api_provider}`)} / {modelConfig.model}
                                </div>
                            </div>
                            {modelConfig.id === config.active_model_id && (
                                <Check size={16} className="text-primary shrink-0" />
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
