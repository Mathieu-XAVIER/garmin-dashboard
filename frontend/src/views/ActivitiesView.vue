<template>
  <div class="view">
    <header class="view-header">
      <div>
        <h1 class="view-title">Activités</h1>
        <p class="view-sub mono">{{ store.activities.length }} activités chargées</p>
      </div>
      <div class="filters">
        <button
          v-for="t in activityTypes"
          :key="t"
          class="filter-btn"
          :class="{ active: selectedType === t }"
          @click="selectedType = selectedType === t ? null : t"
        >{{ t }}</button>
      </div>
    </header>

    <!-- Statistiques agrégées ──────────────────────────── -->
    <section class="section">
      <div class="kpi-grid">
        <MetricCard label="Activités (30j)" :value="filteredActivities.length" accent="teal" />
        <MetricCard label="Distance totale" :value="totalDistance" unit="km" :decimals="1" accent="teal" />
        <MetricCard label="Temps total" :value="totalDuration" accent="none" />
        <MetricCard label="FC moy." :value="avgHR" unit="bpm" accent="orange" />
        <MetricCard label="Charge totale" :value="totalLoad" :decimals="0" accent="purple" />
      </div>
    </section>

    <!-- Charge d'entraînement ──────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Charge d'entraînement — 6 semaines</h2>
      <div class="chart-card">
        <AreaChart
          v-if="loadData.length"
          :data="loadData"
          label="Training Load"
          color="#FF6B35"
          :height="160"
        />
        <div v-else class="chart-empty">Pas de données</div>
      </div>
    </section>

    <!-- Liste des activités ────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Liste</h2>
      <div class="activities-table">
        <div class="table-header">
          <span>Activité</span>
          <span>Date</span>
          <span>Distance</span>
          <span>Durée</span>
          <span>FC moy.</span>
          <span>Allure</span>
          <span>Charge</span>
        </div>
        <div v-if="!filteredActivities.length" class="empty-state">
          Aucune activité
        </div>
        <div
          v-for="act in filteredActivities"
          :key="act.garmin_id"
          class="table-row"
        >
          <span class="act-name-cell">
            <span class="type-dot" :style="{ background: typeColor(act.activity_type) }"></span>
            {{ act.name || act.activity_type }}
          </span>
          <span class="mono muted">{{ fmtDate(act.start_time) }}</span>
          <span class="mono">{{ act.distance_meters ? (act.distance_meters/1000).toFixed(2) + ' km' : '—' }}</span>
          <span class="mono">{{ act.duration_seconds ? fmtDur(act.duration_seconds) : '—' }}</span>
          <span class="mono text-orange">{{ act.avg_heart_rate ? act.avg_heart_rate + ' bpm' : '—' }}</span>
          <span class="mono">{{ pace(act) }}</span>
          <span class="mono muted">{{ act.training_load ? Math.round(act.training_load) : '—' }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useGarminStore } from '../stores/garmin'
import MetricCard from '../components/cards/MetricCard.vue'
import AreaChart from '../components/charts/AreaChart.vue'

const store = useGarminStore()
const selectedType = ref<string | null>(null)

const activityTypes = computed(() => [...new Set(store.activities.map(a => a.activity_type).filter(Boolean))])

const filteredActivities = computed(() =>
  selectedType.value
    ? store.activities.filter(a => a.activity_type === selectedType.value)
    : store.activities
)

const totalDistance = computed(() =>
  filteredActivities.value.reduce((s, a) => s + (a.distance_meters ?? 0), 0) / 1000
)

const avgHR = computed(() => {
  const acts = filteredActivities.value.filter(a => a.avg_heart_rate)
  return acts.length ? Math.round(acts.reduce((s, a) => s + a.avg_heart_rate, 0) / acts.length) : null
})

const totalLoad = computed(() =>
  filteredActivities.value.reduce((s, a) => s + (a.training_load ?? 0), 0)
)

const totalDuration = computed(() => {
  const s = filteredActivities.value.reduce((sum, a) => sum + (a.duration_seconds ?? 0), 0)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}h${m.toString().padStart(2, '0')}`
})

const loadData = computed(() =>
  store.trainingLoad.map(d => ({ x: d.date?.slice(5), y: d.training_load ?? 0 }))
)

const TYPE_COLORS: Record<string, string> = {
  running: '#00D4AA', cycling: '#7C6FCD', swimming: '#3B82F6',
  walking: '#8B92A5', strength_training: '#FF6B35',
}
function typeColor(t: string) { return TYPE_COLORS[t] ?? '#4A5168' }

function fmtDate(dt: string) {
  return dt ? new Date(dt).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' }) : '—'
}
function fmtDur(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}h${m.toString().padStart(2,'0')}` : `${m}min`
}
function pace(act: any) {
  if (!act.distance_meters || !act.duration_seconds) return '—'
  if (act.activity_type !== 'running') return '—'
  const secPerKm = act.duration_seconds / (act.distance_meters / 1000)
  const m = Math.floor(secPerKm / 60), s = Math.round(secPerKm % 60)
  return `${m}:${s.toString().padStart(2,'0')}/km`
}

onMounted(async () => {
  await Promise.all([store.fetchActivities(50), store.fetchTrainingLoad(42)])
})
</script>

<style scoped>
.view { padding: 32px; max-width: 1200px; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; gap: 16px; flex-wrap: wrap; }
.view-title { font-size: 22px; font-weight: 600; }
.view-sub { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
.section { margin-bottom: 28px; }
.section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); font-weight: 500; margin-bottom: 14px; }

.filters { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-btn {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: none;
  color: var(--text-muted);
  font-size: 11px;
  font-family: var(--mono);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.15s;
}
.filter-btn:hover { border-color: var(--teal); color: var(--teal); }
.filter-btn.active { background: var(--teal-dim); border-color: var(--teal); color: var(--teal); }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }

.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 12px 8px; }
.chart-empty { height: 140px; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 12px; font-family: var(--mono); }

.activities-table {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table-header, .table-row {
  display: grid;
  grid-template-columns: 2fr 1.2fr 1fr 0.8fr 0.8fr 1fr 0.7fr;
  gap: 8px;
  padding: 10px 16px;
  align-items: center;
}

.table-header {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  border-bottom: 1px solid var(--border);
  font-weight: 500;
}

.table-row { border-bottom: 1px solid var(--border); font-size: 12px; transition: background 0.12s; }
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--surface-2); }

.act-name-cell { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 500; }
.type-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.mono { font-family: var(--mono); }
.muted { color: var(--text-muted); }
.empty-state { padding: 32px; text-align: center; color: var(--text-dim); font-size: 12px; font-family: var(--mono); }
</style>
