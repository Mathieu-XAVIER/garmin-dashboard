<template>
  <div id="app-shell">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-icon">⬡</span>
        <span class="logo-text">Garmin<br><strong>Dashboard</strong></span>
      </div>

      <nav class="sidebar-nav">
        <RouterLink to="/"           class="nav-item" active-class="active"><span class="nav-icon">▣</span><span>Dashboard</span></RouterLink>
        <RouterLink to="/activities" class="nav-item" active-class="active"><span class="nav-icon">◎</span><span>Activités</span></RouterLink>
        <RouterLink to="/health"     class="nav-item" active-class="active"><span class="nav-icon">♡</span><span>Santé</span></RouterLink>
        <RouterLink to="/sleep"      class="nav-item" active-class="active"><span class="nav-icon">◐</span><span>Sommeil</span></RouterLink>
        <RouterLink to="/profile"    class="nav-item" active-class="active"><span class="nav-icon">◈</span><span>Profil</span></RouterLink>
      </nav>

      <div class="sidebar-footer">
        <button class="sync-btn" @click="handleSync" :disabled="syncing">
          <span :class="{ spinning: syncing }">↻</span>
          {{ syncing ? 'Synchro…' : 'Synchroniser' }}
        </button>
        <p v-if="store.lastSync" class="last-sync">Synchro {{ timeAgo(store.lastSync) }}</p>
      </div>
    </aside>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useGarminStore } from './stores/garmin'

const store = useGarminStore()
const syncing = ref(false)

async function handleSync() {
  syncing.value = true
  try { await store.triggerSync(7) } finally { syncing.value = false }
}

function timeAgo(date: Date): string {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diff < 60) return `il y a ${diff}s`
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)}min`
  return `il y a ${Math.floor(diff / 3600)}h`
}
</script>

<style scoped>
#app-shell { display: flex; min-height: 100vh; }

.sidebar { width: 220px; min-height: 100vh; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 24px 0; position: sticky; top: 0; flex-shrink: 0; }
.sidebar-logo { display: flex; align-items: center; gap: 10px; padding: 0 20px 28px; border-bottom: 1px solid var(--border); }
.logo-icon { font-size: 22px; color: var(--teal); line-height: 1; }
.logo-text { font-family: var(--sans); font-size: 11px; color: var(--text-muted); line-height: 1.4; text-transform: uppercase; letter-spacing: 0.05em; }
.logo-text strong { color: var(--text); font-weight: 600; font-size: 13px; text-transform: none; letter-spacing: 0; }

.sidebar-nav { display: flex; flex-direction: column; gap: 2px; padding: 20px 12px; flex: 1; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: var(--radius); color: var(--text-muted); text-decoration: none; font-size: 13px; font-weight: 500; transition: background 0.15s, color 0.15s; }
.nav-item:hover { background: var(--surface-2); color: var(--text); }
.nav-item.active { background: var(--teal-dim); color: var(--teal); }
.nav-icon { font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }

.sidebar-footer { padding: 16px 12px 0; border-top: 1px solid var(--border); }
.sync-btn { width: 100%; padding: 8px 12px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-family: var(--sans); font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: border-color 0.15s, color 0.15s; }
.sync-btn:hover:not(:disabled) { border-color: var(--teal); color: var(--teal); }
.sync-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spinning { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.last-sync { text-align: center; font-size: 10px; color: var(--text-dim); margin-top: 8px; font-family: var(--mono); }

.main-content { flex: 1; overflow: auto; min-width: 0; }
</style>
