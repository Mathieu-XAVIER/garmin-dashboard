<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast" tag="div" class="toast-list">
        <div
          v-for="n in notifStore.items"
          :key="n.id"
          class="toast"
          :class="`toast--${n.type}`"
        >
          <span class="toast-icon">{{ iconFor(n.type) }}</span>
          <span class="toast-msg">{{ n.message }}</span>
          <button class="toast-dismiss" @click="notifStore.dismiss(n.id)" aria-label="Fermer">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotificationsStore } from '../stores/notifications'
import type { NotificationType } from '../stores/notifications'

const notifStore = useNotificationsStore()

function iconFor(type: NotificationType): string {
  const icons: Record<NotificationType, string> = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: '◈',
  }
  return icons[type]
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 150;
  width: 360px;
  pointer-events: none;
}

.toast-list {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  font-size: 13px;
  font-family: var(--sans);
  pointer-events: auto;
  border-left: 2px solid transparent;
}

.toast--success { border-left-color: var(--teal); background: color-mix(in srgb, var(--surface) 88%, var(--teal)); }
.toast--error   { border-left-color: var(--orange); background: color-mix(in srgb, var(--surface) 88%, var(--orange)); }
.toast--warning { border-left-color: #F59E0B; background: color-mix(in srgb, var(--surface) 92%, #F59E0B); }
.toast--info    { border-left-color: var(--purple); background: color-mix(in srgb, var(--surface) 88%, var(--purple)); }

.toast-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}

.toast--success .toast-icon { color: var(--teal); }
.toast--error   .toast-icon { color: var(--orange); }
.toast--warning .toast-icon { color: #F59E0B; }
.toast--info    .toast-icon { color: var(--purple); }

.toast-msg {
  flex: 1;
  color: var(--text);
  line-height: 1.4;
}

.toast-dismiss {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
  padding: 0 2px;
  flex-shrink: 0;
  transition: color 0.15s;
}

.toast-dismiss:hover {
  color: var(--text);
}

/* Animations TransitionGroup */
.toast-enter-active {
  transition: all 0.22s ease;
}

.toast-leave-active {
  transition: all 0.18s ease;
  position: absolute;
  width: 100%;
}

.toast-move {
  transition: transform 0.18s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}

@media (max-width: 768px) {
  .toast-container {
    top: 60px;
    left: 12px;
    right: 12px;
    width: auto;
  }
}
</style>
