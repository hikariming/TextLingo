import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { AppConfig } from "../tauri";

type LoadType = "init" | "refresh";

export function useConfig() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConfig = async (type: LoadType) => {
    try {
      setLoading(true);
      setError(null);
      const appConfig = await invoke<AppConfig>("get_config");
      setConfig(appConfig);
      return appConfig;
    } catch (err) {
      console.error(`[useConfig] Failed to ${type === "init" ? "load" : "refresh"} config:`, err);
      setError(err as string);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig("init");
  }, []);

  return {
    config,
    loading,
    error,
    // Utility function to refresh config if needed
    refreshConfig: () => loadConfig("refresh")
  };
}