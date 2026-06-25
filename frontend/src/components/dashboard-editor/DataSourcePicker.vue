<template>
  <div class="dsp">
    <div class="form-group">
      <label class="form-label">Source de données</label>
      <select v-model="selectedSource" class="form-field" @change="onSourceChange">
        <option value="" disabled>Choisir une source…</option>
        <optgroup v-for="group in DATA_SOURCES" :key="group.group" :label="group.group">
          <option v-for="item in group.items" :key="`${item.table}.${item.field}`" :value="`${item.table}.${item.field}`">
            {{ item.label }}
          </option>
        </optgroup>
      </select>
    </div>

    <div v-if="showActivityFilter" class="form-group">
      <label class="form-label">Filtrer par type d'activité</label>
      <input v-model="filterTypeText" class="form-field" placeholder="running, trail_running, ..." @input="onFilterChange" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const model = defineModel<Record<string, any>>({ default: () => ({}) })

const DATA_SOURCES = [
  {
    group: 'Activités',
    items: [
      { label: 'Distance (km)', table: 'activities', field: 'distance_meters', transform: 'divide_1000', unit: 'km' },
      { label: 'Durée (heures)', table: 'activities', field: 'duration_seconds', transform: 'divide_3600', unit: 'h' },
      { label: 'Calories brûlées', table: 'activities', field: 'calories', unit: 'kcal' },
      { label: 'Charge entraînement', table: 'activities', field: 'training_load', unit: '' },
      { label: 'VO2max', table: 'activities', field: 'vo2max', unit: '' },
      { label: 'FC moyenne', table: 'activities', field: 'avg_heart_rate', unit: 'bpm' },
    ],
  },
  {
    group: 'Santé quotidienne',
    items: [
      { label: 'Pas', table: 'daily_health', field: 'steps', unit: 'pas' },
      { label: 'Calories totales', table: 'daily_health', field: 'calories_total', unit: 'kcal' },
      { label: 'Body Battery (max)', table: 'daily_health', field: 'body_battery_high', unit: '' },
      { label: 'FC au repos', table: 'daily_health', field: 'resting_heart_rate', unit: 'bpm' },
      { label: 'Stress moyen', table: 'daily_health', field: 'avg_stress', unit: '' },
      { label: 'SpO2 moyen', table: 'daily_health', field: 'avg_spo2', unit: '%' },
    ],
  },
  {
    group: 'Sommeil',
    items: [
      { label: 'Score sommeil', table: 'sleep', field: 'sleep_score', unit: '' },
      { label: 'Durée sommeil (h)', table: 'sleep', field: 'duration_seconds', transform: 'divide_3600', unit: 'h' },
      { label: 'Sommeil profond (h)', table: 'sleep', field: 'deep_sleep_seconds', transform: 'divide_3600', unit: 'h' },
    ],
  },
  {
    group: 'HRV',
    items: [
      { label: 'HRV nuit (ms)', table: 'hrv', field: 'last_night_avg', unit: 'ms' },
      { label: 'HRV semaine (ms)', table: 'hrv', field: 'weekly_avg', unit: 'ms' },
    ],
  },
]

const selectedSource = ref('')
const filterTypeText = ref('')

const showActivityFilter = computed(() => {
  const parts = selectedSource.value.split('.')
  return parts[0] === 'activities'
})

function findSourceItem(key: string) {
  for (const group of DATA_SOURCES) {
    for (const item of group.items) {
      if (`${item.table}.${item.field}` === key) return item
    }
  }
  return null
}

function onSourceChange() {
  updateModel()
}

function onFilterChange() {
  updateModel()
}

function updateModel() {
  const item = findSourceItem(selectedSource.value)
  if (!item) return

  const query: Record<string, any> = {
    table: item.table,
    field: item.field,
  }
  if ('transform' in item && item.transform) {
    query.transform = item.transform
  }
  if (showActivityFilter.value && filterTypeText.value.trim()) {
    query.filter_type = filterTypeText.value.split(',').map(s => s.trim()).filter(Boolean)
  }
  model.value = query
}

watch(() => model.value, (val) => {
  if (val?.table && val?.field) {
    selectedSource.value = `${val.table}.${val.field}`
    if (val.filter_type) {
      filterTypeText.value = val.filter_type.join(', ')
    }
  }
}, { immediate: true })
</script>

<style scoped>
.dsp { display: flex; flex-direction: column; gap: 12px; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
.form-field { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 12px; color: var(--text); font-family: var(--sans); font-size: 13px; outline: none; }
.form-field:focus { border-color: var(--teal); }
</style>
