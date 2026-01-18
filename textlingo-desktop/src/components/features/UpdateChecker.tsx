import { useState, useEffect } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { useTranslation } from "react-i18next";
import { Bell, X, ExternalLink } from "lucide-react";
import { getVersion } from "@tauri-apps/api/app";

interface GitHubRelease {
    tag_name: string;
    html_url: string;
    name: string;
    body: string;
}

export function UpdateChecker() {
    const { t } = useTranslation();
    const [updateAvailable, setUpdateAvailable] = useState<GitHubRelease | null>(null);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const checkUpdate = async () => {
            try {
                // Get current app version
                const version = await getVersion();

                // Fetch latest release from GitHub
                const response = await fetch("https://api.github.com/repos/hikariming/openkoto/releases/latest");
                if (!response.ok) return;

                const data: GitHubRelease = await response.json();
                const latestVersion = data.tag_name.replace(/^v/, "");

                if (compareVersions(latestVersion, version) > 0) {
                    setUpdateAvailable(data);
                    setIsVisible(true);
                }
            } catch (error) {
                console.error("Failed to check for updates:", error);
            }
        };

        checkUpdate();
    }, []);

    const compareVersions = (v1: string, v2: string) => {
        const p1 = v1.split(".").map(Number);
        const p2 = v2.split(".").map(Number);

        for (let i = 0; i < Math.max(p1.length, p2.length); i++) {
            const n1 = p1[i] || 0;
            const n2 = p2[i] || 0;
            if (n1 > n2) return 1;
            if (n1 < n2) return -1;
        }
        return 0;
    };

    if (!isVisible || !updateAvailable) return null;

    return (
        <div className="fixed bottom-4 left-4 z-50 animate-in slide-in-from-left-5 fade-in duration-500">
            <div className="bg-popover text-popover-foreground border border-border rounded-lg shadow-lg p-4 max-w-sm flex items-start gap-4">
                <div className="p-2 bg-primary/10 text-primary rounded-full shrink-0">
                    <Bell size={20} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-sm">{t("update.title")}</h4>
                        <button
                            onClick={() => setIsVisible(false)}
                            className="text-muted-foreground hover:text-foreground transition-colors"
                        >
                            <X size={16} />
                        </button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 mb-3">
                        {t("update.description", { version: updateAvailable.tag_name })}
                    </p>
                    <button
                        onClick={() => openUrl(updateAvailable.html_url)}
                        className="text-xs bg-primary text-primary-foreground hover:bg-primary/90 px-3 py-1.5 rounded-md font-medium inline-flex items-center gap-1.5 transition-colors"
                    >
                        {t("update.action")}
                        <ExternalLink size={12} />
                    </button>
                </div>
            </div>
        </div>
    );
}
