<template>
  <apexchart
    type="line"
    :height="height"
    :options="chartOptions"
    :series="series"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  series: { name: string; data: (number | null)[]; color?: string }[]
  categories: string[]
  height?: number
  unit?: string
  yMin?: number
  yMax?: number
  smooth?: boolean
}>()

const chartOptions = computed(() => ({
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    animations: { enabled: true, speed: 500 },
  },
  theme: { mode: 'dark' },
  colors: props.series.map(s => s.color).filter(Boolean).length
    ? props.series.map(s => s.color ?? '#00D4AA')
    : ['#00D4AA', '#FF6B35', '#7C6FCD'],
  stroke: {
    curve: props.smooth !== false ? 'smooth' : 'straight',
    width: props.series.map(() => 2),
    dashArray: props.series.map((_, i) => i === 1 ? 4 : 0),
  },
  dataLabels: { enabled: false },
  markers: { size: 0, hover: { size: 4 } },
  grid: {
    borderColor: '#252C3D',
    strokeDashArray: 3,
    xaxis: { lines: { show: false } },
  },
  xaxis: {
    categories: props.categories,
    labels: {
      rotate: -30,
      style: { colors: '#8B92A5', fontFamily: 'DM Mono, monospace', fontSize: '10px' },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    min: props.yMin,
    max: props.yMax,
    labels: {
      style: { colors: '#8B92A5', fontFamily: 'DM Mono, monospace', fontSize: '10px' },
      formatter: (v: number): string => props.unit ? String(Math.round(v)) + props.unit : String(Math.round(v)),
    },
  },
  legend: {
    labels: { colors: '#8B92A5' },
    fontFamily: 'DM Mono, monospace',
    fontSize: '11px',
  },
  tooltip: {
    theme: 'dark',
    style: { fontFamily: 'DM Mono, monospace', fontSize: '12px' },
  },
}))
</script>
