<template>
  <Transition name="banner">
    <div v-if="visible" class="garmin-banner" role="alert">
      <span class="banner-icon">⚡</span>
      <span class="banner-msg">
        Synchronisation désactivée —
        <RouterLink to="/profile" class="banner-link">configurez vos identifiants Garmin Connect</RouterLink>
        pour activer la synchro automatique.
      </span>
      <button class="banner-dismiss" @click="handleDismiss" aria-label="Fermer">×</button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const dismissed = ref(sessionStorage.getItem('garmin_banner_dismissed') === '1')

function handleDismiss() {
  sessionStorage.setItem('garmin_banner_dismissed', '1')
  dismissed.value = true
}

const visible = computed(() =>
  !dismissed.value &&
  authStore.user !== null &&
  !authStore.user.has_garmin_credentials
)
</script>

<style scoped>
.garmin-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--orange-dim);
  border-bottom: 1px solid rgba(255, 107, 53, 0.25);
  font-size: 13px;
  color: var(--text-muted);
  font-family: var(--sans);
}

.banner-icon {
  color: var(--orange);
  font-size: 13px;
  flex-shrink: 0;
}

.banner-msg {
  flex: 1;
  line-height: 1.4;
}

.banner-link {
  color: var(--orange);
  text-decoration: underline;
  font-weight: 500;
  transition: opacity 0.15s;
}

.banner-link:hover {
  opacity: 0.85;
}

.banner-dismiss {
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

.banner-dismiss:hover {
  color: var(--orange);
}

.banner-enter-active {
  transition: all 0.2s ease;
}

.banner-leave-active {
  transition: all 0.15s ease;
}

.banner-enter-from,
.banner-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
