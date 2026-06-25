<template>
  <div class="view">
    <header class="view-header">
      <div>
        <h1 class="view-title">Santé</h1>
        <p class="view-sub mono">30 derniers jours</p>
      </div>
      <div class="day-selector">
        <button v-for="d in [7,14,30]" :key="d" :class="['day-btn', {active: days===d}]" @click="changeDays(d)">
          {{ d }}j
        </button>
      </div>
    </header>

    <!-- KPIs santé ─────────────────────────────────────── -->
    <section class="section">
      <div class="kpi-grid">
        <MetricCard label="Steps moy./jour" :value="avgSteps" unit="pas" accent="teal" />
        <MetricCard label="FC repos moy."   :value="avgRHR" unit="bpm" accent="orange" />
        <MetricCard label="Stress moyen"    :value="avgStress" sub="/ 100" accent="none" />
        <MetricCard label="Body Battery max moy." :value="avgBB" accent="teal" />
      </div>
    </section>

    <!-- Steps ──────────────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Steps quotidiens</h2>
      <div class="chart-card">
        <BarChart
          v-if="stepsData.labels.length"
          :categories="stepsData.labels"
          :series="[{ name: 'Steps', data: stepsData.values, color: '#00D4AA' }]"
          :height="180"
        />
        <div v-else class="chart-empty">Pas de données</div>
      </div>
    </section>

    <!-- Body Battery + Stress côte à côte ──────────────── -->
    <div class="two-col">
      <section class="section">
        <h2 class="section-title">Body Battery</h2>
        <div class="chart-card">
          <AreaChart
            v-if="bbData.length"
            :data="bbData"
            label="Max du jour"
            color="#00D4AA"
            :height="160"
            :yMin="0"
            :yMax="100"
          />
          <div v-else class="chart-empty">Pas de données</div>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">Stress moyen</h2>
        <div class="chart-card">
          <AreaChart
            v-if="stressData.length"
            :data="stressData"
            label="Stress"
            color="#FF6B35"
            :height="160"
            :yMin="0"
            :yMax="100"
          />
          <div v-else class="chart-empty">Pas de données</div>
        </div>
      </section>
    </div>

    <!-- FC repos ────────────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Fréquence cardiaque au repos</h2>
      <div class="chart-card">
        <AreaChart
          v-if="rhrData.length"
          :data="rhrData"
          label="FC repos (bpm)"
          color="#FF6B35"
          :height="150"
        />
        <div v-else class="chart-empty">Pas de données</div>
      </div>
    </section>

    <!-- Tableau détaillé ───────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Détail journalier</h2>
      <div class="health-table">
        <div class="table-header">
          <span>Date</span>
          <span>Steps</span>
          <span>BB max</span>
          <span>FC repos</span>
          <span>Stress moy.</span>
          <span>Cal. actives</span>
          <span>Intensité</span>
        </div>
        <div v-for="d in paginatedHealth" :key="d.date" class="table-row">
          <span class="mono muted">{{ d.date }}</span>
          <span class="mono">{{ d.steps?.toLocaleString('fr-FR') ?? '—' }}</span>
          <span class="mono text-teal">{{ d.body_battery_high ?? '—' }}</span>
          <span class="mono text-orange">{{ d.resting_heart_rate ? d.resting_heart_rate + ' bpm' : '—' }}</span>
          <span class="mono">{{ d.avg_stress ?? '—' }}</span>
          <span class="mono">{{ d.calories_active ? d.calories_active + ' kcal' : '—' }}</span>
          <span class="mono muted">{{ intensityMin(d) }}</span>
        </div>
      </div>
      <div v-if="healthTotalPages > 1" class="pagination">
        <button class="page-btn" :disabled="healthPage === 1" @click="healthPage--">‹ Précédent</button>
        <span class="page-info mono">{{ healthPage }} / {{ healthTotalPages }}</span>
        <button class="page-btn" :disabled="healthPage === healthTotalPages" @click="healthPage++">Suivant ›</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useGarminStore } from '../stores/garmin'
