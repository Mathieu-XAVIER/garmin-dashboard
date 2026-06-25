<template>
  <div class="view">
    <header class="view-header">
      <div>
        <h1 class="view-title">Sommeil</h1>
        <p class="view-sub mono">Analyse des nuits</p>
      </div>
      <div class="last-night" v-if="store.latestSleep">
        <span class="ln-label">Dernière nuit</span>
        <span class="ln-score mono" :class="scoreClass">{{ store.latestSleep.sleep_score ?? '—' }}</span>
        <span class="ln-unit">/ 100</span>
      </div>
    </header>

    <!-- KPIs sommeil ───────────────────────────────────── -->
    <section class="section">
      <div class="kpi-grid">
        <MetricCard label="Durée moy." :value="avgDuration" accent="teal" />
        <MetricCard label="Score moy." :value="avgScore" sub="/ 100" accent="teal" />
        <MetricCard label="Sommeil profond moy." :value="avgDeep" accent="purple" />
        <MetricCard label="REM moy." :value="avgRem" accent="purple" />
        <MetricCard label="SpO2 moy." :value="avgSpo2" unit="%" :decimals="1" accent="none" />
      </div>
    </section>

    <!-- Score de sommeil ────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Score de sommeil — 30 jours</h2>
      <div class="chart-card">
        <AreaChart
          v-if="scoreData.length"
          :data="scoreData"
          label="Score"
          color="#7C6FCD"
          :height="160"
          :yMin="0"
          :yMax="100"
        />
        <div v-else class="chart-empty">Pas de données</div>
      </div>
    </section>

    <!-- Phases de sommeil ──────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Phases de sommeil (heures)</h2>
      <div class="chart-card">
        <BarChart
          v-if="phasesData.labels.length"
          :categories="phasesData.labels"
          :series="phasesData.series"
          :height="200"
          unit="h"
          :stacked="true"
        />
        <div v-else class="chart-empty">Pas de données</div>
      </div>
    </section>

    <!-- Tableau détail ─────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Détail des nuits</h2>
      <div class="sleep-table">
        <div class="table-header">
          <span>Date</span>
          <span>Score</span>
          <span>Durée</span>
          <span>Profond</span>
          <span>Léger</span>
          <span>REM</span>
          <span>Éveillé</span>
          <span>SpO2</span>
        </div>
        <div v-for="s in store.sleepHistory" :key="s.date" class="table-row">
          <span class="mono muted">{{ s.date }}</span>
          <span class="mono" :class="scoreColor(s.sleep_score)">{{ s.sleep_score ?? '—' }}</span>
          <span class="mono">{{ fmtSec(s.duration_seconds) }}</span>
          <span class="mono deep">{{ fmtSec(s.deep_sleep_seconds) }}</span>
          <span class="mono light">{{ fmtSec(s.light_sleep_seconds) }}</span>
          <span class="mono rem">{{ fmtSec(s.rem_sleep_seconds) }}</span>
          <span class="mono muted">{{ fmtSec(s.awake_seconds) }}</span>
          <span class="mono">{{ s.avg_spo2 ? s.avg_spo2.toFixed(1) + '%' : '—' }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useGarminStore } from '../stores/garmin'
import MetricCard from '../components/cards/MetricCard.vue'
import AreaChart from '../components/charts/AreaChart.vue'
import BarChart from '../components/charts/BarChart.vue'

const store = useGarminStore()

const reversed = computed(() => [...store.sleepHistory].reverse())

const scoreData  = computed(() => reversed.value.map(s => ({ x: s.date?.slice(5), y: s.sleep_score ?? null })))

const phasesData = computed(() => ({
  labels: reversed.value.map(s => s.date?.slice(5)),
  series: [
    { name: 'Profond', data: reversed.value.map(s => +(((s.deep_sleep_seconds ?? 0) / 3600).toFixed(2))), color: '#7C6FCD' },
    { name: 'REM',     data: reversed.value.map(s => +(((s.rem_sleep_seconds ?? 0) / 3600).toFixed(2))), color: '#00D4AA' },
    { name: 'Léger',   data: reversed.value.map(s => +(((s.light_sleep_seconds ?? 0) / 3600).toFixed(2))), color: '#3B5B8F' },
    { name: 'Éveillé', data: reversed.value.map(s => +(((s.awake_seconds ?? 0) / 3600).toFixed(2))), color: '#252C3D' },
  ],
}))

function avg(key: string, filter = true) {
  const data = store.sleepHistory.filter(s => s[key] != null)
  if (!data.length) return null
  return Math.round(data.reduce((s, d) => s + d[key], 0) / data.length)
}

const avgScore    = computed(() => avg('sleep_score'))
const avgDeep     = computed(() => { const v = avg('deep_sleep_seconds'); return v ? fmtSec(v) : null })
const avgRem      = computed(() => { const v = avg('rem_sleep_seconds'); return v ? fmtSec(v) : null })
const avgDuration = computed(() => { const v = avg('duration_seconds'); return v ? fmtSec(v) : null })
const avgSpo2     = computed(() => {
  const data = store.sleepHistory.filter(s => s.avg_spo2)
  return data.length ? +(data.reduce((s, d) => s + d.avg_spo2, 0) / data.length).toFixed(1) : null
})

const scoreClass = computed(() => scoreColor(store.latestSleep?.sleep_score))

function scoreColor(score: number | null) {
  if (!score) return ''
  if (score >= 80) return 'text-teal'
  if (score >= 60) return 'text-muted'
  return 'text-orange'
}

function fmtSec(s: number | null): string {
  if (!s) return '—'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}h${m.toString().padStart(2,'0')}` : `${m}min`
}

onMounted(() => store.fetchSleepHistory(30))
</script>

<style scoped>
.view { padding: 32px 40px; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
.view-title { font-size: 24px; font-weight: 600; }
.view-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.last-night { display: flex; align-items: baseline; gap: 6px; padding: 10px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); }
.ln-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.ln-score { font-size: 32px; font-family: var(--mono); font-weight: 500; }
.ln-unit  { font-size: 13px; color: var(--text-muted); }
.text-teal { color: var(--teal); }
.text-orange { color: var(--orange); }
.text-muted { color: var(--text-muted); }

.section { margin-bottom: 28px; }
.section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 14px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; }
.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 12px 8px; }
.chart-empty { height: 140px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 13px; font-family: var(--mono); }

.sleep-table { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.table-header, .table-row {
  display: grid;
  grid-template-columns: 1fr 0.7fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr;
  gap: 8px; padding: 10px 16px; align-items: center;
}
.table-header { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); border-bottom: 1px solid var(--border); font-weight: 600; }
.table-row { font-size: 13px; border-bottom: 1px solid var(--border); transition: background 0.12s; }
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--surface-2); }
.mono { font-family: var(--mono); }
.muted { color: var(--text-muted); }
.deep  { color: var(--purple); }
.rem   { color: var(--teal); }
.light { color: #3B5B8F; }
</style>
