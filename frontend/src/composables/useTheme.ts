import { useThemeStore } from '@/stores/theme'

export function useTheme() {
    const themeStore = useThemeStore()
    return {
        isDark: themeStore.isDark,
        mode: themeStore.mode,
        toggleMode: themeStore.toggleMode,
        setMode: themeStore.setMode,
    }
}
