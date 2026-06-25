import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useProfileStore = defineStore('profile', () => {
  const data     = ref<any>(null)
  const loading  = ref(false)
  const error    = ref<string | null>(null)

  async function fetchProfile() {
    loading.value = true
    error.value   = null
    try {
      const { data: d } = await api.get('/profile/')
      data.value = d
    } catch (e: any) {
      error.value = e.message ?? 'Erreur API'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, fetchProfile }
})
