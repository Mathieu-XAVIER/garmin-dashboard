<template>
  <div class="view">
    <header class="view-header">
      <div>
        <h1 class="view-title">Activités</h1>
        <p class="view-sub mono">{{ store.activities.length }} activités chargées</p>
      </div>
      <div class="filters">
        <button v-for="t in activityTypes" :key="t" class="filter-btn" :class="{ active: selectedType === t }" @click="selectedType = selectedType === t ? null : t">
          {{ t }}
        </button>
      </div>
    </header>

    <!-- KPIs ───────────────────────────────────────────── -->
    <section class="section">
      <SkeletonLoader v-if="loading" type="kpi" :count="5" />
      <div v-else class="kpi-grid">
        <MetricCard label="Activités"      :value="filteredActivities.length"  accent="teal" />
        <MetricCard label="Distance totale" :value="totalDistance"  unit="km" :decimals="1" accent="teal" />
        <MetricCard label="Temps total"    :value="totalDuration"              accent="none" />
        <MetricCard label="FC moy."        :value="avgHR"          unit="bpm"  accent="orange" />
        <MetricCard label="Charge totale"  :value="totalLoad"      :decimals="0" accent="purple" />
      </div>
    </section>

    <!-- Charge d'entraînement ──────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Charge d'entraînement — 6 semaines</h2>
      <SkeletonLoader v-if="loading" type="chart" />
      <div v-else class="chart-card">
        <AreaChart v-if="loadData.length" :data="loadData" label="Training Load" color="#FF6B35" :height="160" />
        <EmptyState v-else message="Aucune donnée de charge" hint="Lance une synchro pour récupérer tes activités" />
      </div>
    </section>

    <!-- Tableau ─────────────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Liste</h2>
      <SkeletonLoader v-if="loading" type="table" :count="8" />
      <div v-else class="activities-table">
        <div class="table-header">
          <span>Activité</span>
          <span>Date</span>
          <span>Distance</span>
          <span>Durée</span>
          <span>FC moy.</span>
          <span>Allure</span>
          <span>Charge</span>
          <span></span>
        </div>
        <EmptyState v-if="!filteredActivities.length" message="Aucune activité" />
        <RouterLink
          v-for="act in filteredActivities"
          :key="act.garmin_id"
          :to="`/activities/${act.garmin_id}`"
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
          <span class="chevron">›</span>
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useGarminStore } from '../stores/garmin'
import MetricCard     from '../components/cards/MetricCard.vue'
import AreaChart      from '../components/charts/AreaChart.vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import EmptyState     from '../components/EmptyState.vue'

const store = useGarminStore()
const loading = ref(true)
const selectedType = ref<string | null>(null)

const activityTypes     = computed(() => [...new Set(store.activities.map(a => a.activity_type).filter(Boolean))])
const filteredActivities = computed(() => selectedType.value ? store.activities.filter(a => a.activity_type === selectedType.value) : store.activities)
const totalDistance     = computed(() => filteredActivities.value.reduce((s, a) => s + (a.distance_meters ?? 0), 0) / 1000)
const avgHR             = computed(() => { const a = filteredActivities.value.filter(a => a.avg_heart_rate); return a.length ? Math.round(a.reduce((s, a) => s + a.avg_heart_rate, 0) / a.length) : null })
const totalLoad         = computed(() => filteredActivities.value.reduce((s, a) => s + (a.training_load ?? 0), 0))
const totalDuration     = computed(() => { const s = filteredActivities.value.reduce((sum, a) => sum + (a.duration_seconds ?? 0), 0); return `${Math.floor(s/3600)}h${Math.floor((s%3600)/60).toString().padStart(2,'0')}` })
const loadData          = computed(() => store.trainingLoad.map(d => ({ x: d.date?.slice(5), y: d.training_load ?? 0 })))

const TYPE_COLORS: Record<string, string> = { running: '#00D4AA', cycling: '#7C6FCD', swimming: '#3B82F6', walking: '#8B92A5', strength_training: '#FF6B35' }
function typeColor(t: string) { return TYPE_COLORS[t] ?? '#4A5168' }
function fmtDate(dt: string) { return dt ? new Date(dt).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' }) : '—' }
function fmtDur(s: number) { const h = Math.floor(s/3600), m = Math.floor((s%3600)/60); return h > 0 ? `${h}h${m.toString().padStart(2,'0')}` : `${m}min` }
function pace(act: any) {
  if (!act.distance_meters || !act.duration_seconds) return '—'
  if (act.activity_type !== 'running') return '—'
  const s = act.duration_seconds / (act.distance_meters / 1000)
  return `${Math.floor(s/60)}:${Math.round(s%60).toString().padStart(2,'0')}/km`
}

onMounted(async () => {
  await Promise.all([store.fetchActivities(50), store.fetchTrainingLoad(42)])
  loading.value = false
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
.filter-btn { padding: 5px 12px; border-radius: 20px; border: 1px solid var(--border); background: none; color: var(--text-muted); font-size: 11px; font-family: var(--mono); cursor: pointer; text-transform: uppercase; letter-spacing: 0.05em; transition: all 0.15s; }
.filter-btn:hover { border-color: var(--teal); color: var(--teal); }
.filter-btn.active { background: var(--teal-dim); border-color: var(--teal); color: var(--teal); }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 12px 8px; }
.activities-table { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.table-header, .table-row { display: grid; grid-template-columns: 2fr 1.2fr 1fr 0.8fr 0.8fr 1fr 0.7fr 24px; gap: 8px; padding: 10px 16px; align-items: center; }
.table-header { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); border-bottom: 1px solid var(--border); font-weight: 500; }
.table-row { font-size: 12px; border-bottom: 1px solid var(--border); transition: background 0.12s; text-decoration: none; color: inherit; cursor: pointer; }
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--surface-2); }
.table-row:hover .chevron { color: var(--teal); }
.act-name-cell { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 500; }
.type-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.mono { font-family: var(--mono); }
.muted { color: var(--text-muted); }
.text-orange { color: var(--orange); }
.chevron { font-size: 16px; color: var(--text-dim); transition: color 0.15s; }
</style>
