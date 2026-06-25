<template>
  <div class="view">

    <!-- Header avec retour ─────────────────────────────── -->
    <header class="view-header">
      <RouterLink to="/activities" class="back-btn">← Activités</RouterLink>
      <div v-if="loading" class="badge-loading">Chargement…</div>
    </header>

    <!-- Skeleton pendant le chargement ────────────────── -->
    <template v-if="loading">
      <SkeletonLoader type="kpi" :count="6" />
      <div style="margin-top:24px"><SkeletonLoader type="chart" /></div>
    </template>

    <!-- Contenu chargé ─────────────────────────────────── -->
    <template v-else-if="activity">

      <!-- Titre ──────────────────────────────────────────── -->
      <div class="act-title-row">
        <div class="act-type-badge-lg" :style="{ background: typeColor }">
          {{ typeIcon }}
        </div>
        <div>
          <h1 class="view-title">{{ activity.name || typeLabel }}</h1>
          <p class="act-date mono">{{ formatDate(activity.start_time) }}</p>
        </div>
      </div>

      <!-- KPIs principaux ────────────────────────────────── -->
      <section class="section">
        <div class="kpi-grid">
          <MetricCard label="Distance"   :value="distanceKm"   unit="km"    :decimals="2" accent="teal" />
          <MetricCard label="Durée"      :value="duration"                                accent="teal" />
          <MetricCard label="FC moyenne" :value="activity.avg_heart_rate" unit="bpm"     accent="orange" />
          <MetricCard label="FC max"     :value="activity.max_heart_rate" unit="bpm"     accent="orange" />
          <MetricCard label="Allure moy." v-if="isPace" :value="pace"                    accent="none" />
          <MetricCard label="Vitesse moy." v-else :value="speedKmh" unit="km/h" :decimals="1" accent="none" />
          <MetricCard label="Cadence"    :value="activity.avg_cadence" unit="spm"        accent="none" />
          <MetricCard label="Calories"   :value="activity.calories"    unit="kcal"       accent="none" />
          <MetricCard label="Charge"     :value="activity.training_load" :decimals="0"   accent="purple" />
        </div>
      </section>

      <!-- Carte GPS ─────────────────────────────────────── -->
      <ActivityMap v-if="activity?.has_gps" :garmin-id="(route.params.id as string)" />

      <!-- Effets d'entraînement ──────────────────────────── -->
      <section class="section" v-if="activity.aerobic_training_effect || activity.anaerobic_training_effect">
        <h2 class="section-title">Effets d'entraînement</h2>
        <div class="te-row">
          <div class="te-card">
            <div class="te-label">Aérobie</div>
            <div class="te-bar-wrap">
              <div class="te-bar teal" :style="{ width: (activity.aerobic_training_effect / 5 * 100) + '%' }"></div>
            </div>
            <div class="te-value mono">{{ activity.aerobic_training_effect?.toFixed(1) ?? '—' }} <span class="te-unit">/ 5</span></div>
          </div>
          <div class="te-card">
            <div class="te-label">Anaérobie</div>
            <div class="te-bar-wrap">
              <div class="te-bar orange" :style="{ width: (activity.anaerobic_training_effect / 5 * 100) + '%' }"></div>
            </div>
            <div class="te-value mono">{{ activity.anaerobic_training_effect?.toFixed(1) ?? '—' }} <span class="te-unit">/ 5</span></div>
          </div>
          <MetricCard label="VO2 max" :value="activity.vo2max" :decimals="1" sub="ml/kg/min" accent="purple" />
        </div>
      </section>

      <!-- Zones FC ───────────────────────────────────────── -->
      <section class="section" v-if="hrZones.length">
        <h2 class="section-title">Zones de fréquence cardiaque</h2>
        <div class="zones-layout">
          <div class="donut-wrap-outer">
            <DonutChart
              :labels="hrZones.map((z: any) => z.name)"
              :series="hrZones.map((z: any) => z.seconds)"
              :colors="hrZones.map((z: any) => z.color)"
              :height="240"
              center-label="Total"
              :center-value="duration"
            />
          </div>
          <div class="zones-list">
            <div v-for="z in hrZones" :key="z.name" class="zone-row">
              <span class="zone-dot" :style="{ background: z.color }"></span>
              <span class="zone-name">{{ z.name }}</span>
              <div class="zone-bar-wrap">
                <div class="zone-bar" :style="{ width: zonePercent(z.seconds) + '%', background: z.color }"></div>
              </div>
              <span class="zone-time mono">{{ fmtSec(z.seconds) }}</span>
              <span class="zone-pct mono muted">{{ zonePercent(z.seconds) }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Splits ─────────────────────────────────────────── -->
      <section class="section" v-if="splits.length">
        <h2 class="section-title">Splits</h2>
        <div class="splits-table">
          <div class="table-header">
            <span>#</span>
            <span>Distance</span>
            <span>Temps</span>
            <span>{{ isPace ? 'Allure' : 'Vitesse' }}</span>
            <span>FC moy.</span>
            <span>Cadence</span>
            <span>D+</span>
          </div>
          <div v-for="s in splits" :key="s.index" class="table-row">
            <span class="mono muted">{{ s.index }}</span>
            <span class="mono">{{ s.distance_meters ? (s.distance_meters / 1000).toFixed(2) + ' km' : '—' }}</span>
            <span class="mono">{{ fmtSec(s.duration_seconds) }}</span>
            <span class="mono text-teal">{{ splitPaceOrSpeed(s) }}</span>
            <span class="mono text-orange">{{ s.avg_heart_rate ? s.avg_heart_rate + ' bpm' : '—' }}</span>
            <span class="mono">{{ s.avg_cadence ?? '—' }}</span>
            <span class="mono muted">{{ s.elevation_gain != null ? '+' + Math.round(s.elevation_gain) + 'm' : '—' }}</span>
          </div>
        </div>
      </section>

      <!-- Données élévation / puissance ──────────────────── -->
      <section class="section" v-if="timeline">
        <h2 class="section-title">Données supplémentaires</h2>
        <div class="kpi-grid">
          <MetricCard v-if="timeline.elevation_gain" label="D+ total"       :value="timeline.elevation_gain"        unit="m"   :decimals="0" accent="none" />
          <MetricCard v-if="timeline.elevation_loss" label="D- total"       :value="timeline.elevation_loss"        unit="m"   :decimals="0" accent="none" />
          <MetricCard v-if="timeline.max_elevation"  label="Altitude max"   :value="timeline.max_elevation"         unit="m"   :decimals="0" accent="none" />
          <MetricCard v-if="timeline.avg_power"      label="Puissance moy." :value="timeline.avg_power"             unit="W"   :decimals="0" accent="purple" />
          <MetricCard v-if="timeline.normalized_power" label="NP"           :value="timeline.normalized_power"      unit="W"   :decimals="0" accent="purple" />
          <MetricCard v-if="timeline.training_stress_score" label="TSS"     :value="timeline.training_stress_score" :decimals="0" accent="purple" />
        </div>
      </section>

    </template>

    <!-- État erreur ────────────────────────────────────── -->
    <div v-else class="error-state">
      <p>Activité introuvable.</p>
      <RouterLink to="/activities" class="back-btn">← Retour</RouterLink>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import api from '@/api'
import MetricCard from '../components/cards/MetricCard.vue'
import DonutChart from '../components/charts/DonutChart.vue'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import ActivityMap from '../components/maps/ActivityMap.vue'

const route    = useRoute()
const activity = ref<any>(null)
const loading  = ref(true)

// ── Fetch ──────────────────────────────────────────────
onMounted(async () => {
  try {
    const { data } = await api.get(`/activities/${route.params.id}`)
    activity.value = data
  } finally {
    loading.value = false
  }
})

// ── Type helpers ───────────────────────────────────────
const TYPE_MAP: Record<string, { icon: string; label: string; color: string }> = {
  running:           { icon: '🏃', label: 'Course',         color: 'rgba(0,212,170,0.15)' },
  cycling:           { icon: '🚴', label: 'Vélo',           color: 'rgba(124,111,205,0.15)' },
  swimming:          { icon: '🏊', label: 'Natation',       color: 'rgba(30,130,230,0.15)' },
  walking:           { icon: '🚶', label: 'Marche',         color: 'rgba(139,146,165,0.15)' },
  strength_training: { icon: '🏋️', label: 'Musculation',   color: 'rgba(255,107,53,0.15)' },
}

const typeData  = computed(() => TYPE_MAP[activity.value?.activity_type] ?? { icon: '⬡', label: activity.value?.activity_type ?? '—', color: 'rgba(139,146,165,0.1)' })
const typeIcon  = computed(() => typeData.value.icon)
const typeLabel = computed(() => typeData.value.label)
const typeColor = computed(() => typeData.value.color)
const isPace    = computed(() => ['running', 'walking'].includes(activity.value?.activity_type))

// ── Computed metrics ───────────────────────────────────
const distanceKm = computed(() =>
  activity.value?.distance_meters ? activity.value.distance_meters / 1000 : null
)

const duration = computed(() => fmtSec(activity.value?.duration_seconds))

const pace = computed(() => {
  const a = activity.value
  if (!a?.distance_meters || !a?.duration_seconds) return '—'
  const secPerKm = a.duration_seconds / (a.distance_meters / 1000)
  const m = Math.floor(secPerKm / 60), s = Math.round(secPerKm % 60)
  return `${m}:${s.toString().padStart(2, '0')}/km`
})

const speedKmh = computed(() => {
  const speed = activity.value?.avg_speed
  return speed ? speed * 3.6 : null
})

const hrZones   = computed(() => activity.value?.hr_zones_detail ?? [])
const splits    = computed(() => activity.value?.splits ?? [])
const timeline  = computed(() => activity.value?.metrics_timeline)

const totalZoneSeconds = computed(() => hrZones.value.reduce((s: number, z: any) => s + z.seconds, 0))

// ── Helpers ────────────────────────────────────────────
function zonePercent(sec: number): number {
  const total = totalZoneSeconds.value
  return total ? Math.round((sec / total) * 100) : 0
}

function fmtSec(s: number | null | undefined): string {
  if (!s) return '—'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60)
  return h > 0
    ? `${h}:${m.toString().padStart(2,'0')}:${sec.toString().padStart(2,'0')}`
    : `${m}:${sec.toString().padStart(2,'0')}`
}

