<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-panel">
      <div class="modal-header">
        <h2 class="modal-title">{{ step === 'type' ? 'Ajouter un widget' : 'Configurer le widget' }}</h2>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <!-- Étape 1 : choix du type -->
      <div v-if="step === 'type'" class="modal-body">
        <div class="type-grid">
          <button v-for="t in widgetTypes" :key="t.id" class="type-card" @click="selectType(t.id)">
            <span class="type-icon">{{ t.icon }}</span>
            <span class="type-name">{{ t.name }}</span>
            <span class="type-desc">{{ t.desc }}</span>
          </button>
        </div>
      </div>

      <!-- Étape 2 : configuration -->
      <div v-else class="modal-body">
        <div class="form-group">
          <label class="form-label">Titre</label>
          <input v-model="title" class="form-field" :placeholder="selectedType?.name" />
        </div>

        <div class="form-group">
          <label class="form-label">Largeur</label>
          <select v-model="width" class="form-field">
            <option value="quarter">1/4</option>
            <option value="half">1/2</option>
            <option value="full">Pleine largeur</option>
          </select>
        </div>

        <!-- Config Objectif -->
        <template v-if="selectedTypeId === 'objective'">
          <div class="form-group">
            <label class="form-label">Source</label>
            <select v-model="objSource" class="form-field">
              <option value="garmin">Données Garmin</option>
              <option value="exercise">Exercice personnalisé</option>
            </select>
          </div>
          <template v-if="objSource === 'garmin'">
            <DataSourcePicker v-model="garminQuery" />
          </template>
          <template v-else>
            <div class="form-group">
              <label class="form-label">Type d'exercice</label>
              <input v-model="exerciseType" class="form-field" placeholder="ex: pompes" />
            </div>
          </template>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Objectif</label>
              <input v-model.number="targetValue" type="number" class="form-field" min="0" />
            </div>
            <div class="form-group">
              <label class="form-label">Unité</label>
              <input v-model="unit" class="form-field" placeholder="km, reps..." />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Icône</label>
              <input v-model="icon" class="form-field" placeholder="🏃" maxlength="4" style="width:60px;text-align:center;font-size:20px" />
            </div>
            <div class="form-group">
              <label class="form-label">Agrégation</label>
              <select v-model="aggregation" class="form-field">
                <option value="sum">Somme</option>
                <option value="max">Maximum</option>
                <option value="avg">Moyenne</option>
              </select>
            </div>
          </div>
        </template>

        <!-- Config Métrique -->
        <template v-if="selectedTypeId === 'metric'">
          <DataSourcePicker v-model="garminQuery" />
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Unité</label>
              <input v-model="unit" class="form-field" placeholder="pas, bpm..." />
            </div>
            <div class="form-group">
              <label class="form-label">Accent</label>
              <select v-model="accent" class="form-field">
                <option value="teal">Teal</option>
                <option value="orange">Orange</option>
                <option value="purple">Violet</option>
                <option value="none">Aucun</option>
              </select>
            </div>
          </div>
        </template>

        <!-- Config Graphique -->
        <template v-if="selectedTypeId === 'chart'">
          <div class="form-group">
            <label class="form-label">Type de graphique</label>
            <select v-model="chartType" class="form-field">
              <option value="area">Aire</option>
              <option value="bar">Barres</option>
              <option value="line">Ligne</option>
              <option value="donut">Donut</option>
            </select>
          </div>
          <DataSourcePicker v-model="garminQuery" />
        </template>

        <!-- Config Exercise Tracker -->
        <template v-if="selectedTypeId === 'exercise_tracker'">
          <div class="form-group">
            <label class="form-label">Exercices (un par ligne : type,label,icône,objectif)</label>
            <textarea v-model="exercisesText" class="form-field form-textarea" rows="4" placeholder="pompes,Pompes,💪,30&#10;squats,Squats,🦵,50"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">
              <input type="checkbox" v-model="showInputForm" /> Formulaire de saisie
            </label>
          </div>
          <div class="form-group">
            <label class="form-label">
              <input type="checkbox" v-model="showWeeklyBreakdown" /> Suivi semaine par semaine
            </label>
          </div>
        </template>

        <!-- Config Liste d'activités -->
        <template v-if="selectedTypeId === 'activity_list'">
          <div class="form-group">
            <label class="form-label">Types d'activités (séparés par des virgules)</label>
            <input v-model="filterTypesText" class="form-field" placeholder="running, trail_running" />
          </div>
          <div class="form-group">
            <label class="form-label">Nombre max</label>
            <input v-model.number="limit" type="number" class="form-field" min="1" />
          </div>
        </template>
      </div>

      <div v-if="step === 'config'" class="modal-footer">
        <button class="btn-back" @click="step = 'type'">Retour</button>
        <button class="btn-save" @click="handleSave" :disabled="!title.trim() || saving">
          {{ saving ? '…' : 'Ajouter' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDashboardsStore } from '@/stores/dashboards'
import DataSourcePicker from './DataSourcePicker.vue'

const props = defineProps<{ slug: string }>()
const emit = defineEmits<{ close: []; added: [] }>()

const dashStore = useDashboardsStore()
const saving = ref(false)
const step = ref<'type' | 'config'>('type')
const selectedTypeId = ref('')

const widgetTypes = [
  { id: 'objective', icon: '🎯', name: 'Objectif', desc: 'KPI avec anneau de progression' },
  { id: 'metric', icon: '📊', name: 'Métrique', desc: 'Valeur simple depuis Garmin' },
  { id: 'chart', icon: '📈', name: 'Graphique', desc: 'Graphique configurable' },
  { id: 'exercise_tracker', icon: '💪', name: 'Exercices', desc: 'Suivi d\'exercices personnalisés' },
  { id: 'activity_list', icon: '🏃', name: 'Activités', desc: 'Liste filtrée d\'activités' },
]

const selectedType = computed(() => widgetTypes.find(t => t.id === selectedTypeId.value))

const title = ref('')
const width = ref('full')
const icon = ref('')
const unit = ref('')
const targetValue = ref(0)
const aggregation = ref('sum')
const accent = ref('teal')
const chartType = ref('area')
const objSource = ref('garmin')
const exerciseType = ref('')
const garminQuery = ref<Record<string, any>>({})
const exercisesText = ref('')
const showInputForm = ref(true)
const showWeeklyBreakdown = ref(true)
const filterTypesText = ref('')
const limit = ref(10)

function selectType(typeId: string) {
  selectedTypeId.value = typeId
  title.value = widgetTypes.find(t => t.id === typeId)?.name || ''
  width.value = ['objective', 'metric'].includes(typeId) ? 'quarter' : 'full'
  step.value = 'config'
}

function buildConfig(): Record<string, any> {
  const type = selectedTypeId.value

  if (type === 'objective') {
    const base: Record<string, any> = {
      target_value: targetValue.value,
      unit: unit.value,
      icon: icon.value,
      color: 'var(--teal)',
      aggregation: aggregation.value,
    }
    if (objSource.value === 'garmin') {
      base.garmin_query = garminQuery.value
      base.data_source = 'garmin'
    } else {
      base.exercise_type = exerciseType.value
    }
    return base
  }

  if (type === 'metric') {
    return { garmin_query: { ...garminQuery.value, date_mode: 'latest' }, unit: unit.value, accent: accent.value }
  }

  if (type === 'chart') {
    return { chart_type: chartType.value, garmin_query: garminQuery.value, color: '#00D4AA', label: title.value }
  }

  if (type === 'exercise_tracker') {
    const exercises = exercisesText.value
      .split('\n')
      .filter(l => l.trim())
      .map(line => {
        const [type, label, icon, target] = line.split(',').map(s => s.trim())
        return { type, label: label || type, icon: icon || '', color: 'var(--teal)', target: parseInt(target) || 0, aggregation: 'max' }
      })
    return { exercises, show_input_form: showInputForm.value, show_weekly_breakdown: showWeeklyBreakdown.value }
  }

  if (type === 'activity_list') {
    return {
      filter_types: filterTypesText.value.split(',').map(s => s.trim()).filter(Boolean),
      limit: limit.value,
      show_fields: ['distance_km', 'duration', 'avg_heart_rate'],
      date_mode: 'dashboard_range',
    }
  }

  return {}
}

async function handleSave() {
  saving.value = true
  try {
    await dashStore.addWidget(props.slug, {
      widget_type: selectedTypeId.value,
      title: title.value,
      width: width.value,
      config: buildConfig(),
    })
    emit('added')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200; display: flex; align-items: center; justify-content: center; }
.modal-panel { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-lg); width: 520px; max-height: 85vh; overflow-y: auto; }

.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 16px; font-weight: 600; }
.modal-close { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; line-height: 1; }

