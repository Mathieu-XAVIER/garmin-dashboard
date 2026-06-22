<template>
  <div class="donut-wrap">
    <apexchart
      type="donut"
      :height="height"
      :options="chartOptions"
      :series="series"
    />
    <div class="donut-center" v-if="centerLabel">
      <span class="center-value mono">{{ centerValue }}</span>
      <span class="center-label">{{ centerLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  labels: string[]
  series: number[]
  colors?: string[]
  height?: number
  centerLabel?: string
  centerValue?: string | number
}>()

const chartOptions = computed(() => ({
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    animations: { enabled: true, speed: 600 },
  },
  theme: { mode: 'dark' },
  colors: props.colors ?? ['#00D4AA', '#7C6FCD', '#3B5B8F', '#FF6B35'],
  labels: props.labels,
  legend: {
    position: 'bottom' as const,
    labels: { colors: '#8B92A5' },
    fontFamily: 'DM Mono, monospace',
    fontSize: '11px',
    markers: { size: 6 },
  },
  dataLabels: { enabled: false },
  plotOptions: {
    pie: {
      donut: {
        size: '72%',
        labels: { show: false },
      },
    },
  },
  stroke: { width: 0 },
  tooltip: {
    theme: 'dark',
    style: { fontFamily: 'DM Mono, monospace', fontSize: '12px' },
    y: {
      formatter: (v: number) => {
        const total = props.series.reduce((a, b) => a + b, 0)
        const pct = total ? Math.round((v / total) * 100) : 0
        const h = Math.floor(v / 3600)
        const m = Math.floor((v % 3600) / 60)
        const time = h > 0 ? `${h}h${m.toString().padStart(2,'0')}` : `${m}min`
        return `${time} (${pct}%)`
      },
    },
  },
}))
</script>

<style scoped>
.donut-wrap { position: relative; }
.donut-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -62%);
  text-align: center;
  pointer-events: none;
}
.center-value {
  display: block;
  font-size: 20px;
  font-weight: 500;
  color: var(--text);
  line-height: 1;
}
.center-label {
  display: block;
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 4px;
}
</style>
