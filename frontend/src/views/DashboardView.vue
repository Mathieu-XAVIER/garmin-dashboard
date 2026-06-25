<template>
  <div class="view">
    <header class="view-header">
      <div>
        <h1 class="view-title">Dashboard</h1>
        <p class="view-sub mono">{{ today }}</p>
      </div>
      <div v-if="store.error" class="error-badge">{{ store.error }}</div>
    </header>

    <!-- KPIs du jour ───────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Aujourd'hui</h2>
      <SkeletonLoader v-if="store.loading" type="kpi" :count="6" />
      <div v-else class="kpi-grid">
        <MetricCard label="Steps"            :value="store.todayHealth?.steps"              unit="pas"  accent="teal" />
        <MetricCard label="Body Battery max" :value="store.todayHealth?.body_battery_high"  sub="Niveau max du jour" accent="teal" />
        <MetricCard label="FC au repos"      :value="store.todayHealth?.resting_heart_rate" unit="bpm"  accent="orange" />
        <MetricCard label="Stress moyen"     :value="store.todayHealth?.avg_stress"         sub="/ 100" accent="none" />
        <MetricCard label="Calories"          :value="store.todayHealth?.calories_total"     unit="kcal" accent="none" />
        <MetricCard label="VO2 max"          :value="store.summary?.latest_vo2max"          :decimals="1" sub="Dernière activité" accent="purple" />
      </div>
    </section>

    <!-- Body Battery ───────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Body Battery — 14 jours</h2>
      <SkeletonLoader v-if="store.loading" type="chart" />
      <div v-else class="chart-card">
        <AreaChart v-if="bodyBatteryData.length" :data="bodyBatteryData" label="Body Battery max" color="#00D4AA" :height="160" :yMin="0" :yMax="100" />
        <EmptyState v-else message="Aucune donnée de body battery" />
      </div>
    </section>

    <!-- Activités + Volume hebdo ───────────────────────── -->
    <div class="two-col">
      <section class="section activities-section">
        <h2 class="section-title">Activités récentes</h2>
        <SkeletonLoader v-if="store.loading" type="table" :count="4" />
        <div v-else class="card-list">
          <EmptyState v-if="!store.activities.length" message="Aucune activité enregistrée" />
          <ActivityRow v-for="act in store.activities.slice(0, 4)" :key="act.garmin_id" :activity="act" />
        </div>
        <RouterLink to="/activities" class="see-all-link mono">Voir tout →</RouterLink>
      </section>

      <section class="section">
        <h2 class="section-title">Volume hebdomadaire — 12 sem.</h2>
        <SkeletonLoader v-if="store.loading" type="chart" />
        <div v-else class="chart-card">
          <BarChart v-if="weeklyDistData.labels.length" :categories="weeklyDistData.labels" :series="[{ name: 'Distance (km)', data: weeklyDistData.values, color: '#00D4AA' }]" :height="220" unit="km" />
          <EmptyState v-else message="Pas encore de données hebdomadaires" />
        </div>
      </section>
    </div>

    <!-- HRV ────────────────────────────────────────────── -->
    <section class="section">
      <div class="section-header-row">
        <h2 class="section-title">HRV — 14 jours</h2>
        <div v-if="store.latestHrv" class="hrv-status" :class="hrvStatusClass">
          {{ store.latestHrv.status ?? '—' }}
        </div>
      </div>
      <SkeletonLoader v-if="store.loading" type="chart" />
      <div v-else class="chart-card">
        <AreaChart v-if="hrvData.length" :data="hrvData" label="HRV (ms)" color="#7C6FCD" :height="140" />
        <EmptyState v-else message="Aucune donnée HRV" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useGarminStore } from '../stores/garmin'
import MetricCard    from '../components/cards/MetricCard.vue'
import ActivityRow   from '../components/cards/ActivityRow.vue'
import AreaChart     from '../components/charts/AreaChart.vue'
import BarChart      from '../components/charts/BarChart.vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import EmptyState    from '../components/EmptyState.vue'

const store = useGarminStore()

const today = new Date().toLocaleDateString('fr-FR', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
})

const bodyBatteryData = computed(() =>
  store.dailyHealth.map(d => ({ x: d.date?.slice(5), y: d.body_battery_high ?? null })).reverse()
)
const weeklyDistData = computed(() => {
  const weeks = store.weeklyStats.slice(-12)
  return {
    labels: weeks.map(w => w.week_start?.slice(5)),
    values: weeks.map(w => parseFloat((w.total_distance_km ?? 0).toFixed(1))),
  }
})
const hrvData = computed(() =>
  store.hrvHistory.map(h => ({ x: h.date?.slice(5), y: h.last_night_avg ?? null })).reverse()
)
const hrvStatusClass = computed(() => {
  const s = store.latestHrv?.status
  if (s === 'BALANCED') return 'status-good'
  if (s === 'LOW')      return 'status-warn'
  return 'status-neutral'
})

onMounted(() => {
  store.loadDashboard()
  store.fetchDailyHealth(14)
})
</script>

<style scoped>
.view { padding: 32px 40px; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 32px; }
.view-title { font-size: 24px; font-weight: 600; color: var(--text); }
.view-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; text-transform: capitalize; }
.error-badge { padding: 5px 14px; border-radius: 20px; font-size: 12px; font-family: var(--mono); background: var(--orange-dim); color: var(--orange); }
.section { margin-bottom: 32px; }
.section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 14px; }
.section-header-row { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 12px 8px; }
.card-list { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; padding: 4px 0; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }
.hrv-status { font-size: 12px; font-family: var(--mono); padding: 4px 12px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em; }
.status-good    { background: var(--teal-dim); color: var(--teal); }
.status-warn    { background: var(--orange-dim); color: var(--orange); }
.status-neutral { background: var(--surface-2); color: var(--text-muted); }
.activities-section { position: relative; }
.see-all-link { position: absolute; top: 0; right: 0; font-size: 12px; color: var(--teal); text-decoration: none; transition: opacity 0.15s; }
.see-all-link:hover { opacity: 0.8; }
.two-col > .section { display: flex; flex-direction: column; }
.two-col > .section > .card-list,
.two-col > .section > .chart-card { flex: 1; }
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } .view { padding: 20px 16px; } }
</style>
