<template>
  <div class="view">

    <!-- Header ─────────────────────────────────────────── -->
    <header class="view-header">
      <div>
        <h1 class="view-title">Prépa Handball</h1>
        <p class="view-sub mono">Nord Drôme Handball · 30 juin — 10 août</p>
      </div>
      <div class="player-badge">
        <span class="badge-name">MATHIEU</span>
        <span class="badge-detail mono">DC · 183 cm · 73 kg</span>
        <span class="badge-warn">⚠ Genoux</span>
      </div>
    </header>

    <!-- Skeleton ────────────────────────────────────────── -->
    <template v-if="store.loading">
      <SkeletonLoader type="kpi" :count="4" />
      <div style="margin-top:24px"><SkeletonLoader type="chart" /></div>
    </template>

    <template v-else-if="store.data">

      <!-- Barre de progression globale ─────────────────── -->
      <section class="section">
        <div class="global-progress-card">
          <div class="gp-header">
            <span class="gp-title">Progression globale</span>
            <span class="gp-week mono">
              <template v-if="prep.current_week === 0">Commence le 30 juin</template>
              <template v-else-if="prep.current_week > prep.total_weeks">Terminée !</template>
              <template v-else>Semaine {{ prep.current_week }} / {{ prep.total_weeks }}</template>
            </span>
          </div>
          <div class="gp-bar-wrap">
            <div class="gp-bar" :style="{ width: globalProgress + '%' }"></div>
          </div>
          <div class="gp-pct mono">{{ globalProgress }}%</div>
        </div>
      </section>

      <!-- KPIs ─────────────────────────────────────────── -->
      <section class="section">
        <h2 class="section-title">Objectifs</h2>
        <div class="kpi-grid">
          <div class="obj-card">
            <div class="obj-icon">🏃</div>
            <div class="obj-label">Défi Course</div>
            <div class="obj-progress-ring-wrap">
              <svg viewBox="0 0 100 100" class="obj-ring">
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--surface-2)" stroke-width="8"/>
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--teal)" stroke-width="8"
                  stroke-linecap="round"
                  :stroke-dasharray="`${kmArc} 264`"
                  stroke-dashoffset="66"
                  style="transition: stroke-dasharray 0.8s ease"/>
              </svg>
              <div class="obj-ring-center">
                <span class="obj-val mono">{{ totals.km }}</span>
                <span class="obj-unit">/ {{ objectives.course_km }} km</span>
              </div>
            </div>
            <div class="obj-count mono">{{ totals.runs }} sortie{{ totals.runs > 1 ? 's' : '' }}</div>
          </div>

          <div class="obj-card" v-for="ex in exerciseCards" :key="ex.key">
            <div class="obj-icon">{{ ex.icon }}</div>
            <div class="obj-label">{{ ex.label }}</div>
            <div class="obj-progress-ring-wrap">
              <svg viewBox="0 0 100 100" class="obj-ring">
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--surface-2)" stroke-width="8"/>
                <circle cx="50" cy="50" r="42" fill="none" :stroke="ex.color" stroke-width="8"
                  stroke-linecap="round"
                  :stroke-dasharray="`${ex.arc} 264`"
                  stroke-dashoffset="66"
                  style="transition: stroke-dasharray 0.8s ease"/>
              </svg>
              <div class="obj-ring-center">
                <span class="obj-val mono">{{ ex.best }}</span>
                <span class="obj-unit">/ {{ ex.obj }} reps</span>
              </div>
            </div>
            <div class="obj-count mono">Meilleur score</div>
          </div>
        </div>
      </section>

      <!-- Saisie rapide ────────────────────────────────── -->
      <section class="section">
        <h2 class="section-title">Enregistrer un essai</h2>
        <div class="input-card">
          <div class="input-row">
            <div class="input-group">
              <label class="input-label">Date</label>
              <input type="date" v-model="formDate" class="input-field" />
            </div>
            <div class="input-group">
              <label class="input-label">Exercice</label>
              <select v-model="formType" class="input-field">
                <option value="pompes">Pompes</option>
                <option value="squats">Squats</option>
                <option value="abdos">Abdos</option>
              </select>
            </div>
            <div class="input-group">
              <label class="input-label">Reps</label>
              <input type="number" v-model.number="formReps" min="0" class="input-field" placeholder="0" />
            </div>
            <button class="save-btn" @click="saveExercise" :disabled="store.saving || !formReps">
              {{ store.saving ? '…' : 'Enregistrer' }}
            </button>
          </div>
          <p v-if="saveMsg" class="save-msg mono">{{ saveMsg }}</p>
        </div>
      </section>

      <!-- Semaines ─────────────────────────────────────── -->
      <section class="section">
        <h2 class="section-title">Suivi semaine par semaine</h2>
        <div class="weeks-grid">
          <div v-for="w in prep.weeks" :key="w.week" class="week-card"
               :class="{ 'week-current': w.week === prep.current_week, 'week-future': w.week > prep.current_week && prep.current_week > 0 }">
            <div class="week-header">
              <span class="week-num">S{{ w.week }}</span>
              <span class="week-dates mono">{{ formatDateShort(w.start) }} → {{ formatDateShort(w.end) }}</span>
            </div>

            <div class="week-metrics">
              <div class="wm-item">
                <span class="wm-icon">🏃</span>
                <span class="wm-val mono">{{ w.km }} km</span>
                <span class="wm-sub mono">{{ w.runs }} run{{ w.runs > 1 ? 's' : '' }}</span>
              </div>
              <div class="wm-item">
                <span class="wm-icon">💪</span>
                <span class="wm-val mono">{{ w.pompes }}</span>
                <span class="wm-sub">pompes</span>
              </div>
              <div class="wm-item">
                <span class="wm-icon">🦵</span>
                <span class="wm-val mono">{{ w.squats }}</span>
                <span class="wm-sub">squats</span>
              </div>
              <div class="wm-item">
                <span class="wm-icon">🔥</span>
                <span class="wm-val mono">{{ w.abdos }}</span>
                <span class="wm-sub">abdos</span>
              </div>
            </div>

            <!-- Détail sorties course -->
            <div v-if="w.running_entries.length" class="week-runs">
              <div v-for="r in w.running_entries" :key="r.garmin_id" class="run-row">
                <span class="run-date mono">{{ r.date.slice(5) }}</span>
                <span class="run-name">{{ r.name }}</span>
                <span class="run-dist mono">{{ r.distance_km }} km</span>
                <span class="run-hr mono" v-if="r.avg_heart_rate">♡ {{ r.avg_heart_rate }}</span>
              </div>
            </div>

            <!-- Détail exercices -->
            <div v-if="w.exercise_entries.length" class="week-exercises">
              <div v-for="e in w.exercise_entries" :key="e.id" class="ex-row">
                <span class="ex-date mono">{{ e.date.slice(5) }}</span>
                <span class="ex-type">{{ e.exercise_type }}</span>
                <span class="ex-reps mono">{{ e.reps }} reps</span>
                <button class="ex-del" @click="store.deleteExercise(e.id)" title="Supprimer">×</button>
              </div>
            </div>

            <div v-if="!w.running_entries.length && !w.exercise_entries.length" class="week-empty mono">
              Aucune activité
            </div>
          </div>
        </div>
      </section>

    </template>

    <div v-else-if="store.error" class="error-state">{{ store.error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useHandballStore } from '../stores/handball'
import SkeletonLoader from '../components/SkeletonLoader.vue'

const store = useHandballStore()

const formDate = ref(new Date().toISOString().slice(0, 10))
const formType = ref('pompes')
const formReps = ref<number | null>(null)
const saveMsg = ref('')

const prep = computed(() => store.data ?? { current_week: 0, total_weeks: 6, weeks: [], objectives: {}, totals: {} })
const totals = computed(() => prep.value.totals ?? { km: 0, runs: 0, best_pompes: 0, best_squats: 0, best_abdos: 0 })
const objectives = computed(() => prep.value.objectives ?? { course_km: 50, pompes: 30, squats: 50, abdos: 80 })

const globalProgress = computed(() => {
  const o = objectives.value
  const t = totals.value
  const pKm = Math.min(100, (t.km / o.course_km) * 100)
  const pPompes = Math.min(100, (t.best_pompes / o.pompes) * 100)
  const pSquats = Math.min(100, (t.best_squats / o.squats) * 100)
  const pAbdos = Math.min(100, (t.best_abdos / o.abdos) * 100)
  return Math.round((pKm + pPompes + pSquats + pAbdos) / 4)
})

const kmArc = computed(() => Math.round(Math.min(1, totals.value.km / objectives.value.course_km) * 264))

const exerciseCards = computed(() => [
  {
    key: 'pompes', label: 'Pompes', icon: '💪', color: 'var(--orange)',
    best: totals.value.best_pompes, obj: objectives.value.pompes,
    arc: Math.round(Math.min(1, totals.value.best_pompes / objectives.value.pompes) * 264),
  },
  {
    key: 'squats', label: 'Squats', icon: '🦵', color: 'var(--purple)',
    best: totals.value.best_squats, obj: objectives.value.squats,
    arc: Math.round(Math.min(1, totals.value.best_squats / objectives.value.squats) * 264),
  },
  {
    key: 'abdos', label: 'Abdos', icon: '🔥', color: '#F59E0B',
    best: totals.value.best_abdos, obj: objectives.value.abdos,
    arc: Math.round(Math.min(1, totals.value.best_abdos / objectives.value.abdos) * 264),
  },
])

function formatDateShort(iso: string) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

async function saveExercise() {
  if (!formReps.value) return
  await store.addExercise(formDate.value, formType.value, formReps.value)
  saveMsg.value = `${formType.value} : ${formReps.value} reps enregistrées`
  formReps.value = null
  setTimeout(() => { saveMsg.value = '' }, 3000)
}

onMounted(() => store.fetchPrep())
</script>

<style scoped>
.view { padding: 32px 40px; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
.view-title { font-size: 22px; font-weight: 600; }
.view-sub { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

.player-badge { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
.badge-name { font-size: 14px; font-weight: 600; color: var(--teal); text-transform: uppercase; letter-spacing: 0.1em; }
.badge-detail { font-size: 11px; color: var(--text-muted); }
.badge-warn { font-size: 10px; color: var(--orange); background: var(--orange-dim); padding: 2px 8px; border-radius: 10px; }

.section { margin-bottom: 28px; }
.section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); font-weight: 500; margin-bottom: 14px; }

/* Global progress */
.global-progress-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px 24px; }
.gp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.gp-title { font-size: 13px; font-weight: 500; }
.gp-week { font-size: 12px; color: var(--teal); }
.gp-bar-wrap { height: 10px; background: var(--surface-2); border-radius: 5px; overflow: hidden; }
.gp-bar { height: 100%; background: linear-gradient(90deg, var(--teal), #00B894); border-radius: 5px; transition: width 0.8s ease; }
.gp-pct { text-align: right; font-size: 11px; color: var(--text-muted); margin-top: 6px; }

/* Objectives */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.obj-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.obj-icon { font-size: 24px; }
.obj-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 500; }
.obj-progress-ring-wrap { position: relative; width: 100px; height: 100px; }
.obj-ring { width: 100px; height: 100px; transform: rotate(-90deg); }
.obj-ring-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.obj-val { display: block; font-size: 20px; font-weight: 500; color: var(--text); line-height: 1; }
.obj-unit { display: block; font-size: 9px; color: var(--text-muted); margin-top: 2px; }
.obj-count { font-size: 10px; color: var(--text-dim); }

/* Input */
.input-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; }
.input-row { display: flex; gap: 12px; align-items: flex-end; }
.input-group { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.input-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); }
.input-field { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 12px; color: var(--text); font-family: var(--mono); font-size: 12px; outline: none; }
.input-field:focus { border-color: var(--teal); }
.save-btn { padding: 8px 20px; background: var(--teal-dim); border: 1px solid var(--teal); border-radius: var(--radius); color: var(--teal); font-family: var(--sans); font-size: 12px; font-weight: 500; cursor: pointer; white-space: nowrap; transition: background 0.15s; }
.save-btn:hover:not(:disabled) { background: rgba(0, 212, 170, 0.2); }
.save-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.save-msg { font-size: 11px; color: var(--teal); margin-top: 8px; }

