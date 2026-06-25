<template>
  <div id="app-shell">
    <!-- Sidebar desktop -->
    <aside v-if="showSidebar" class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-icon">⬡</span>
        <span class="logo-text">Garmin<br><strong>Dashboard</strong></span>
      </div>

      <nav class="sidebar-nav">
        <RouterLink v-for="tab in navStore.nativeTabs" :key="tab.id"
          :to="tab.to" class="nav-item" active-class="active">
          <span class="nav-icon">{{ tab.icon }}</span><span>{{ tab.label }}</span>
        </RouterLink>

        <div v-if="navStore.customDashboards.length" class="nav-separator"></div>

        <RouterLink v-for="dash in navStore.customDashboards" :key="dash.slug"
          :to="`/d/${dash.slug}`" class="nav-item" active-class="active">
          <span class="nav-icon">{{ dash.icon || '◇' }}</span><span>{{ dash.name }}</span>
        </RouterLink>

        <button class="nav-item nav-add" @click="navStore.settingsOpen = true">
          <span class="nav-icon">+</span><span>Personnaliser</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <button class="sync-btn" @click="handleSync" :disabled="syncing">
          <span :class="{ spinning: syncing }">↻</span>
          {{ syncing ? 'Synchro…' : 'Synchroniser' }}
        </button>
        <p v-if="store.lastSync" class="last-sync">Synchro {{ timeAgo(store.lastSync) }}</p>
        <button class="logout-btn" @click="handleLogout">Déconnexion</button>
      </div>
    </aside>

    <!-- Mobile header -->
    <header v-if="showSidebar" class="mobile-header">
      <div class="mobile-header-left">
        <span class="logo-icon">⬡</span>
        <span class="mobile-title">Garmin Dashboard</span>
      </div>
      <div class="mobile-header-actions">
        <button class="mobile-sync-btn" @click="handleSync" :disabled="syncing">
          <span :class="{ spinning: syncing }">↻</span>
        </button>
        <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen">
          {{ mobileMenuOpen ? '×' : '☰' }}
        </button>
      </div>
    </header>

    <!-- Mobile slide menu -->
    <Teleport to="body">
      <div v-if="mobileMenuOpen && showSidebar" class="mobile-menu-overlay" @click="mobileMenuOpen = false">
        <div class="mobile-menu-panel" @click.stop>
          <div class="mobile-menu-header">
            <span class="logo-icon">⬡</span>
            <span class="mobile-title">Garmin Dashboard</span>
            <button class="mobile-menu-close" @click="mobileMenuOpen = false">×</button>
          </div>
          <nav class="mobile-menu-nav">
            <RouterLink v-for="tab in navStore.nativeTabs" :key="tab.id"
              :to="tab.to" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
              <span class="nav-icon">{{ tab.icon }}</span><span>{{ tab.label }}</span>
            </RouterLink>
            <div v-if="navStore.customDashboards.length" class="nav-separator"></div>
            <RouterLink v-for="dash in navStore.customDashboards" :key="dash.slug"
              :to="`/d/${dash.slug}`" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
              <span class="nav-icon">{{ dash.icon || '◇' }}</span><span>{{ dash.name }}</span>
            </RouterLink>
            <button class="nav-item nav-add" @click="navStore.settingsOpen = true; mobileMenuOpen = false">
              <span class="nav-icon">+</span><span>Personnaliser</span>
            </button>
          </nav>
          <div class="mobile-menu-footer">
            <button class="sync-btn" @click="handleSync" :disabled="syncing">
              <span :class="{ spinning: syncing }">↻</span>
              {{ syncing ? 'Synchro…' : 'Synchroniser' }}
            </button>
            <button class="logout-btn" @click="handleLogout">Déconnexion</button>
          </div>
        </div>
      </div>
    </Teleport>

    <NavSettings v-if="navStore.settingsOpen" @close="navStore.settingsOpen = false" />

    <main class="main-content" :class="{ 'full-width': !showSidebar }">
      <RouterView />
    </main>

    <!-- Bottom nav mobile -->
    <nav v-if="showSidebar" class="bottom-nav">
      <RouterLink v-for="tab in bottomTabs" :key="tab.id"
        :to="tab.to" class="bottom-nav-item" active-class="active">
        <span class="bottom-nav-icon">{{ tab.icon }}</span>
        <span class="bottom-nav-label">{{ tab.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useGarminStore } from './stores/garmin'
import { useAuthStore } from './stores/auth'
import { useNavStore } from './stores/nav'
import NavSettings from './components/sidebar/NavSettings.vue'

const store = useGarminStore()
const authStore = useAuthStore()
const navStore = useNavStore()
const route = useRoute()
const syncing = ref(false)
const mobileMenuOpen = ref(false)

const showSidebar = computed(() => route.name !== 'login')

const bottomTabs = computed(() => navStore.nativeTabs.slice(0, 5))

async function handleSync() {
  syncing.value = true
  try {
    await store.triggerSync(7)
    await store.loadDashboard()
  } finally {
    syncing.value = false
  }
}

function handleLogout() {
  authStore.logout()
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

/* ── Sidebar desktop ───────────────────────────── */
.sidebar { width: 220px; height: 100vh; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 24px 0; position: sticky; top: 0; flex-shrink: 0; overflow-y: auto; }
.sidebar-logo { display: flex; align-items: center; gap: 10px; padding: 0 20px 28px; border-bottom: 1px solid var(--border); }
.logo-icon { font-size: 22px; color: var(--teal); line-height: 1; }
.logo-text { font-family: var(--sans); font-size: 12px; color: var(--text-muted); line-height: 1.4; text-transform: uppercase; letter-spacing: 0.05em; }
.logo-text strong { color: var(--text); font-weight: 600; font-size: 14px; text-transform: none; letter-spacing: 0; }

.sidebar-nav { display: flex; flex-direction: column; gap: 2px; padding: 20px 12px; flex: 1; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--radius); color: var(--text-muted); text-decoration: none; font-size: 14px; font-weight: 500; transition: background 0.15s, color 0.15s; }
.nav-item:hover { background: var(--surface-2); color: var(--text); }
.nav-item.active { background: var(--teal-dim); color: var(--teal); }
.nav-icon { font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }

.nav-separator { height: 1px; background: var(--border); margin: 8px 0; }
.nav-add { color: var(--text-dim); font-size: 13px; border: none; background: none; cursor: pointer; width: 100%; text-align: left; }
.nav-add:hover { background: var(--surface-2); color: var(--teal); }

.sidebar-footer { padding: 16px 12px 0; border-top: 1px solid var(--border); }
.sync-btn { width: 100%; padding: 9px 12px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-family: var(--sans); font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: border-color 0.15s, color 0.15s; }
.sync-btn:hover:not(:disabled) { border-color: var(--teal); color: var(--teal); }
.sync-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spinning { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.last-sync { text-align: center; font-size: 12px; color: var(--text-muted); margin-top: 8px; font-family: var(--mono); }

.logout-btn { width: 100%; padding: 8px 12px; background: transparent; border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-family: var(--sans); font-size: 12px; cursor: pointer; margin-top: 8px; transition: border-color 0.15s, color 0.15s; }
.logout-btn:hover { border-color: var(--orange); color: var(--orange); }

.main-content { flex: 1; overflow: auto; min-width: 0; }
.main-content.full-width { width: 100%; }

/* ── Mobile header ─────────────────────────────── */
.mobile-header { display: none; }
.bottom-nav { display: none; }

@media (max-width: 768px) {
  .sidebar { display: none; }

  .mobile-header {
    display: flex;
    position: sticky;
    top: 0;
    z-index: 50;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    width: 100%;
  }

  .mobile-header-left { display: flex; align-items: center; gap: 8px; }
  .mobile-title { font-size: 14px; font-weight: 600; color: var(--text); }

  .mobile-header-actions { display: flex; align-items: center; gap: 4px; }
  .mobile-sync-btn, .mobile-menu-btn {
    background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer;
    width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;
    border-radius: var(--radius); transition: background 0.15s, color 0.15s;
  }
  .mobile-sync-btn:hover, .mobile-menu-btn:hover { background: var(--surface-2); color: var(--text); }
  .mobile-sync-btn:disabled { opacity: 0.4; }

  /* App shell vertical */
  #app-shell { flex-direction: column; }

  .main-content { padding-bottom: 64px; }

  /* ── Bottom nav ──────────────────────────────── */
  .bottom-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 50;
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 6px 0;
    padding-bottom: max(6px, env(safe-area-inset-bottom));
  }
  .bottom-nav-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 0;
    text-decoration: none;
    color: var(--text-dim);
    font-size: 10px;
    transition: color 0.15s;
  }
  .bottom-nav-item.active { color: var(--teal); }
  .bottom-nav-icon { font-size: 18px; line-height: 1; }
  .bottom-nav-label { font-size: 10px; font-weight: 500; }
}

/* ── Mobile menu overlay ───────────────────────── */
.mobile-menu-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200;
}
.mobile-menu-panel {
  width: 280px; height: 100%; background: var(--surface); display: flex; flex-direction: column;
  animation: slideIn 0.2s ease;
}
@keyframes slideIn { from { transform: translateX(-100%); } to { transform: translateX(0); } }

.mobile-menu-header {
  display: flex; align-items: center; gap: 8px; padding: 16px; border-bottom: 1px solid var(--border);
}
.mobile-menu-close {
  margin-left: auto; background: none; border: none; color: var(--text-muted); font-size: 24px; cursor: pointer; line-height: 1;
}
.mobile-menu-nav { flex: 1; padding: 16px 12px; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }
.mobile-menu-footer { padding: 16px 12px; border-top: 1px solid var(--border); }
</style>
