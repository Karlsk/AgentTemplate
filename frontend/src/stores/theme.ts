import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import { usePreferredDark } from '@vueuse/core'
import { darkTheme, type GlobalThemeOverrides } from 'naive-ui'

export type ThemeMode = 'light' | 'dark' | 'system'

export const useThemeStore = defineStore('theme', () => {
    const mode = ref<ThemeMode>(
        (localStorage.getItem('themeMode') as ThemeMode) || 'system',
    )
    const prefersDark = usePreferredDark()

    const isDark = computed(() => {
        if (mode.value === 'system') return prefersDark.value
        return mode.value === 'dark'
    })

    const naiveTheme = computed(() => (isDark.value ? darkTheme : null))

    const themeOverrides = computed<GlobalThemeOverrides>(() => ({
        common: {
            primaryColor: '#3B82F6',
            primaryColorHover: '#2563EB',
            primaryColorPressed: '#1D4ED8',
            primaryColorSuppl: '#3B82F6',
            borderRadius: '12px',
            borderRadiusSmall: '8px',
            fontSize: '14px',
        },
        Button: {
            borderRadiusMedium: '12px',
            borderRadiusSmall: '8px',
            borderRadiusLarge: '12px',
        },
        Card: {
            borderRadius: '16px',
        },
        Input: {
            borderRadius: '12px',
        },
        DataTable: {
            borderRadius: '12px',
        },
    }))

    function setMode(newMode: ThemeMode) {
        mode.value = newMode
        localStorage.setItem('themeMode', newMode)
    }

    function toggleMode() {
        const modes: ThemeMode[] = ['light', 'dark', 'system']
        const currentIndex = modes.indexOf(mode.value)
        setMode(modes[(currentIndex + 1) % modes.length]!)
    }

    watch(
        isDark,
        (dark) => {
            document.documentElement.classList.toggle('dark', dark)
        },
        { immediate: true },
    )

    return {
        mode,
        isDark,
        naiveTheme,
        themeOverrides,
        setMode,
        toggleMode,
    }
})
