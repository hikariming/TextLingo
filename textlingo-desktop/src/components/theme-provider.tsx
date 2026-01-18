import { createContext, useContext, useEffect, useState } from "react"

// 主题名称类型 - 城市特色主题
type ThemeName = "seoul" | "tokyo" | "california"

// 显示模式类型
type ThemeMode = "light" | "dark" | "system"

type ThemeProviderProps = {
    children: React.ReactNode
    defaultThemeName?: ThemeName
    defaultThemeMode?: ThemeMode
    storageKeyName?: string
    storageKeyMode?: string
}

type ThemeProviderState = {
    themeName: ThemeName
    themeMode: ThemeMode
    setThemeName: (name: ThemeName) => void
    setThemeMode: (mode: ThemeMode) => void
    // 兼容旧 API，返回实际的显示模式
    resolvedMode: "light" | "dark"
}

const initialState: ThemeProviderState = {
    themeName: "california",
    themeMode: "system",
    setThemeName: () => null,
    setThemeMode: () => null,
    resolvedMode: "light",
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
    children,
    defaultThemeName = "california",
    defaultThemeMode = "system",
    storageKeyName = "vite-ui-theme-name",
    storageKeyMode = "vite-ui-theme-mode",
}: ThemeProviderProps) {
    // 从 localStorage 读取主题名称
    const [themeName, setThemeNameState] = useState<ThemeName>(() => {
        const stored = localStorage.getItem(storageKeyName)
        if (stored && ["seoul", "tokyo", "california"].includes(stored)) {
            return stored as ThemeName
        }
        return defaultThemeName
    })

    // 从 localStorage 读取显示模式
    const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
        const stored = localStorage.getItem(storageKeyMode)
        if (stored && ["light", "dark", "system"].includes(stored)) {
            return stored as ThemeMode
        }
        return defaultThemeMode
    })

    // 计算实际显示模式
    const [resolvedMode, setResolvedMode] = useState<"light" | "dark">("light")

    useEffect(() => {
        const root = window.document.documentElement

        // 计算实际模式
        let actualMode: "light" | "dark" = "light"
        if (themeMode === "system") {
            actualMode = window.matchMedia("(prefers-color-scheme: dark)").matches
                ? "dark"
                : "light"
        } else {
            actualMode = themeMode
        }
        setResolvedMode(actualMode)

        // 移除所有主题相关类
        root.classList.remove(
            "light", "dark",
            "theme-seoul", "theme-tokyo", "theme-california"
        )

        // 添加主题类
        root.classList.add(`theme-${themeName}`)

        // 添加模式类
        root.classList.add(actualMode)

        // 监听系统主题变化
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
        const handleChange = (e: MediaQueryListEvent) => {
            if (themeMode === "system") {
                const newMode = e.matches ? "dark" : "light"
                setResolvedMode(newMode)
                root.classList.remove("light", "dark")
                root.classList.add(newMode)
            }
        }

        mediaQuery.addEventListener("change", handleChange)
        return () => mediaQuery.removeEventListener("change", handleChange)
    }, [themeName, themeMode])

    const setThemeName = (name: ThemeName) => {
        localStorage.setItem(storageKeyName, name)
        setThemeNameState(name)
    }

    const setThemeMode = (mode: ThemeMode) => {
        localStorage.setItem(storageKeyMode, mode)
        setThemeModeState(mode)
    }

    const value = {
        themeName,
        themeMode,
        setThemeName,
        setThemeMode,
        resolvedMode,
    }

    return (
        <ThemeProviderContext.Provider value={value}>
            {children}
        </ThemeProviderContext.Provider>
    )
}

export const useTheme = () => {
    const context = useContext(ThemeProviderContext)

    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider")

    return context
}