function splitPaceOrSpeed(s: any): string {
  if (!s.duration_seconds || !s.distance_meters) return '—'
  if (isPace.value) {
    const secPerKm = s.duration_seconds / (s.distance_meters / 1000)
    const m = Math.floor(secPerKm / 60), sec = Math.round(secPerKm % 60)
    return `${m}:${sec.toString().padStart(2,'0')}/km`
  }
  return ((s.distance_meters / s.duration_seconds) * 3.6).toFixed(1) + ' km/h'
}

function formatDate(dt: string): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.view { padding: 32px 40px; }

.view-header { margin-bottom: 24px; display: flex; align-items: center; gap: 16px; }
.back-btn {
  font-size: 13px;
  color: var(--text-muted);
  text-decoration: none;
  font-family: var(--mono);
  transition: color 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.back-btn:hover { color: var(--teal); }
.badge-loading { font-size: 12px; font-family: var(--mono); padding: 4px 12px; background: var(--teal-dim); color: var(--teal); border-radius: 20px; }

.act-title-row { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
.act-type-badge-lg { width: 52px; height: 52px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
.view-title { font-size: 24px; font-weight: 600; }
.act-date { font-size: 13px; color: var(--text-muted); margin-top: 4px; text-transform: capitalize; }

.section { margin-bottom: 28px; }
.section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 14px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }

/* Training Effect */
.te-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: 12px; align-items: start; }
.te-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }
.te-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.te-bar-wrap { height: 6px; background: var(--surface-2); border-radius: 3px; overflow: hidden; }
.te-bar { height: 100%; border-radius: 3px; transition: width 0.8s cubic-bezier(0.4,0,0.2,1); }
.te-bar.teal   { background: var(--teal); }
.te-bar.orange { background: var(--orange); }
.te-value { font-family: var(--mono); font-size: 22px; font-weight: 500; }
.te-unit { font-size: 13px; color: var(--text-muted); }

