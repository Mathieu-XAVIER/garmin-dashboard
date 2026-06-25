<template>
  <div class="obj-card">
    <div class="obj-icon">{{ config.icon }}</div>
    <div class="obj-label">{{ widget.title }}</div>
    <div class="obj-progress-ring-wrap">
      <svg viewBox="0 0 100 100" class="obj-ring">
        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--surface-2)" stroke-width="8"/>
        <circle cx="50" cy="50" r="42" fill="none" :stroke="config.color || 'var(--teal)'" stroke-width="8"
          stroke-linecap="round"
          :stroke-dasharray="`${arc} 264`"
          stroke-dashoffset="66"
          style="transition: stroke-dasharray 0.8s ease"/>
      </svg>
      <div class="obj-ring-center">
        <span class="obj-val mono">{{ currentValue }}</span>
        <span class="obj-unit">/ {{ config.target_value }} {{ config.unit }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Widget } from '@/stores/dashboards'

const props = defineProps<{ widget: Widget; data: { current_value: number; target: number } }>()

const config = computed(() => props.widget.config || {})
const currentValue = computed(() => {
  const v = props.data?.current_value ?? 0
  return typeof v === 'number' && v % 1 !== 0 ? v.toFixed(1) : v
})
const arc = computed(() => {
  const target = config.value.target_value || 1
  return Math.round(Math.min(1, (props.data?.current_value ?? 0) / target) * 264)
})
</script>

<style scoped>
.obj-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.obj-icon { font-size: 24px; }
.obj-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
.obj-progress-ring-wrap { position: relative; width: 100px; height: 100px; }
.obj-ring { width: 100px; height: 100px; transform: rotate(-90deg); }
.obj-ring-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.obj-val { display: block; font-size: 20px; font-weight: 500; color: var(--text); line-height: 1; }
.obj-unit { display: block; font-size: 11px; color: var(--text-muted); margin-top: 2px; }
</style>
