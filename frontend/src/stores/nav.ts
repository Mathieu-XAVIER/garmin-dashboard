import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

interface NativeTab {
  id: string
  label: string
  icon: string
  to: string
}

const NATIVE_TABS: NativeTab[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '▣', to: '/' },
  { id: 'activities', label: 'Activités', icon: '◎', to: '/activities' },
  { id: 'health', label: 'Santé', icon: '♡', to: '/health' },
  { id: 'sleep', label: 'Sommeil', icon: '◐', to: '/sleep' },
  { id: 'profile', label: 'Profil', icon: '◈', to: '/profile' },
]

export const useNavStore = defineStore('nav', () => {
  const hiddenTabs = ref<string[]>([])
  const settingsOpen = ref(false)

  const allNativeTabs = computed(() => NATIVE_TABS)

  const nativeTabs = computed(() =>
    NATIVE_TABS.filter(t => !hiddenTabs.value.includes(t.id))
  )

  function syncFromAuth(user: { nav_preferences?: { hidden_tabs?: string[] } | null }) {
    hiddenTabs.value = user.nav_preferences?.hidden_tabs ?? []
  }

  async function fetchPreferences() {
    try {
      const { data } = await api.get('/preferences/nav')
      hiddenTabs.value = data.hidden_tabs ?? []
    } catch {
      // silencieux
    }
  }

  async function updateHiddenTabs(tabs: string[]) {
    hiddenTabs.value = tabs
    await api.put('/preferences/nav', { hidden_tabs: tabs })
  }

  return {
    hiddenTabs, settingsOpen,
    allNativeTabs, nativeTabs,
    syncFromAuth, fetchPreferences, updateHiddenTabs,
  }
})
