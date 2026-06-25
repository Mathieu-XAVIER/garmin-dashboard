<template>
  <div class="metric-widget" :class="`accent-${config.accent || 'teal'}`">
    <div class="mw-icon" v-if="config.icon">{{ config.icon }}</div>
    <div class="mw-label">{{ widget.title }}</div>
    <div class="mw-value mono">{{ displayValue }}</div>
    <div class="mw-unit" v-if="config.unit">{{ config.unit }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Widget } from '@/stores/dashboards'

const props = defineProps<{ widget: Widget; data: { value: number } }>()

const config = computed(() => props.widget.config || {})
const displayValue = computed(() => {
  const v = props.data?.value ?? 0
  const decimals = config.value.decimals ?? 0
  return typeof v === 'number' ? v.toFixed(decimals) : v
})
</script>

<style scoped>
.metric-widget { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.mw-icon { font-size: 24px; }
.mw-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
.mw-value { font-size: 28px; font-weight: 600; line-height: 1; }
.mw-unit { font-size: 12px; color: var(--text-muted); }

.accent-teal .mw-value { color: var(--teal); }
.accent-orange .mw-value { color: var(--orange); }
.accent-purple .mw-value { color: var(--purple); }
.accent-none .mw-value { color: var(--text); }
</style>
