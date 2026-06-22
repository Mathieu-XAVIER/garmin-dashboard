<template>
  <div class="empty-state">
    <div class="empty-icon">◌</div>
    <p class="empty-msg">{{ message }}</p>
    <p class="empty-hint" v-if="hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string
  hint?: string
}>()
</script>

<style scoped>
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 24px; gap: 8px; }
.empty-icon { font-size: 28px; color: var(--text-dim); line-height: 1; margin-bottom: 4px; }
.empty-msg { font-size: 13px; color: var(--text-muted); text-align: center; }
.empty-hint { font-size: 11px; color: var(--text-dim); font-family: var(--mono); text-align: center; }
</style>
