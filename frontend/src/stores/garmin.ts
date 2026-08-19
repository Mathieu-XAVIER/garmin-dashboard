import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useGarminStore = defineStore('garmin', () => {
  // ── State ────────────────────────────────────────────────
  const summary     = ref<any>(null)
  const weeklyStats = ref<any[]>([])
  const activities  = ref<any[]>([])
  const dailyHealth = ref<any[]>([])
  const todayHealth = ref<any>(null)
  const sleepHistory = ref<any[]>([])
  const hrvHistory  = ref<any[]>([])
  const trainingLoad = ref<any[]>([])

  const loading = ref(false)
  const lastSync = ref<Date | null>(null)
  const error = ref<string | null>(null)
  const syncStatus = ref<any>(null)

  // ── Getters ──────────────────────────────────────────────
  const latestActivity = computed(() => activities.value[0] ?? null)
  const latestSleep    = computed(() => sleepHistory.value[0] ?? null)
  const latestHrv      = computed(() => hrvHistory.value[0] ?? null)

  // ── Actions ──────────────────────────────────────────────
  async function fetchSummary() {
    const { data } = await api.get('/stats/summary')
    summary.value = data
  }

  async function fetchWeeklyStats(weeks = 12) {
    const { data } = await api.get(`/stats/weekly?weeks=${weeks}`)
    weeklyStats.value = data
  }

  async function fetchTrainingLoad(days = 42) {
    const { data } = await api.get(`/stats/training-load?days=${days}`)
    trainingLoad.value = data
  }

  async function fetchActivities(limit = 20) {
    const { data } = await api.get(`/activities/?limit=${limit}`)
    activities.value = data.items
  }

  async function fetchDailyHealth(days = 30) {
    const { data } = await api.get(`/health/daily?days=${days}`)
    dailyHealth.value = data
  }

  async function fetchTodayHealth() {
    const { data } = await api.get('/health/today')
    todayHealth.value = data
  }

  async function fetchSleepHistory(days = 30) {
    const { data } = await api.get(`/health/sleep?days=${days}`)
    sleepHistory.value = data
  }

  async function fetchHrvHistory(days = 30) {
    const { data } = await api.get(`/health/hrv?days=${days}`)
    hrvHistory.value = data
  }

  async function fetchSyncStatus() {
    const { data } = await api.get('/sync/status')
    syncStatus.value = data
    if (data.derniere?.finished_at) {
      lastSync.value = new Date(data.derniere.finished_at + 'Z')
    }
  }

  async function triggerSync(days = 7) {
    await api.post(`/sync?days=${days}`)
    await fetchSyncStatus()
  }

  async function loadDashboard() {
    loading.value = true
    error.value = null
    try {
      const results = await Promise.allSettled([
        fetchSummary(),
        fetchWeeklyStats(),
        fetchTrainingLoad(),
        fetchActivities(10),
        fetchTodayHealth(),
        fetchSleepHistory(14),
        fetchHrvHistory(14),
        fetchSyncStatus(),
      ])
      const failures = results.filter(r => r.status === 'rejected')
      if (failures.length) {
        error.value = `${failures.length} requête(s) en erreur`
      }
    } catch (e: any) {
      error.value = e.message ?? 'Erreur de connexion à l\'API'
    } finally {
      loading.value = false
    }
  }

  return {
    summary, weeklyStats, activities, dailyHealth, todayHealth,
    sleepHistory, hrvHistory, trainingLoad, loading, lastSync, error, syncStatus,
    latestActivity, latestSleep, latestHrv,
    fetchSummary, fetchWeeklyStats, fetchTrainingLoad, fetchActivities,
    fetchDailyHealth, fetchTodayHealth, fetchSleepHistory, fetchHrvHistory,
    triggerSync, loadDashboard, fetchSyncStatus,
  }
})

// ── Profil ────────────────────────────────────────────────────────────────
// (ajouté séparément dans profileStore)
