<template>
  <div class="et-widget">
    <!-- Barre de progression globale -->
    <div class="et-global-progress" v-if="data">
      <div class="gp-header">
        <span class="gp-title">Progression globale</span>
        <span class="gp-week mono">
          <template v-if="data.current_week === 0">Pas encore commencé</template>
          <template v-else-if="data.current_week > data.total_weeks">Terminée !</template>
          <template v-else>Semaine {{ data.current_week }} / {{ data.total_weeks }}</template>
        </span>
      </div>
      <div class="gp-bar-wrap">
        <div class="gp-bar" :style="{ width: globalProgress + '%' }"></div>
      </div>
      <div class="gp-pct mono">{{ globalProgress }}%</div>
    </div>

    <!-- Formulaire de saisie -->
    <div v-if="config.show_input_form" class="et-input-card">
      <h3 class="et-section-title">{{ widget.title }}</h3>
      <div class="et-input-row">
        <div class="et-input-group">
          <label class="et-input-label">Date</label>
          <input type="date" v-model="formDate" class="et-field" />
        </div>
        <div class="et-input-group">
          <label class="et-input-label">Exercice</label>
          <select v-model="formType" class="et-field">
            <option v-for="ex in exerciseOptions" :key="ex.type" :value="ex.type">{{ ex.label }}</option>
          </select>
        </div>
        <div class="et-input-group">
          <label class="et-input-label">Reps</label>
          <input type="number" v-model.number="formReps" min="0" class="et-field" placeholder="0" />
        </div>
        <button class="et-save-btn" @click="saveExercise" :disabled="saving || !formReps">
          {{ saving ? '…' : 'Enregistrer' }}
        </button>
      </div>
      <p v-if="saveMsg" class="et-save-msg mono">{{ saveMsg }}</p>
    </div>

    <!-- Suivi semaine par semaine -->
    <div v-if="config.show_weekly_breakdown && data?.weeks?.length" class="et-weeks">
      <h3 class="et-section-title">Suivi semaine par semaine</h3>
      <div class="et-weeks-grid">
        <div v-for="w in data.weeks" :key="w.week" class="et-week-card"
             :class="{ 'week-current': w.week === data.current_week, 'week-future': w.week > data.current_week && data.current_week > 0 }">
          <div class="et-week-header">
            <span class="et-week-num">S{{ w.week }}</span>
            <span class="et-week-dates mono">{{ formatDate(w.start) }} → {{ formatDate(w.end) }}</span>
          </div>

          <div class="et-week-metrics">
            <div class="et-wm-item" v-if="config.running_types">
              <span class="et-wm-icon">🏃</span>
              <span class="et-wm-val mono">{{ w.km }} km</span>
              <span class="et-wm-sub mono">{{ w.runs }} run{{ w.runs > 1 ? 's' : '' }}</span>
            </div>
            <div v-for="ex in exerciseOptions" :key="ex.type" class="et-wm-item">
              <span class="et-wm-icon">{{ ex.icon }}</span>
              <span class="et-wm-val mono">{{ w[ex.type] ?? 0 }}</span>
              <span class="et-wm-sub">{{ ex.label.toLowerCase() }}</span>
            </div>
          </div>

          <!-- Détail sorties course -->
          <div v-if="w.running_entries?.length" class="et-week-runs">
            <div v-for="r in w.running_entries" :key="r.garmin_id" class="et-run-row">
              <span class="et-run-date mono">{{ r.date.slice(5) }}</span>
              <span class="et-run-name">{{ r.name }}</span>
              <span class="et-run-dist mono">{{ r.distance_km }} km</span>
              <span class="et-run-hr mono" v-if="r.avg_heart_rate">♡ {{ r.avg_heart_rate }}</span>
            </div>
          </div>

          <!-- Détail exercices -->
          <div v-if="w.exercise_entries?.length" class="et-week-entries">
            <div v-for="e in w.exercise_entries" :key="e.id" class="et-entry-row">
              <span class="et-entry-date mono">{{ e.date.slice(5) }}</span>
              <span class="et-entry-type">{{ e.exercise_type }}</span>
              <span class="et-entry-reps mono">{{ e.reps }} reps</span>
              <button class="et-entry-del" @click="handleDelete(e.id)" title="Supprimer">×</button>
            </div>
          </div>

          <div v-if="!w.running_entries?.length && !w.exercise_entries?.length" class="et-week-empty mono">
            Aucune activité
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardsStore } from '@/stores/dashboards'
import type { Widget } from '@/stores/dashboards'

const props = defineProps<{
  widget: Widget
  data: {
    exercises: { type: string; label: string; icon: string; color: string; target: number; best: number }[]
    entries: { id: number; date: string; exercise_type: string; reps: number }[]
    weeks: Record<string, any>[]
    total_km: number
    total_runs: number
    current_week: number
    total_weeks: number
  }
}>()

