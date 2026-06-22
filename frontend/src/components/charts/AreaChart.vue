<template>
  <apexchart
    type="area"
    :height="height"
    :options="chartOptions"
    :series="series"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: { x: string | number; y: number | null }[]
  label?: string
  color?: string
  height?: number
  unit?: string
  yMin?: number
  yMax?: number
}>()

const series = computed(() => [{
  name: props.label ?? '',
  data: props.data,
}])

const chartOptions = computed(() => ({
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    sparkline: { enabled: false },
    animations: { enabled: true, speed: 600 },
  },
  theme: { mode: 'dark' },
  colors: [props.color ?? '#00D4AA'],
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.3,
      opacityTo: 0.01,
      stops: [0, 100],
    },
  },
  stroke: { curve: 'smooth', width: 2 },
  dataLabels: { enabled: false },
  grid: {
    borderColor: '#252C3D',
    strokeDashArray: 3,
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
    padding: { left: 0, right: 0 },
  },
  xaxis: {
    type: 'category',
    labels: {
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
      formatter: (v: number) => props.unit ? `${Math.round(v)}${props.unit}` : Math.round(v).toString(),
    },
  },
  tooltip: {
    theme: 'dark',
    style: { fontFamily: 'DM Mono, monospace', fontSize: '12px' },
    y: {
      formatter: (v: number) => props.unit ? `${v} ${props.unit}` : String(v),
    },
  },
  markers: { size: 0, hover: { size: 4 } },
}))
</script>
