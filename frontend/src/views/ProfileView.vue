<template>
  <div class="view">

    <!-- Header ─────────────────────────────────────────── -->
    <header class="view-header">
      <div>
        <h1 class="view-title">Profil</h1>
        <p class="view-sub mono">Forme · Charge · Récupération</p>
      </div>
    </header>

    <!-- Compte ─────────────────────────────────────────── -->
    <section class="section">
      <h2 class="section-title">Compte</h2>
      <div class="account-card">
        <div class="account-row">
          <span class="account-label">Email</span>
          <span class="account-value mono">{{ authStore.user?.email }}</span>
        </div>

        <h3 class="subsection-title">Identifiants Garmin Connect</h3>

        <div v-if="authStore.user?.has_garmin_credentials && !showGarminForm" class="garmin-status">
          <span class="garmin-connected mono">{{ authStore.user?.garmin_email }}</span>
          <div class="garmin-actions">
            <button class="btn-sm" @click="showGarminForm = true">Modifier</button>
            <button class="btn-sm btn-danger" @click="handleDeleteGarmin">Supprimer</button>
          </div>
        </div>

        <div v-else-if="!showGarminForm" class="garmin-status">
          <span class="garmin-not-connected">Non connecté</span>
          <button class="btn-sm" @click="showGarminForm = true">Configurer</button>
        </div>

        <form v-if="showGarminForm" @submit.prevent="handleSaveGarmin" class="garmin-form">
          <div class="field-inline">
            <input v-model="garminEmail" type="email" placeholder="Email Garmin" required />
            <input v-model="garminPassword" type="password" placeholder="Mot de passe Garmin" required />
          </div>
          <div class="garmin-form-actions">
            <button type="submit" class="btn-sm btn-primary" :disabled="savingGarmin">
              {{ savingGarmin ? 'Enregistrement…' : 'Enregistrer' }}
            </button>
            <button type="button" class="btn-sm" @click="showGarminForm = false">Annuler</button>
          </div>
          <p v-if="garminMsg" class="garmin-msg" :class="garminMsgType">{{ garminMsg }}</p>
        </form>
      </div>
    </section>

    <!-- Skeleton ────────────────────────────────────────── -->
    <template v-if="store.loading">
      <SkeletonLoader type="kpi" :count="5" />
      <div style="margin-top:24px"><SkeletonLoader type="chart" /></div>
      <div style="margin-top:24px"><SkeletonLoader type="chart" /></div>
    </template>

    <template v-else-if="store.data">
      <!-- Score de forme ───────────────────────────────── -->
      <section class="section">
        <div class="fitness-hero">
          <div class="score-ring-wrap">
            <svg viewBox="0 0 120 120" class="score-ring">
              <circle cx="60" cy="60" r="52" fill="none" stroke="var(--surface-2)" stroke-width="10"/>
              <circle
                cx="60" cy="60" r="52" fill="none"
                :stroke="scoreColor"
                stroke-width="10"
                stroke-linecap="round"
                :stroke-dasharray="`${scoreArc} 327`"
                stroke-dashoffset="82"
                style="transition: stroke-dasharray 1s ease"
              />
            </svg>
            <div class="score-center">
              <span class="score-val mono">{{ fitness.score }}</span>
              <span class="score-label">Forme</span>
            </div>
          </div>
          <div class="fitness-metrics">
            <div class="fm-item">
              <span class="fm-label">CTL <span class="fm-hint">(charge chronique)</span></span>
              <span class="fm-value mono">{{ fitness.ctl ?? '—' }}</span>
            </div>
            <div class="fm-item">
              <span class="fm-label">ATL <span class="fm-hint">(charge aiguë)</span></span>
              <span class="fm-value mono">{{ fitness.atl ?? '—' }}</span>
            </div>
            <div class="fm-item">
              <span class="fm-label">TSB <span class="fm-hint">(fraîcheur)</span></span>
              <span class="fm-value mono" :class="tsbClass">{{ fitness.tsb != null ? (fitness.tsb > 0 ? '+' : '') + fitness.tsb : '—' }}</span>
            </div>
            <div class="fm-item">
              <span class="fm-label">HRV moy. 7j</span>
              <span class="fm-value mono">{{ fitness.hrv_avg_7d ?? '—' }} <span class="fm-unit">ms</span></span>
            </div>
            <div class="fm-item">
              <span class="fm-label">HRV baseline 42j</span>
              <span class="fm-value mono">{{ fitness.hrv_baseline_42d ?? '—' }} <span class="fm-unit">ms</span></span>
            </div>
            <div class="fm-item">
              <span class="fm-label">Sommeil moy. 7j</span>
              <span class="fm-value mono">{{ fitness.sleep_score_avg_7d ?? '—' }} <span class="fm-unit">/ 100</span></span>
            </div>
          </div>
        </div>
      </section>

      <!-- Série + Records ──────────────────────────────── -->
      <div class="two-col">
        <section class="section">
          <h2 class="section-title">Activité</h2>
          <div class="streak-cards">
            <div class="streak-card">
              <div class="streak-num mono">{{ streak.current_streak }}</div>
              <div class="streak-label">Jours consécutifs</div>
            </div>
            <div class="streak-card">
              <div class="streak-num mono">{{ streak.best_streak_90d }}</div>
              <div class="streak-label">Meilleure série (90j)</div>
            </div>
          </div>
        </section>

        <section class="section">
          <h2 class="section-title">Records personnels</h2>
          <div class="pb-list">
            <div v-for="(val, key) in bests" :key="key" class="pb-row">
              <span class="pb-key">{{ pbLabel(key) }}</span>
              <span class="pb-val mono">{{ pbValue(key, val) }}</span>
              <span class="pb-date mono muted">{{ val.date }}</span>
            </div>
            <div v-if="!Object.keys(bests).length" class="empty-hint">Pas encore de records</div>
          </div>
        </section>
      </div>

      <!-- VO2max ───────────────────────────────────────── -->
      <section class="section" v-if="vo2maxSeries.categories.length">
        <h2 class="section-title">VO2max — évolution</h2>
        <div class="chart-card">
          <LineChart
            :series="[{ name: 'VO2max (ml/kg/min)', data: vo2maxSeries.values, color: '#7C6FCD' }]"
            :categories="vo2maxSeries.categories"
            :height="180"
            unit=" ml/kg/min"
          />
        </div>
      </section>

      <!-- Charge CTL / ATL ─────────────────────────────── -->
      <section class="section" v-if="loadBalance.length">
        <h2 class="section-title">Charge d'entraînement — CTL / ATL (16 semaines)</h2>
        <div class="chart-card">
          <LineChart
            :series="[
              { name: 'CTL (forme)', data: loadBalance.map((d: any) => d.ctl), color: '#00D4AA' },
              { name: 'ATL (fatigue)', data: loadBalance.map((d: any) => d.atl), color: '#FF6B35' },
            ]"
            :categories="loadBalance.map((d: any) => d.date?.slice(5))"
            :height="200"
          />
        </div>
        <p class="chart-note">CTL = charge sur 42j · ATL = charge sur 7j · TSB = CTL − ATL (positif = frais, négatif = fatigué)</p>
      </section>

      <!-- FC repos + HRV + Body Battery ───────────────── -->
      <div class="two-col">
        <section class="section" v-if="rhrTrend.length">
          <h2 class="section-title">FC repos — 90 jours</h2>
          <div class="chart-card">
            <LineChart
              :series="[
                { name: 'FC repos', data: rhrTrend.map((d: any) => d.rhr), color: '#4A5168' },
                { name: 'Moy. 7j', data: rhrTrend.map((d: any) => d.rhr_ma7), color: '#FF6B35' },
              ]"
              :categories="rhrTrend.map((d: any) => d.date?.slice(5))"
              :height="180"
              unit=" bpm"
            />
          </div>
        </section>

        <section class="section" v-if="recoveryTrend.length">
          <h2 class="section-title">Récupération — 30 jours</h2>
          <div class="chart-card">
            <LineChart
              :series="[
                { name: 'Body Battery', data: recoveryTrend.map((d: any) => d.body_battery), color: '#00D4AA' },
                { name: 'HRV (ms)', data: recoveryTrend.map((d: any) => d.hrv), color: '#7C6FCD' },
              ]"
              :categories="recoveryTrend.map((d: any) => d.date?.slice(5))"
              :height="180"
            />
          </div>
        </section>
      </div>

      <!-- Sommeil ──────────────────────────────────────── -->
      <section class="section" v-if="sleepTrend.length">
        <h2 class="section-title">Sommeil — score & durée (30j)</h2>
        <div class="chart-card">
          <LineChart
            :series="[
              { name: 'Score', data: sleepTrend.map((d: any) => d.score), color: '#7C6FCD' },
              { name: 'Durée (h)', data: sleepTrend.map((d: any) => d.duration_h), color: '#3B5B8F' },
            ]"
            :categories="sleepTrend.map((d: any) => d.date?.slice(5))"
            :height="180"
          />
        </div>
      </section>

    </template>

    <div v-else-if="store.error" class="error-state">{{ store.error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfileStore } from '../stores/profile'
import { useAuthStore } from '../stores/auth'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import LineChart from '../components/charts/LineChart.vue'

const store = useProfileStore()
const authStore = useAuthStore()

const showGarminForm = ref(false)
const garminEmail = ref('')
const garminPassword = ref('')
const savingGarmin = ref(false)
const garminMsg = ref('')
const garminMsgType = ref('')

async function handleSaveGarmin() {
  savingGarmin.value = true
  garminMsg.value = ''
  try {
    const result = await authStore.updateGarminCredentials(garminEmail.value, garminPassword.value)
    showGarminForm.value = false
    garminEmail.value = ''
    garminPassword.value = ''
    garminMsg.value = result.credentials_valid ? 'Identifiants valides' : 'Identifiants sauvegardés (connexion Garmin non vérifiée)'
    garminMsgType.value = result.credentials_valid ? 'success' : 'warning'
  } catch {
    garminMsg.value = 'Erreur lors de la sauvegarde'
    garminMsgType.value = 'error'
  } finally {
    savingGarmin.value = false
  }
}

async function handleDeleteGarmin() {
  await authStore.deleteGarminCredentials()
}

const fitness       = computed(() => store.data?.fitness_score ?? {})
const vo2maxHistory = computed(() => store.data?.vo2max_history ?? [])
const loadBalance   = computed(() => store.data?.load_balance ?? [])
const recoveryTrend = computed(() => store.data?.recovery_trend ?? [])
const rhrTrend      = computed(() => store.data?.rhr_trend ?? [])
const sleepTrend    = computed(() => store.data?.sleep_trend ?? [])
const bests         = computed(() => store.data?.personal_bests ?? {})
const streak        = computed(() => store.data?.activity_streak ?? { current_streak: 0, best_streak_90d: 0 })

// Score anneau SVG
const scoreArc    = computed(() => Math.round((fitness.value.score ?? 0) / 100 * 327))
const scoreColor  = computed(() => {
  const s = fitness.value.score ?? 0
  if (s >= 75) return 'var(--teal)'
  if (s >= 50) return '#F59E0B'
  return 'var(--orange)'
})
const tsbClass    = computed(() => {
  const tsb = fitness.value.tsb
  if (tsb == null) return ''
  if (tsb > 5)  return 'text-teal'
  if (tsb < -10) return 'text-orange'
  return ''
})

// VO2max
const vo2maxSeries = computed(() => ({
  categories: vo2maxHistory.value.map((d: any) => d.date?.slice(5)),
  values:     vo2maxHistory.value.map((d: any) => d.vo2max),
}))

// Records labels
const PB_LABELS: Record<string, string> = {
  running_max_distance: 'Course — distance max',
  cycling_max_distance: 'Vélo — distance max',
  swimming_max_distance: 'Natation — distance max',
  vo2max_best: 'VO2max record',
}
function pbLabel(key: string | number | symbol) { return PB_LABELS[String(key)] ?? String(key) }
function pbValue(key: string | number | symbol, val: any) {
  if (String(key) === "vo2max_best") return `${val.value} ml/kg/min`
  return `${val.value_km} km`
}

onMounted(() => store.fetchProfile())
</script>

<style scoped>
.view { padding: 32px 40px; }
.view-header { margin-bottom: 28px; }
.view-title { font-size: 24px; font-weight: 600; }
.view-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.section { margin-bottom: 28px; }
.section-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 14px; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; }
.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px 12px 8px; }
.chart-note { font-size: 12px; color: var(--text-muted); font-family: var(--mono); margin-top: 8px; text-align: center; }