const route = useRoute()
const dashStore = useDashboardsStore()
const config = computed(() => props.widget.config || {})

const exerciseOptions = computed(() => config.value.exercises || [])

const formDate = ref(new Date().toISOString().slice(0, 10))
const formType = ref(exerciseOptions.value[0]?.type || '')
const formReps = ref<number | null>(null)
const saveMsg = ref('')
const saving = computed(() => dashStore.saving)

const slug = computed(() => route.params.slug as string)

const globalProgress = computed(() => {
  if (!props.data?.exercises) return 0
  const exerciseProgresses = props.data.exercises.map(ex =>
    Math.min(100, ex.target > 0 ? (ex.best / ex.target) * 100 : 0)
  )
  const runningTarget = config.value.running_target_km
  const runProgress = runningTarget ? Math.min(100, (props.data.total_km / runningTarget) * 100) : 0
  const all = runningTarget ? [runProgress, ...exerciseProgresses] : exerciseProgresses
  if (all.length === 0) return 0
  return Math.round(all.reduce((a, b) => a + b, 0) / all.length)
})

function formatDate(iso: string) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

async function saveExercise() {
  if (!formReps.value) return
  await dashStore.addExercise(slug.value, formDate.value, formType.value, formReps.value)
  saveMsg.value = `${formType.value} : ${formReps.value} reps enregistrées`
  formReps.value = null
  setTimeout(() => { saveMsg.value = '' }, 3000)
}

async function handleDelete(id: number) {
  await dashStore.deleteExercise(slug.value, id)
}
</script>

<style scoped>
.et-widget { display: flex; flex-direction: column; gap: 16px; }

/* Progression globale */
.et-global-progress { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px 24px; }
.gp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.gp-title { font-size: 13px; font-weight: 500; }
.gp-week { font-size: 12px; color: var(--teal); }
.gp-bar-wrap { height: 10px; background: var(--surface-2); border-radius: 5px; overflow: hidden; }
.gp-bar { height: 100%; background: linear-gradient(90deg, var(--teal), #00B894); border-radius: 5px; transition: width 0.8s ease; }
.gp-pct { text-align: right; font-size: 12px; color: var(--text-muted); margin-top: 6px; }

/* Formulaire */
.et-input-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; }
.et-section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 14px; }
.et-input-row { display: flex; gap: 12px; align-items: flex-end; }
.et-input-group { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.et-input-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.et-field { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 12px; color: var(--text); font-family: var(--mono); font-size: 12px; outline: none; }
.et-field:focus { border-color: var(--teal); }
.et-save-btn { padding: 8px 20px; background: var(--teal-dim); border: 1px solid var(--teal); border-radius: var(--radius); color: var(--teal); font-family: var(--sans); font-size: 12px; font-weight: 500; cursor: pointer; white-space: nowrap; transition: background 0.15s; }
.et-save-btn:hover:not(:disabled) { background: rgba(0, 212, 170, 0.2); }
.et-save-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.et-save-msg { font-size: 12px; color: var(--teal); margin-top: 8px; }

/* Semaines */
.et-weeks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.et-week-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px; transition: border-color 0.15s; }
.et-week-card.week-current { border-color: var(--teal); box-shadow: 0 0 0 1px var(--teal-dim); }
.et-week-card.week-future { opacity: 0.5; }
.et-week-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.et-week-num { font-size: 14px; font-weight: 600; color: var(--teal); }
.et-week-dates { font-size: 12px; color: var(--text-dim); }

.et-week-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
.et-wm-item { text-align: center; }
.et-wm-icon { font-size: 14px; display: block; }
.et-wm-val { font-size: 14px; font-weight: 500; color: var(--text); display: block; }
.et-wm-sub { font-size: 11px; color: var(--text-dim); display: block; }

.et-week-runs { border-top: 1px solid var(--border); padding-top: 8px; }
.et-run-row { display: flex; gap: 8px; align-items: center; padding: 4px 0; font-size: 12px; }
.et-run-date { color: var(--text-dim); min-width: 40px; }
.et-run-name { color: var(--text-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.et-run-dist { color: var(--teal); }
.et-run-hr { color: var(--orange); font-size: 12px; }

.et-week-entries { border-top: 1px solid var(--border); padding-top: 8px; }
.et-entry-row { display: flex; gap: 8px; align-items: center; padding: 4px 0; font-size: 12px; }
.et-entry-date { color: var(--text-dim); min-width: 40px; }
.et-entry-type { color: var(--text-muted); flex: 1; text-transform: capitalize; }
.et-entry-reps { color: var(--purple); }
.et-entry-del { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 14px; padding: 0 4px; line-height: 1; }
.et-entry-del:hover { color: var(--orange); }

.et-week-empty { text-align: center; font-size: 12px; color: var(--text-dim); padding: 8px 0; }

@media (max-width: 900px) {
  .et-input-row { flex-direction: column; }
  .et-weeks-grid { grid-template-columns: 1fr; }
}
</style>