/* Zones FC */
.zones-layout { display: grid; grid-template-columns: 260px 1fr; gap: 24px; align-items: start; }
.donut-wrap-outer { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 12px; }
.zones-list { display: flex; flex-direction: column; gap: 10px; }
.zone-row { display: grid; grid-template-columns: 10px 56px 1fr 52px 40px; align-items: center; gap: 10px; }
.zone-dot { width: 10px; height: 10px; border-radius: 50%; }
.zone-name { font-size: 13px; color: var(--text-muted); }
.zone-bar-wrap { height: 6px; background: var(--surface-2); border-radius: 3px; overflow: hidden; }
.zone-bar { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.zone-time { font-size: 13px; text-align: right; }
.zone-pct  { font-size: 12px; text-align: right; }

/* Splits */
.splits-table { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.table-header, .table-row {
  display: grid;
  grid-template-columns: 32px 1fr 1fr 1.2fr 1fr 0.8fr 0.8fr;
  gap: 8px; padding: 10px 16px; align-items: center;
}
.table-header { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); border-bottom: 1px solid var(--border); font-weight: 600; }
.table-row { font-size: 13px; border-bottom: 1px solid var(--border); transition: background 0.12s; }
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--surface-2); }
.mono { font-family: var(--mono); }
.muted { color: var(--text-muted); }
.text-teal   { color: var(--teal); }
.text-orange { color: var(--orange); }

.error-state { padding: 64px 32px; text-align: center; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 16px; }

@media (max-width: 768px) {
  .view { padding: 16px 12px; }
  .view-title { font-size: 20px; }
  .act-title-row { gap: 12px; margin-bottom: 20px; }
  .act-type-badge-lg { width: 44px; height: 44px; font-size: 20px; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .te-row { grid-template-columns: 1fr; }
  .zones-layout { grid-template-columns: 1fr; gap: 16px; }
  .zone-row { grid-template-columns: 10px 50px 1fr 44px 36px; gap: 6px; }
  .splits-table { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .table-header, .table-row { min-width: 500px; }
  .section { margin-bottom: 20px; }
}
</style>
