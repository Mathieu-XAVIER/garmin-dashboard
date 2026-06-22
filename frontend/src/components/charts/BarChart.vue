<template>
  <apexchart
    type="bar"
    :height="height"
    :options="chartOptions"
    :series="series"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  categories: string[]
  series: { name: string; data: number[]; color?: string }[]
  height?: number
  unit?: string
  stacked?: boolean
}>()

const chartOptions = computed(() => ({
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    stacked: props.stacked ?? false,
    animations: { enabled: true, speed: 500 },
  },
  theme: { mode: 'dark' },
  colors: props.series.map(s => s.color).filter(Boolean).length
    ? props.series.map(s => s.color ?? '#00D4AA')
    : ['#00D4AA', '#FF6B35', '#7C6FCD'],
  plotOptions: {
    bar: { borderRadius: 3, columnWidth: '60%' },
  },
  dataLabels: { enabled: false },
  grid: {
    borderColor: '#252C3D',
    strokeDashArray: 3,
    xaxis: { lines: { show: false } },
  },
  xaxis: {
    categories: props.categories,
    labels: {
      style: { colors: '#8B92A5', fontFamily: 'DM Mono, monospace', fontSize: '10px' },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    labels: {
      style: { colors: '#8B92A5', fontFamily: 'DM Mono, monospace', fontSize: '10px' },
      formatter: (v: number): string => props.unit ? String(Math.round(v)) + props.unit : String(Math.round(v)),
    },
  },
  tooltip: {
    theme: 'dark',
    style: { fontFamily: 'DM Mono, monospace', fontSize: '12px' },
  },
  legend: {
    labels: { colors: '#8B92A5' },
    fontFamily: 'DM Mono, monospace',
    fontSize: '11px',
  },
}))
</script>