/* Weeks */
.weeks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.week-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px; transition: border-color 0.15s; }
.week-card.week-current { border-color: var(--teal); box-shadow: 0 0 0 1px var(--teal-dim); }
.week-card.week-future { opacity: 0.5; }
.week-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.week-num { font-size: 14px; font-weight: 600; color: var(--teal); }
.week-dates { font-size: 10px; color: var(--text-dim); }

.week-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
.wm-item { text-align: center; }
.wm-icon { font-size: 14px; display: block; }
.wm-val { font-size: 14px; font-weight: 500; color: var(--text); display: block; }
.wm-sub { font-size: 9px; color: var(--text-dim); display: block; }

.week-runs { border-top: 1px solid var(--border); padding-top: 8px; }
.run-row { display: flex; gap: 8px; align-items: center; padding: 4px 0; font-size: 11px; }
.run-date { color: var(--text-dim); min-width: 40px; }
.run-name { color: var(--text-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.run-dist { color: var(--teal); }
.run-hr { color: var(--orange); font-size: 10px; }

.week-exercises { border-top: 1px solid var(--border); padding-top: 8px; }
.ex-row { display: flex; gap: 8px; align-items: center; padding: 4px 0; font-size: 11px; }
.ex-date { color: var(--text-dim); min-width: 40px; }
.ex-type { color: var(--text-muted); flex: 1; text-transform: capitalize; }
.ex-reps { color: var(--purple); }
.ex-del { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 14px; padding: 0 4px; line-height: 1; }
.ex-del:hover { color: var(--orange); }

.week-empty { text-align: center; font-size: 11px; color: var(--text-dim); padding: 8px 0; }

.error-state { padding: 64px; text-align: center; color: var(--text-muted); }

@media (max-width: 900px) {
  .view { padding: 20px 16px; }
  .view-header { flex-direction: column; gap: 12px; }
  .player-badge { align-items: flex-start; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .weeks-grid { grid-template-columns: 1fr; }
  .input-row { flex-direction: column; }
}
</style>
