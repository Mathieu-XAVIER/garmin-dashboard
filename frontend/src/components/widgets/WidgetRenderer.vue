<template>
  <component :is="widgetComponent" v-if="widgetComponent"
    :widget="widget" :data="widget.data" :dashboard="dashboard" />
  <div v-else class="widget-unknown">Widget inconnu : {{ widget.widget_type }}</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ObjectiveWidget from './ObjectiveWidget.vue'
import MetricWidget from './MetricWidget.vue'
import ChartWidget from './ChartWidget.vue'
import ExerciseTrackerWidget from './ExerciseTrackerWidget.vue'
import ActivityListWidget from './ActivityListWidget.vue'

import type { Widget, Dashboard } from '@/stores/dashboards'

const WIDGET_MAP: Record<string, any> = {
  objective: ObjectiveWidget,
  metric: MetricWidget,
  chart: ChartWidget,
  exercise_tracker: ExerciseTrackerWidget,
  activity_list: ActivityListWidget,
}

const props = defineProps<{ widget: Widget; dashboard: Dashboard }>()

const widgetComponent = computed(() => WIDGET_MAP[props.widget.widget_type] ?? null)
</script>

<style scoped>
.widget-unknown { padding: 20px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); color: var(--text-muted); text-align: center; font-size: 13px; }
</style>
