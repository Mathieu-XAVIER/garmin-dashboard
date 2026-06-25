<template>
  <RouterLink :to="`/activities/${activity.garmin_id}`" class="activity-row">
    <div class="act-type-badge" :style="{ background: typeColor }">
      {{ typeIcon }}
    </div>
    <div class="act-info">
      <div class="act-name">{{ activity.name || typeLabel }}</div>
      <div class="act-date mono">{{ formatDate(activity.start_time) }}</div>
    </div>
    <div class="act-metrics">
      <div class="act-metric" v-if="activity.distance_meters">
        <span class="mono">{{ (activity.distance_meters / 1000).toFixed(2) }}</span>
        <span class="unit">km</span>
      </div>
      <div class="act-metric" v-if="activity.duration_seconds">
        <span class="mono">{{ formatDuration(activity.duration_seconds) }}</span>
      </div>
      <div class="act-metric" v-if="activity.avg_heart_rate">
        <span class="mono text-orange">{{ activity.avg_heart_rate }}</span>
        <span class="unit">bpm</span>
      </div>
      <span class="chevron">›</span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps<{ activity: any }>()

const TYPE_MAP: Record<string, { icon: string; label: string; color: string }> = {
  running:           { icon: '🏃', label: 'Course',       color: 'rgba(0,212,170,0.15)' },
  cycling:           { icon: '🚴', label: 'Vélo',         color: 'rgba(124,111,205,0.15)' },
  swimming:          { icon: '🏊', label: 'Natation',     color: 'rgba(30,130,230,0.15)' },
  walking:           { icon: '🚶', label: 'Marche',       color: 'rgba(139,146,165,0.15)' },
  strength_training: { icon: '🏋️', label: 'Musculation', color: 'rgba(255,107,53,0.15)' },
}

const typeData  = computed(() => TYPE_MAP[props.activity.activity_type] ?? { icon: '⬡', label: props.activity.activity_type ?? '—', color: 'rgba(139,146,165,0.1)' })
const typeIcon  = computed(() => typeData.value.icon)
const typeLabel = computed(() => typeData.value.label)
const typeColor = computed(() => typeData.value.color)

function formatDuration(s: number): string {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}h${m.toString().padStart(2, '0')}` : `${m}min`
}

function formatDate(dt: string): string {
  if (!dt) return '—'
  const d = new Date(dt)
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.activity-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-radius: var(--radius);
  transition: background 0.15s;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}
.activity-row:hover { background: var(--surface-2); }
.activity-row:hover .chevron { color: var(--teal); }

.act-type-badge { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.act-info { flex: 1; min-width: 0; }
.act-name { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.act-date { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.act-metrics { display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
.act-metric { display: flex; align-items: baseline; gap: 3px; font-family: var(--mono); font-size: 14px; }
.unit { font-size: 12px; color: var(--text-muted); }
.text-orange { color: var(--orange); }
.chevron { font-size: 18px; color: var(--text-dim); transition: color 0.15s; margin-left: 4px; }
</style>