.modal-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

.type-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.type-card { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 20px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); cursor: pointer; transition: border-color 0.15s; text-align: center; }
.type-card:hover { border-color: var(--teal); }
.type-icon { font-size: 28px; }
.type-name { font-size: 14px; font-weight: 500; }
.type-desc { font-size: 12px; color: var(--text-muted); }

.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
.form-field { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 12px; color: var(--text); font-family: var(--sans); font-size: 13px; outline: none; }
.form-field:focus { border-color: var(--teal); }
.form-textarea { font-family: var(--mono); font-size: 12px; resize: vertical; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }

.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid var(--border); }
.btn-back { padding: 8px 16px; background: transparent; border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-size: 13px; cursor: pointer; }
.btn-save { padding: 8px 20px; background: var(--teal-dim); border: 1px solid var(--teal); border-radius: var(--radius); color: var(--teal); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-save:hover:not(:disabled) { background: rgba(0, 212, 170, 0.2); }
.btn-save:disabled { opacity: 0.4; cursor: not-allowed; }

@media (max-width: 768px) {
  .modal-panel { width: 100%; max-width: 100%; max-height: 100vh; border-radius: 0; }
  .modal-overlay { align-items: flex-end; }
  .modal-panel { border-radius: var(--radius-lg) var(--radius-lg) 0 0; max-height: 90vh; }
  .modal-body { padding: 16px; }
  .modal-header { padding: 16px; }
  .modal-footer { padding: 12px 16px; }
  .type-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .type-card { padding: 14px 8px; }
  .form-row { flex-direction: column; gap: 12px; }
}
</style>
