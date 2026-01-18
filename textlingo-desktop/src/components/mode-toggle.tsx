import { Moon, Sun, Palette } from "lucide-react"
import { useTheme } from "./theme-provider"
import { Button } from "./ui/Button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
    DropdownMenuLabel,
} from "./ui/DropdownMenu"
import { useTranslation } from "react-i18next"

export function ModeToggle() {
    const { themeName, themeMode, setThemeName, setThemeMode, resolvedMode } = useTheme()
    const { t } = useTranslation()

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="w-9 px-0">
                    {/* 根据当前模式显示图标 */}
                    <Sun className={`h-[1.2rem] w-[1.2rem] transition-all ${resolvedMode === "dark" ? "rotate-90 scale-0" : "rotate-0 scale-100"}`} />
                    <Moon className={`absolute h-[1.2rem] w-[1.2rem] transition-all ${resolvedMode === "dark" ? "rotate-0 scale-100" : "rotate-90 scale-0"}`} />
                    <span className="sr-only">{t("settings.theme.themeName")}</span>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
                {/* 主题选择区域 */}
                <DropdownMenuLabel className="text-xs text-muted-foreground">
                    {t("settings.theme.themeName")}
                </DropdownMenuLabel>
                <DropdownMenuItem
                    onClick={() => setThemeName("seoul")}
                    className={themeName === "seoul" ? "bg-accent" : ""}
                >
                    <Palette className="mr-2 h-4 w-4" />
                    <span>{t("settings.theme.seoul")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                    onClick={() => setThemeName("tokyo")}
                    className={themeName === "tokyo" ? "bg-accent" : ""}
                >
                    <Palette className="mr-2 h-4 w-4" />
                    <span>{t("settings.theme.tokyo")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                    onClick={() => setThemeName("california")}
                    className={themeName === "california" ? "bg-accent" : ""}
                >
                    <Palette className="mr-2 h-4 w-4" />
                    <span>{t("settings.theme.california")}</span>
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                {/* 模式选择区域 */}
                <DropdownMenuLabel className="text-xs text-muted-foreground">
                    {t("settings.theme.themeMode")}
                </DropdownMenuLabel>
                <DropdownMenuItem
                    onClick={() => setThemeMode("light")}
                    className={themeMode === "light" ? "bg-accent" : ""}
                >
                    <Sun className="mr-2 h-4 w-4" />
                    <span>{t("settings.theme.light")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                    onClick={() => setThemeMode("dark")}
                    className={themeMode === "dark" ? "bg-accent" : ""}
                >
                    <Moon className="mr-2 h-4 w-4" />
                    <span>{t("settings.theme.dark")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                    onClick={() => setThemeMode("system")}
                    className={themeMode === "system" ? "bg-accent" : ""}
                >
                    <span className="mr-2 h-4 w-4 flex items-center justify-center text-xs">⚙️</span>
                    <span>{t("settings.theme.system")}</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}
