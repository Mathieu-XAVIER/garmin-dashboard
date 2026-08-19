import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface Objectif {
  metrique: string
  cible: number
  libelle: string
  unite: string
}

export interface Progression extends Objectif {
  actuel: number
  pourcentage: number
  atteint: boolean
}

export const useGoalsStore = defineStore('goals', () => {
  const objectifs = ref<Objectif[]>([])
  const metriquesDisponibles = ref<Objectif[]>([])
  const progression = ref<Progression[]>([])
  const semaineDebut = ref<string | null>(null)
  const semaineFin = ref<string | null>(null)
  const chargement = ref(false)

  async function fetchObjectifs() {
    const { data } = await api.get('/goals/')
    objectifs.value = data.objectifs
    metriquesDisponibles.value = data.metriques_disponibles
  }

  async function fetchProgression() {
    chargement.value = true
    try {
      const { data } = await api.get('/goals/progress')
      progression.value = data.objectifs
      semaineDebut.value = data.semaine_debut
      semaineFin.value = data.semaine_fin
    } finally {
      chargement.value = false
    }
  }

  async function enregistrer(cibles: { metrique: string; cible: number }[]) {
    const { data } = await api.put('/goals/', { objectifs: cibles })
    objectifs.value = data.objectifs
    await fetchProgression()
  }

  return {
    objectifs, metriquesDisponibles, progression,
    semaineDebut, semaineFin, chargement,
    fetchObjectifs, fetchProgression, enregistrer,
  }
})
