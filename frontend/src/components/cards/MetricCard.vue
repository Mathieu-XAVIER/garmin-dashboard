<template>
  <div class="metric-card" :class="accent">
    <div class="card-label">{{ label }}</div>
    <div class="card-value mono">
      <span class="value-number" ref="numEl">{{ displayValue }}</span>
      <span class="value-unit" v-if="unit">{{ unit }}</span>
    </div>
    <div class="card-sub" v-if="sub">{{ sub }}</div>
    <div class="card-trend" v-if="trend !== undefined">
      <span :class="trend >= 0 ? 'up' : 'down'">
        {{ trend >= 0 ? '▲' : '▼' }} {{ Math.abs(trend) }}%
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value: number | string | null | undefined
  unit?: string
  sub?: string
  trend?: number
  accent?: 'teal' | 'orange' | 'purple' | 'none'
  decimals?: number
}>()

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '—'
  if (typeof props.value === 'string') return props.value
  return props.decimals !== undefined
    ? props.value.toFixed(props.decimals)
    : Math.round(props.value).toString()
})
</script>

<style scoped>
.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color 0.2s;
}
.metric-card:hover { border-color: var(--text-dim); }

.metric-card.teal { border-left: 3px solid var(--teal); }
.metric-card.orange { border-left: 3px solid var(--orange); }
.metric-card.purple { border-left: 3px solid var(--purple); }

.card-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  font-weight: 500;
}

.card-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 4px;
}

.value-number {
  font-family: var(--mono);
  font-size: 28px;
  font-weight: 500;
  color: var(--text);
  line-height: 1;
}

.value-unit {
  font-size: 14px;
  color: var(--text-muted);
  font-family: var(--mono);
}

.card-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.card-trend { margin-top: 6px; font-size: 12px; font-family: var(--mono); }
.up { color: var(--teal); }
.down { color: var(--orange); }

@media (max-width: 768px) {
  .metric-card { padding: 12px 14px; }
  .value-number { font-size: 22px; }
  .card-label { font-size: 11px; }
}
</style>
