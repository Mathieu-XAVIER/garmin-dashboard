import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000' })

export const useHandballStore = defineStore('handball', () => {
  const data = ref<any>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const saving = ref(false)

  async function fetchPrep() {
    loading.value = true
    error.value = null
    try {
      const { data: d } = await api.get('/handball/prep')
      data.value = d
    } catch (e: any) {
      error.value = e.message ?? 'Erreur API'
    } finally {
      loading.value = false
    }
  }

  async function addExercise(date: string, exerciseType: string, reps: number) {
    saving.value = true
    try {
      await api.post('/handball/exercises', {
        date,
        exercise_type: exerciseType,
        reps,
      })
      await fetchPrep()
    } catch (e: any) {
      error.value = e.message ?? 'Erreur lors de la sauvegarde'
    } finally {
      saving.value = false
    }
  }

  async function deleteExercise(id: number) {
    try {
      await api.delete(`/handball/exercises/${id}`)
      await fetchPrep()
    } catch (e: any) {
      error.value = e.message ?? 'Erreur lors de la suppression'
    }
  }

  return { data, loading, error, saving, fetchPrep, addExercise, deleteExercise }
})
