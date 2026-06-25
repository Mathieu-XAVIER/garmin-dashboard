<template>
  <div class="chart-widget">
    <div class="cw-header">
      <span class="cw-title">{{ widget.title }}</span>
    </div>
    <component :is="chartComponent" v-if="chartComponent && data?.labels?.length"
      :categories="data.labels"
      :series="chartSeries"
      :color="config.color || '#00D4AA'"
      :height="220"
    />
    <div v-else class="cw-empty mono">Aucune donnée</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AreaChart from '@/components/charts/AreaChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import type { Widget } from '@/stores/dashboards'

const CHART_MAP: Record<string, any> = {
  area: AreaChart,
  bar: BarChart,
  line: LineChart,
  donut: DonutChart,
}

const props = defineProps<{ widget: Widget; data: { labels: string[]; values: number[] } }>()

const config = computed(() => props.widget.config || {})
const chartComponent = computed(() => CHART_MAP[config.value.chart_type || 'area'] ?? AreaChart)
const chartSeries = computed(() => {
  const label = config.value.label || props.widget.title
  return [{ name: label, data: props.data?.values ?? [] }]
})
</script>

<style scoped>
.chart-widget { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; }
.cw-header { margin-bottom: 12px; }
.cw-title { font-size: 13px; font-weight: 500; }
.cw-empty { text-align: center; padding: 40px 0; color: var(--text-dim); font-size: 13px; }
</style>
