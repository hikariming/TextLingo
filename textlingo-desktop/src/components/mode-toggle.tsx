import { Moon, Sun, Eye } from "lucide-react"
import { useTheme } from "./theme-provider"
import { Button } from "./ui/Button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "./ui/DropdownMenu"
import { useTranslation } from "react-i18next"

export function ModeToggle() {
    const { setTheme } = useTheme()
    const { t } = useTranslation()

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="w-9 px-0">
                    <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 eye-protection:scale-0" />
                    <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 eye-protection:scale-0" />
                    <Eye className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all eye-protection:rotate-0 eye-protection:scale-100" />
                    <span className="sr-only">Toggle theme</span>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setTheme("light")}>
                    <Sun className="mr-2 h-4 w-4" />
                    <span>{t("Light")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme("dark")}>
                    <Moon className="mr-2 h-4 w-4" />
                    <span>{t("Dark")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme("eye-protection")}>
                    <Eye className="mr-2 h-4 w-4" />
                    <span>{t("Eye Protection")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme("system")}>
                    <span>{t("System")}</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}
