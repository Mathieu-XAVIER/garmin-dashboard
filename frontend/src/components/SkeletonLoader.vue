<template>
  <div class="skeleton-wrap">
    <!-- KPI grid -->
    <div v-if="type === 'kpi'" class="skeleton-kpi-grid">
      <div v-for="i in count" :key="i" class="skeleton-card">
        <div class="skel skel-label"></div>
        <div class="skel skel-value"></div>
        <div class="skel skel-sub"></div>
      </div>
    </div>

    <!-- Chart -->
    <div v-else-if="type === 'chart'" class="skeleton-chart-card">
      <div class="skel skel-chart"></div>
    </div>

    <!-- Table rows -->
    <div v-else-if="type === 'table'" class="skeleton-table">
      <div v-for="i in count" :key="i" class="skeleton-row">
        <div class="skel skel-dot"></div>
        <div class="skel skel-line long"></div>
        <div class="skel skel-line medium"></div>
        <div class="skel skel-line short"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  type: 'kpi' | 'chart' | 'table'
  count?: number
}>()
</script>

<style scoped>
@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position:  400px 0; }
}

.skel {
  border-radius: 4px;
  background: linear-gradient(90deg,
    var(--surface-2) 25%,
    var(--border)    50%,
    var(--surface-2) 75%
  );
  background-size: 800px 100%;
  animation: shimmer 1.4s infinite linear;
}

/* KPI */
.skeleton-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.skeleton-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.skel-label { height: 10px; width: 60%; }
.skel-value { height: 28px; width: 50%; }
.skel-sub   { height: 8px;  width: 40%; }

/* Chart */
.skeleton-chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px;
}
.skel-chart { height: 160px; width: 100%; border-radius: var(--radius); }

/* Table */
.skeleton-table {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.skeleton-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.skeleton-row:last-child { border-bottom: none; }
.skel-dot    { width: 36px; height: 36px; border-radius: 8px; flex-shrink: 0; }
.skel-line   { height: 10px; }
.skel-line.long   { width: 35%; }
.skel-line.medium { width: 20%; }
.skel-line.short  { width: 12%; }
</style>
