import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export interface NavDashboard {
  id: number
  name: string
  slug: string
  icon: string | null
  position: number
}

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
  const customDashboards = ref<NavDashboard[]>([])
  const settingsOpen = ref(false)

  const allNativeTabs = computed(() => NATIVE_TABS)

  const nativeTabs = computed(() =>
    NATIVE_TABS.filter(t => !hiddenTabs.value.includes(t.id))
  )

  function syncFromAuth(user: { nav_preferences?: { hidden_tabs?: string[] } | null, custom_dashboards?: NavDashboard[] }) {
    hiddenTabs.value = user.nav_preferences?.hidden_tabs ?? []
    customDashboards.value = user.custom_dashboards ?? []
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

  function addDashboardToNav(d: NavDashboard) {
    customDashboards.value.push(d)
  }

  function removeDashboardFromNav(slug: string) {
    customDashboards.value = customDashboards.value.filter(d => d.slug !== slug)
  }

  function updateDashboardInNav(slug: string, updates: Partial<NavDashboard>) {
    const d = customDashboards.value.find(d => d.slug === slug)
    if (d) Object.assign(d, updates)
  }

  return {
    hiddenTabs, customDashboards, settingsOpen,
    allNativeTabs, nativeTabs,
    syncFromAuth, fetchPreferences, updateHiddenTabs,
    addDashboardToNav, removeDashboardFromNav, updateDashboardInNav,
  }
})
