import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import { useNavStore } from './nav'

export interface WidgetData {
  [key: string]: any
}

export interface Widget {
  id: number
  widget_type: string
  title: string
  position: number
  width: string
  config: Record<string, any>
  data?: WidgetData
}

export interface Dashboard {
  id: number
  name: string
  slug: string
  icon: string | null
  position: number
  config: Record<string, any> | null
}

export interface DashboardWithWidgets {
  dashboard: Dashboard
  widgets: Widget[]
}

export const useDashboardsStore = defineStore('dashboards', () => {
  const dashboards = ref<Dashboard[]>([])
  const currentDashboard = ref<DashboardWithWidgets | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function fetchDashboards() {
    const { data } = await api.get('/dashboards/')
    dashboards.value = data
  }

  async function fetchDashboardData(slug: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get(`/dashboards/${slug}/data`)
      currentDashboard.value = data
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Erreur lors du chargement'
    } finally {
      loading.value = false
    }
  }

  async function createDashboard(input: { name: string; icon?: string; config?: Record<string, any> }) {
    saving.value = true
    try {
      const { data } = await api.post('/dashboards/', input)
      dashboards.value.push(data)
      const navStore = useNavStore()
      navStore.addDashboardToNav({ id: data.id, name: data.name, slug: data.slug, icon: data.icon, position: data.position })
      return data
    } finally {
      saving.value = false
    }
  }

  async function updateDashboard(slug: string, input: { name?: string; icon?: string; config?: Record<string, any> }) {
    saving.value = true
    try {
      const { data } = await api.put(`/dashboards/${slug}`, input)
      const idx = dashboards.value.findIndex(d => d.slug === slug)
      if (idx >= 0) dashboards.value[idx] = data
      const navStore = useNavStore()
      navStore.updateDashboardInNav(slug, { name: data.name, slug: data.slug, icon: data.icon })
      return data
    } finally {
      saving.value = false
    }
  }

  async function deleteDashboard(slug: string) {
    await api.delete(`/dashboards/${slug}`)
    dashboards.value = dashboards.value.filter(d => d.slug !== slug)
    const navStore = useNavStore()
    navStore.removeDashboardFromNav(slug)
  }

  async function reorderDashboards(order: number[]) {
    await api.put('/dashboards/reorder', { order })
  }

  async function addWidget(slug: string, input: { widget_type: string; title: string; width?: string; config: Record<string, any> }) {
    saving.value = true
    try {
      const { data } = await api.post(`/dashboards/${slug}/widgets`, input)
      return data
    } finally {
      saving.value = false
    }
  }

  async function updateWidget(slug: string, widgetId: number, input: { title?: string; width?: string; config?: Record<string, any>; position?: number }) {
    saving.value = true
    try {
      const { data } = await api.put(`/dashboards/${slug}/widgets/${widgetId}`, input)
      return data
    } finally {
      saving.value = false
    }
  }

  async function deleteWidget(slug: string, widgetId: number) {
    await api.delete(`/dashboards/${slug}/widgets/${widgetId}`)
  }

  async function reorderWidgets(slug: string, order: number[]) {
    await api.put(`/dashboards/${slug}/widgets/reorder`, { order })
  }

  async function addExercise(slug: string, date: string, exerciseType: string, reps: number) {
    saving.value = true
    try {
      await api.post(`/dashboards/${slug}/exercises`, { date, exercise_type: exerciseType, reps })
      await fetchDashboardData(slug)
    } finally {
      saving.value = false
    }
  }

  async function deleteExercise(slug: string, exerciseId: number) {
    await api.delete(`/dashboards/${slug}/exercises/${exerciseId}`)
    await fetchDashboardData(slug)
  }

  return {
    dashboards, currentDashboard, loading, saving, error,
    fetchDashboards, fetchDashboardData,
    createDashboard, updateDashboard, deleteDashboard, reorderDashboards,
    addWidget, updateWidget, deleteWidget, reorderWidgets,
    addExercise, deleteExercise,
  }
})