/* Score de forme */
.fitness-hero { display: grid; grid-template-columns: 240px 1fr; gap: 32px; align-items: start; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 28px; }
.score-ring-wrap { position: relative; width: 140px; margin: 0 auto; }
.score-ring { width: 140px; height: 140px; transform: rotate(-90deg); }
.score-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.score-val { display: block; font-size: 36px; font-weight: 500; color: var(--text); line-height: 1; }
.score-label { display: block; font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }

.fitness-metrics { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.fm-item { display: flex; flex-direction: column; gap: 4px; }
.fm-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.fm-hint { font-size: 11px; color: var(--text-dim); text-transform: none; letter-spacing: 0; }
.fm-value { font-size: 22px; font-family: var(--mono); font-weight: 500; color: var(--text); }
.fm-unit { font-size: 12px; color: var(--text-muted); }

/* Série */
.streak-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.streak-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; text-align: center; }
.streak-num { font-size: 40px; font-weight: 500; color: var(--teal); }
.streak-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }

/* Records */
.pb-list { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.pb-row { display: grid; grid-template-columns: 1fr auto auto; gap: 12px; padding: 11px 16px; border-bottom: 1px solid var(--border); align-items: center; font-size: 13px; }
.pb-row:last-child { border-bottom: none; }
.pb-key { color: var(--text-muted); }
.pb-val { font-family: var(--mono); color: var(--teal); }
.pb-date { font-size: 12px; }
.empty-hint { padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px; font-family: var(--mono); }

.mono { font-family: var(--mono); }
.muted { color: var(--text-muted); }
.text-teal { color: var(--teal); }
.text-orange { color: var(--orange); }
/* Compte */
.account-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; }
.account-row { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
.account-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.account-value { font-size: 14px; color: var(--text); }
.subsection-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 600; margin-bottom: 12px; }
.garmin-status { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.garmin-connected { font-size: 14px; color: var(--teal); }
.garmin-not-connected { font-size: 13px; color: var(--text-muted); }
.garmin-actions { display: flex; gap: 8px; }
.garmin-form { margin-top: 12px; }
.field-inline { display: flex; gap: 8px; margin-bottom: 12px; }
.field-inline input { flex: 1; padding: 9px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text); font-family: var(--mono); font-size: 13px; outline: none; }
.field-inline input:focus { border-color: var(--teal); }
.field-inline input::placeholder { color: var(--text-dim); }
.garmin-form-actions { display: flex; gap: 8px; }
.garmin-msg { font-size: 12px; font-family: var(--mono); margin-top: 8px; padding: 6px 10px; border-radius: var(--radius); }
.garmin-msg.success { color: var(--teal); background: rgba(0, 212, 170, 0.08); }
.garmin-msg.warning { color: #F59E0B; background: rgba(245, 158, 11, 0.08); }
.garmin-msg.error { color: var(--orange); background: rgba(255, 107, 53, 0.08); }
.btn-sm { padding: 6px 14px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-family: var(--sans); font-size: 12px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.btn-sm:hover { border-color: var(--teal); color: var(--teal); }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--teal); color: #000; border-color: var(--teal); }
.btn-primary:hover { opacity: 0.9; color: #000; border-color: var(--teal); }
.btn-danger:hover { border-color: var(--orange); color: var(--orange); }

.error-state { padding: 64px; text-align: center; color: var(--text-muted); }

@media (max-width: 900px) {
  .two-col { grid-template-columns: 1fr; }
  .fitness-hero { grid-template-columns: 1fr; }
  .fitness-metrics { grid-template-columns: 1fr 1fr; }
  .view { padding: 20px 16px; }
}
</style>
