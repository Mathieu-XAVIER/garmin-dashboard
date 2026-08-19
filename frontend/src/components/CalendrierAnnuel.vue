<template>
  <div class="calendrier">
    <div class="calendrier-entete">
      <div class="calendrier-nav">
        <button class="annee-btn" @click="$emit('changer-annee', annee - 1)">‹</button>
        <span class="annee mono">{{ annee }}</span>
        <button class="annee-btn" :disabled="annee >= anneeCourante" @click="$emit('changer-annee', annee + 1)">›</button>
      </div>
      <p class="calendrier-resume mono">
        {{ totalActivites }} séances · {{ totalDistance }} km · {{ joursActifs }} jours actifs
      </p>
    </div>

    <div class="calendrier-corps">
      <div class="jours-semaine">
        <span>Lun</span><span></span><span>Mer</span><span></span><span>Ven</span><span></span><span>Dim</span>
      </div>

      <div class="grille-wrap">
        <div class="mois-labels">
          <span v-for="mois in labelsMois" :key="mois.index" :style="{ gridColumn: mois.colonne }">
            {{ mois.nom }}
          </span>
        </div>

        <div class="grille">
          <div
            v-for="case_ in cases"
            :key="case_.cle"
            class="case"
            :class="`niveau-${case_.niveau}`"
            :style="{ gridRow: case_.ligne, gridColumn: case_.colonne }"
            :title="case_.infobulle"
          />
        </div>
      </div>
    </div>

    <div class="legende">
      <span class="legende-texte">Moins</span>
      <div v-for="n in 5" :key="n" class="case" :class="`niveau-${n - 1}`" />
      <span class="legende-texte">Plus</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface JourActif {
  date: string
  activites: number
  duree_secondes: number
  distance_km: number
  charge: number
  types: string[]
}

const props = defineProps<{
  annee: number
  jours: JourActif[]
  totalActivites: number
  totalDistance: number
  joursActifs: number
}>()

defineEmits<{ 'changer-annee': [annee: number] }>()

const anneeCourante = new Date().getFullYear()
const NOMS_MOIS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']

const parDate = computed(() => {
  const carte = new Map<string, JourActif>()
  props.jours.forEach(j => carte.set(j.date, j))
  return carte
})

/** Seuils calculés sur les données réelles : une semaine à 3 h ne doit pas
 *  paraître identique à une semaine à 15 h. */
const seuils = computed<[number, number, number, number]>(() => {
  const durees = props.jours.map(j => j.duree_secondes).filter(Boolean).sort((a, b) => a - b)
  if (!durees.length) return [0, 0, 0, 0]
  const quantile = (q: number) => durees[Math.floor((durees.length - 1) * q)] ?? 0
  return [quantile(0.25), quantile(0.5), quantile(0.75), quantile(0.9)]
})

function niveauPour(jour: JourActif | undefined): number {
  if (!jour) return 0
  const [q1, q2, q3, q4] = seuils.value
  const d = jour.duree_secondes
  if (d > q4) return 4
  if (d > q3) return 3
  if (d > q2) return 2
  if (d > q1) return 1
  return 1
}

function formatDuree(secondes: number): string {
  const h = Math.floor(secondes / 3600)
  const m = Math.floor((secondes % 3600) / 60)
  return h > 0 ? `${h} h ${m.toString().padStart(2, '0')}` : `${m} min`
}

const cases = computed(() => {
  const debut = new Date(props.annee, 0, 1)
  const fin = new Date(props.annee, 11, 31)
  const resultat = []

  // La grille démarre au lundi précédant le 1er janvier.
  const curseur = new Date(debut)
  const decalage = (debut.getDay() + 6) % 7
  curseur.setDate(curseur.getDate() - decalage)

  let colonne = 1
  while (curseur <= fin) {
    for (let ligne = 1; ligne <= 7; ligne++) {
      if (curseur >= debut && curseur <= fin) {
        const cle = `${curseur.getFullYear()}-${String(curseur.getMonth() + 1).padStart(2, '0')}-${String(curseur.getDate()).padStart(2, '0')}`
        const jour = parDate.value.get(cle)
        const dateLisible = curseur.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
        resultat.push({
          cle,
          ligne,
          colonne,
          niveau: niveauPour(jour),
          infobulle: jour
            ? `${dateLisible} — ${jour.activites} séance${jour.activites > 1 ? 's' : ''}, ${formatDuree(jour.duree_secondes)}${jour.distance_km ? `, ${jour.distance_km} km` : ''}`
            : `${dateLisible} — repos`,
        })
      }
      curseur.setDate(curseur.getDate() + 1)
    }
    colonne++
  }
  return resultat
})

const labelsMois = computed(() => {
  const vus = new Set<number>()
  const resultat: { index: number; nom: string; colonne: number }[] = []
  cases.value.forEach(c => {
    const mois = Number(c.cle.slice(5, 7)) - 1
    if (!vus.has(mois)) {
      vus.add(mois)
      resultat.push({ index: mois, nom: NOMS_MOIS[mois] ?? '', colonne: c.colonne })
    }
  })
  return resultat
})
</script>

<style scoped>
.calendrier { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 18px; }

.calendrier-entete { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.calendrier-nav { display: flex; align-items: center; gap: 10px; }
.annee { font-size: 15px; font-weight: 600; color: var(--text); min-width: 48px; text-align: center; }
.annee-btn { width: 26px; height: 26px; border-radius: var(--radius); border: 1px solid var(--border); background: none; color: var(--text-muted); font-size: 15px; line-height: 1; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.annee-btn:hover:not(:disabled) { border-color: var(--teal); color: var(--teal); }
.annee-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.calendrier-resume { font-size: 12px; color: var(--text-muted); }

.calendrier-corps { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.jours-semaine { display: grid; grid-template-rows: repeat(7, 12px); gap: 3px; padding-top: 18px; flex-shrink: 0; }
.jours-semaine span { font-size: 9px; color: var(--text-dim); font-family: var(--mono); line-height: 12px; }

.grille-wrap { flex: 1; min-width: 0; }
.mois-labels { display: grid; grid-auto-flow: column; grid-auto-columns: 12px; gap: 3px; height: 14px; margin-bottom: 4px; }
.mois-labels span { font-size: 9px; color: var(--text-dim); font-family: var(--mono); white-space: nowrap; }

.grille { display: grid; grid-template-rows: repeat(7, 12px); grid-auto-flow: column; grid-auto-columns: 12px; gap: 3px; }
.case { width: 12px; height: 12px; border-radius: 2px; background: var(--surface-2); }
.niveau-0 { background: var(--surface-2); }
.niveau-1 { background: rgba(0, 212, 170, 0.25); }
.niveau-2 { background: rgba(0, 212, 170, 0.45); }
.niveau-3 { background: rgba(0, 212, 170, 0.7); }
.niveau-4 { background: var(--teal); }

.legende { display: flex; align-items: center; gap: 4px; justify-content: flex-end; margin-top: 12px; }
.legende-texte { font-size: 10px; color: var(--text-dim); font-family: var(--mono); margin: 0 4px; }

@media (max-width: 768px) {
  .calendrier { padding: 12px; }
  .calendrier-entete { margin-bottom: 12px; }
}
</style>
