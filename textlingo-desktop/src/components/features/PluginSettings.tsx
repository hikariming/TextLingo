import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Loader2, Download, AlertTriangle, Terminal, Package, RefreshCw, FolderOpen, Cog } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from "../ui/Button";

interface PluginMetadata {
    name: string;
    display_name: string;
    version: string;
    description: string;
    release_repo: string;
}

interface PluginInfo {
    metadata: PluginMetadata;
    path: string;
    active_mode: 'Dev' | 'Prod';
    installed: boolean;
}

// Default known plugins
const KNOWN_PLUGINS: PluginMetadata[] = [
    {
        name: "openkoto-pdf-translator",
        display_name: "PDF Translator",
        version: "0.1.0",
        description: "PDF Translation Plugin for OpenKoto",
        release_repo: "hikariming/TextLingo"
    }
];

export function PluginSettings() {
    const { t } = useTranslation();
    const [plugins, setPlugins] = useState<PluginInfo[]>([]);
    const [pluginModes, setPluginModes] = useState<Record<string, 'Dev' | 'Prod'>>({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isDevEnv, setIsDevEnv] = useState(false);

    useEffect(() => {
        setIsDevEnv(import.meta.env.DEV);
        fetchPlugins();
    }, []);

    const fetchPlugins = async () => {
        setLoading(true);
        try {
            // Fetch detected plugins AND mode configuration in parallel
            const [list, modes] = await Promise.all([
                invoke<PluginInfo[]>('list_plugins_cmd'),
                invoke<Record<string, 'Dev' | 'Prod'>>('get_plugin_modes_cmd')
            ]);

            setPlugins(list);
            setPluginModes(modes);
            setError(null);
        } catch (err) {
            console.error('Failed to list plugins:', err);
            setError(t('settings.plugins.noPlugins'));
        } finally {
            setLoading(false);
        }
    };

    const handleModeToggle = async (pluginName: string, mode: 'Dev' | 'Prod') => {
        try {
            // Optimistic update
            setPluginModes(prev => ({
                ...prev,
                [pluginName]: mode
            }));

            await invoke('set_plugin_mode_cmd', { pluginName, mode: mode.toLowerCase() });
            // No need to fetchPlugins fully if we trust the optimistic update, 
            // but fetching ensures sync with backend state.
            // await fetchPlugins(); 
        } catch (err) {
            console.error('Failed to set plugin mode:', err);
            // Revert on error
            fetchPlugins();
        }
    };

    const handleOpenPluginsFolder = async () => {
        try {
            await invoke('open_plugins_directory');
        } catch (err) {
            console.error('Failed to open plugins directory:', err);
        }
    };

    // Merge detected plugins with known defaults
    const displayPlugins = KNOWN_PLUGINS.map(known => {
        const detected = plugins.find(p => p.metadata.name === known.name);

        // Use the explicitly configured mode if available, otherwise fallback to detected active_mode or 'Prod'
        const configuredMode = pluginModes[known.name] || (detected ? detected.active_mode : 'Prod');

        if (detected) {
            return {
                ...detected,
                active_mode: configuredMode
            };
        }

        return {
            metadata: known,
            path: "",
            active_mode: configuredMode, // Now this persists even if not installed!
            installed: false
        };
    }).concat(plugins.filter(p => !KNOWN_PLUGINS.some(k => k.name === p.metadata.name)).map(p => ({
        ...p,
        active_mode: pluginModes[p.metadata.name] || p.active_mode
    })));

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center bg-secondary/30 p-2.5 rounded-lg border border-border/50">
                <span className="text-sm font-medium px-2 flex items-center gap-2">
                    <Cog size={16} className="text-muted-foreground" />
                    {t('settings.plugins.title')}
                </span>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={handleOpenPluginsFolder}
                        className="h-8 text-xs gap-2 bg-background shadow-sm hover:translate-y-[-1px] transition-transform"
                    >
                        <FolderOpen size={14} className="text-blue-500" />
                        {t('settings.plugins.location')}
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => fetchPlugins()}
                        className="h-8 w-8 p-0"
                        title={t('settings.plugins.refresh')}
                        disabled={loading}
                    >
                        <RefreshCw size={14} className={loading ? "animate-spin text-primary" : "text-muted-foreground"} />
                    </Button>
                </div>
            </div>

            {error && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-md flex items-center mb-4 text-sm animate-in fade-in slide-in-from-top-1">
                    <AlertTriangle className="mr-2 shrink-0" size={16} />
                    {error}
                </div>
            )}

            {/* Dev Environment Hint */}
            {isDevEnv && plugins.some(p => p.active_mode === 'Prod') && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-md p-3 text-sm text-yellow-700 dark:text-yellow-400 flex flex-col gap-2">
                    <div className="flex items-start gap-2">
                        <AlertTriangle size={16} className="mt-0.5 shrink-0" />
                        <div className="flex-1">
                            <p className="font-medium">{t('settings.plugins.devEnvDetected')}</p>
                            <p className="opacity-90 leading-snug mt-1">{t('settings.plugins.devEnvTip')}</p>
                        </div>
                    </div>
                </div>
            )}

            <div className="space-y-4">
                {displayPlugins.map((plugin) => (
                    <div
                        key={plugin.metadata.name}
                        className={`group border border-border rounded-xl bg-card transition-all ${!plugin.installed ? 'opacity-90 border-dashed bg-muted/20' : 'hover:border-primary/50 shadow-sm'}`}
                    >
                        <div className="p-4">
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <h3 className="text-base font-semibold flex items-center gap-2 text-foreground">
                                        {plugin.metadata.display_name}
                                        {plugin.installed ? (
                                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                                                v{plugin.metadata.version}
                                            </span>
                                        ) : (
                                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                                                {t('settings.plugins.notInstalled')}
                                            </span>
                                        )}
                                    </h3>
                                    <p className="text-xs text-muted-foreground mt-1 max-w-sm leading-relaxed">
                                        {plugin.metadata.description}
                                    </p>
                                </div>
                                {plugin.metadata.release_repo && (
                                    <a
                                        href={`https://github.com/${plugin.metadata.release_repo}/releases`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-xs text-primary bg-primary/5 px-2 py-1 rounded-md hover:bg-primary/10 transition-colors flex items-center gap-1.5"
                                    >
                                        <Download size={13} />
                                        {t('settings.plugins.checkUpdates')}
                                    </a>
                                )}
                            </div>

                            {/* Always show Mode Switcher */}
                            <div className="mt-4 pb-4 border-b border-border/50">
                                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                                    <div className="flex items-center gap-4">
                                        <span className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
                                            {t('settings.plugins.activeMode')}
                                        </span>
                                        <div className="relative inline-flex bg-muted p-1 rounded-lg border border-border/50 shadow-inner">
                                            <div
                                                className={`absolute top-1 bottom-1 w-[calc(50%-4px)] bg-background rounded-md shadow-sm transition-all duration-300 ease-spring ${plugin.active_mode === 'Prod' ? 'left-1' : 'left-[calc(50%+0px)]'}`}
                                            />
                                            <button
                                                onClick={() => handleModeToggle(plugin.metadata.name, 'Prod')}
                                                className={`relative z-10 flex items-center justify-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors w-20 ${plugin.active_mode === 'Prod' ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                                            >
                                                <Package size={13} />
                                                User
                                            </button>
                                            <button
                                                onClick={() => handleModeToggle(plugin.metadata.name, 'Dev')}
                                                className={`relative z-10 flex items-center justify-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors w-20 ${plugin.active_mode === 'Dev' ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground hover:text-foreground'}`}
                                            >
                                                <Terminal size={13} />
                                                Dev
                                            </button>
                                        </div>
                                    </div>
                                    <div className="text-[10px] text-muted-foreground text-right max-w-xs transition-opacity duration-300">
                                        {plugin.active_mode === 'Dev'
                                            ? t('settings.plugins.devModeWarning')
                                            : t('settings.plugins.userModeWarning')}
                                    </div>
                                </div>
                            </div>

                            {plugin.installed ? (
                                <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                                    <div className="flex-1">
                                        <span className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mb-1 block">
                                            {t('settings.plugins.location')}
                                        </span>
                                        <div className="flex">
                                            <code className="text-[10px] inline-block bg-muted/30 px-2.5 py-1.5 rounded-md border border-border/30 text-muted-foreground break-all max-w-full hover:bg-muted/50 transition-colors cursor-copy select-all" title={plugin.path}>
                                                {plugin.path}
                                            </code>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="mt-4 p-4 bg-muted/30 rounded-lg border border-border/40 flex flex-col sm:flex-row items-center justify-between gap-4">
                                    <div className="text-sm text-muted-foreground flex items-center gap-2">
                                        <AlertTriangle size={14} className="text-amber-500" />
                                        {t("settings.plugins.notInstalledDesc")}
                                    </div>
                                    <div className="flex items-center gap-2 w-full sm:w-auto">
                                        <Button
                                            size="sm"
                                            variant="default"
                                            onClick={() => window.open(`https://github.com/${plugin.metadata.release_repo}/releases`, '_blank')}
                                            className="flex-1 sm:flex-none gap-2 bg-primary hover:bg-primary/90"
                                        >
                                            <Download size={14} />
                                            {t("settings.plugins.download")}
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