import MetricCard from '../components/cards/MetricCard.vue'
import AreaChart from '../components/charts/AreaChart.vue'
import BarChart from '../components/charts/BarChart.vue'

const store = useGarminStore()
const days = ref(30)
const healthPage = ref(1)
const healthPerPage = 15

const healthTotalPages = computed(() => Math.max(1, Math.ceil(store.dailyHealth.length / healthPerPage)))
const paginatedHealth = computed(() => store.dailyHealth.slice((healthPage.value - 1) * healthPerPage, healthPage.value * healthPerPage))
watch(days, () => { healthPage.value = 1 })

async function changeDays(d: number) {
  days.value = d
  await store.fetchDailyHealth(d)
}

// Données inversées (plus ancien → plus récent)
const reversed = computed(() => [...store.dailyHealth].reverse())

const stepsData = computed(() => ({
  labels: reversed.value.map(d => d.date?.slice(5)),
  values: reversed.value.map(d => d.steps ?? 0),
}))
const bbData      = computed(() => reversed.value.map(d => ({ x: d.date?.slice(5), y: d.body_battery_high ?? null })))
const stressData  = computed(() => reversed.value.map(d => ({ x: d.date?.slice(5), y: d.avg_stress ?? null })))
const rhrData     = computed(() => reversed.value.map(d => ({ x: d.date?.slice(5), y: d.resting_heart_rate ?? null })).filter(d => d.y))

const avgSteps  = computed(() => avg(store.dailyHealth, 'steps'))
const avgRHR    = computed(() => avg(store.dailyHealth.filter(d => d.resting_heart_rate), 'resting_heart_rate'))
const avgStress = computed(() => avg(store.dailyHealth.filter(d => d.avg_stress), 'avg_stress'))
const avgBB     = computed(() => avg(store.dailyHealth.filter(d => d.body_battery_high), 'body_battery_high'))

function avg(arr: any[], key: string) {
  if (!arr.length) return null
  return Math.round(arr.reduce((s, d) => s + (d[key] ?? 0), 0) / arr.length)
}

function intensityMin(d: any) {
  const mod = d.moderate_intensity_minutes ?? 0
  const vig = d.vigorous_intensity_minutes ?? 0
  if (!mod && !vig) return '—'
  return `${mod}m mod. ${vig}m vig.`
}

onMounted(() => store.fetchDailyHealth(30))
</script>

<style scoped>
.view { padding: 32px 40px; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
.view-title { font-size: 24px; font-weight: 600; }
.view-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.day-selector { display: flex; gap: 4px; }
.day-btn {
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: none;
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--mono);
  cursor: pointer;
  transition: all 0.15s;
}
.day-btn:hover { border-color: var(--teal); color: var(--teal); }
.day-btn.active { background: var(--teal-dim); border-color: var(--teal); color: var(--teal); }

.section { margin-bottom: 28px; }
.section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 14px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 12px 8px; }
.chart-empty { height: 140px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 13px; font-family: var(--mono); }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; }

.health-table { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.table-header, .table-row {
  display: grid;
  grid-template-columns: 1fr 1fr 0.8fr 1fr 1fr 1fr 1.5fr;
  gap: 8px;
  padding: 10px 16px;
  align-items: center;
}
.table-header { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); border-bottom: 1px solid var(--border); font-weight: 600; }
.table-row { font-size: 13px; border-bottom: 1px solid var(--border); transition: background 0.12s; }
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--surface-2); }
.mono { font-family: var(--mono); }
.muted { color: var(--text-muted); }
.text-teal { color: var(--teal); }
.text-orange { color: var(--orange); }
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 14px; }
.page-btn { padding: 6px 14px; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface); color: var(--text-muted); font-family: var(--mono); font-size: 12px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.page-btn:hover:not(:disabled) { border-color: var(--teal); color: var(--teal); }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.page-info { font-size: 12px; color: var(--text-muted); }
</style>
