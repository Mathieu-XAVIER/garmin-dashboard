<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-panel">
      <div class="modal-header">
        <h2 class="modal-title">{{ isEdit ? 'Modifier le dashboard' : 'Nouveau dashboard' }}</h2>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Nom</label>
          <input v-model="name" class="form-field" placeholder="Ex: Prépa Marathon" />
        </div>

        <div class="form-group">
          <label class="form-label">Icône (emoji)</label>
          <input v-model="icon" class="form-field form-field-icon" placeholder="🏃" maxlength="4" />
        </div>

        <div class="form-group">
          <label class="form-label">Description</label>
          <input v-model="description" class="form-field" placeholder="Optionnel" />
        </div>

        <div class="form-group">
          <label class="form-label">Période</label>
          <select v-model="dateType" class="form-field">
            <option value="rolling">Glissante</option>
            <option value="fixed">Fixe</option>
          </select>
        </div>

        <template v-if="dateType === 'rolling'">
          <div class="form-group">
            <label class="form-label">Nombre de jours</label>
            <input v-model.number="rollingDays" type="number" class="form-field" min="1" />
          </div>
        </template>

        <template v-if="dateType === 'fixed'">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Début</label>
              <input v-model="fixedStart" type="date" class="form-field" />
            </div>
            <div class="form-group">
              <label class="form-label">Fin</label>
              <input v-model="fixedEnd" type="date" class="form-field" />
            </div>
          </div>
        </template>

        <div class="form-group">
          <label class="form-label">Couleur d'accent</label>
          <input v-model="color" type="color" class="form-field form-field-color" />
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Annuler</button>
        <button class="btn-save" @click="handleSave" :disabled="!name.trim() || saving">
          {{ saving ? '…' : (isEdit ? 'Enregistrer' : 'Créer') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDashboardsStore, type Dashboard } from '@/stores/dashboards'

const props = defineProps<{ dashboard?: Dashboard | null }>()
const emit = defineEmits<{ close: []; saved: [slug: string] }>()

const dashStore = useDashboardsStore()

const isEdit = computed(() => !!props.dashboard)

const name = ref(props.dashboard?.name || '')
const icon = ref(props.dashboard?.icon || '')
const description = ref(props.dashboard?.config?.description || '')
const dateType = ref(props.dashboard?.config?.date_range?.type || 'rolling')
const rollingDays = ref(props.dashboard?.config?.date_range?.rolling_days || 30)
const fixedStart = ref(props.dashboard?.config?.date_range?.start || '')
const fixedEnd = ref(props.dashboard?.config?.date_range?.end || '')
const color = ref(props.dashboard?.config?.color || '#00D4AA')
const saving = ref(false)

async function handleSave() {
  saving.value = true
  try {
    const config: Record<string, any> = {
      description: description.value || undefined,
      color: color.value,
      date_range: dateType.value === 'fixed'
        ? { type: 'fixed', start: fixedStart.value, end: fixedEnd.value }
        : { type: 'rolling', rolling_days: rollingDays.value },
    }

    if (isEdit.value && props.dashboard) {
      const result = await dashStore.updateDashboard(props.dashboard.slug, {
        name: name.value,
        icon: icon.value || undefined,
        config,
      })
      emit('saved', result.slug)
    } else {
      const result = await dashStore.createDashboard({
        name: name.value,
        icon: icon.value || undefined,
        config,
      })
      emit('saved', result.slug)
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200; display: flex; align-items: center; justify-content: center; }
.modal-panel { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-lg); width: 440px; max-height: 80vh; overflow-y: auto; }

.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--border); }
.modal-title { font-size: 16px; font-weight: 600; }
.modal-close { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; line-height: 1; }

.modal-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
.form-field { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 12px; color: var(--text); font-family: var(--sans); font-size: 13px; outline: none; }
.form-field:focus { border-color: var(--teal); }
.form-field-icon { width: 60px; text-align: center; font-size: 20px; }
.form-field-color { width: 60px; height: 36px; padding: 2px; cursor: pointer; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }

.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid var(--border); }
.btn-cancel { padding: 8px 16px; background: transparent; border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-size: 13px; cursor: pointer; }
.btn-cancel:hover { border-color: var(--text-muted); }
.btn-save { padding: 8px 20px; background: var(--teal-dim); border: 1px solid var(--teal); border-radius: var(--radius); color: var(--teal); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-save:hover:not(:disabled) { background: rgba(0, 212, 170, 0.2); }
.btn-save:disabled { opacity: 0.4; cursor: not-allowed; }

@media (max-width: 768px) {
  .modal-overlay { align-items: flex-end; }
  .modal-panel { width: 100%; border-radius: var(--radius-lg) var(--radius-lg) 0 0; max-height: 90vh; }
  .modal-body { padding: 16px; }
  .modal-header { padding: 16px; }
  .modal-footer { padding: 12px 16px; }
  .form-row { flex-direction: column; gap: 12px; }
}
</style>
