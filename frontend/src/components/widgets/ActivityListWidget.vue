<template>
  <div class="al-widget">
    <div class="al-header">
      <span class="al-title">{{ widget.title }}</span>
    </div>
    <div v-if="data?.activities?.length" class="al-list">
      <div v-for="a in data.activities" :key="a.garmin_id" class="al-row">
        <span class="al-date mono">{{ a.date?.slice(5) }}</span>
        <span class="al-name">{{ a.name || a.activity_type }}</span>
        <span class="al-dist mono" v-if="a.distance_km">{{ a.distance_km }} km</span>
        <span class="al-dur mono" v-if="a.duration_seconds">{{ formatDuration(a.duration_seconds) }}</span>
        <span class="al-hr mono" v-if="a.avg_heart_rate">♡ {{ a.avg_heart_rate }}</span>
      </div>
    </div>
    <div v-else class="al-empty mono">Aucune activité</div>
  </div>
</template>

<script setup lang="ts">
import type { Widget } from '@/stores/dashboards'

defineProps<{
  widget: Widget
  data: {
    activities: {
      garmin_id: string
      name: string
      activity_type: string
      date: string | null
      distance_km: number
      duration_seconds: number
      avg_heart_rate: number | null
      calories: number | null
    }[]
  }
}>()

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h}h${String(m).padStart(2, '0')}` : `${m}min`
}
</script>

<style scoped>
.al-widget { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; }
.al-header { margin-bottom: 12px; }
.al-title { font-size: 13px; font-weight: 500; }
.al-list { display: flex; flex-direction: column; }
.al-row { display: flex; gap: 10px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.al-row:last-child { border-bottom: none; }
.al-date { color: var(--text-dim); min-width: 42px; font-size: 12px; }
.al-name { flex: 1; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.al-dist { color: var(--teal); font-size: 12px; }
.al-dur { color: var(--text-muted); font-size: 12px; }
.al-hr { color: var(--orange); font-size: 12px; }
.al-empty { text-align: center; padding: 32px 0; color: var(--text-dim); font-size: 13px; }
</style>
