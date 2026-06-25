<template>
  <div class="nav-settings-overlay" @click.self="$emit('close')">
    <div class="nav-settings-panel">
      <div class="nsp-header">
        <h2 class="nsp-title">Personnaliser</h2>
        <button class="nsp-close" @click="$emit('close')">×</button>
      </div>

      <!-- Onglets natifs -->
      <section class="nsp-section">
        <h3 class="nsp-section-title">Onglets natifs</h3>
        <div v-for="tab in navStore.allNativeTabs" :key="tab.id" class="nsp-toggle-row">
          <span class="nsp-toggle-icon">{{ tab.icon }}</span>
          <span class="nsp-toggle-label">{{ tab.label }}</span>
          <button class="nsp-toggle-btn" :class="{ active: !isHidden(tab.id) }" @click="toggleTab(tab.id)">
            {{ isHidden(tab.id) ? 'Masqué' : 'Visible' }}
          </button>
        </div>
      </section>

      <!-- Tableaux de bord personnalisés -->
      <section class="nsp-section">
        <h3 class="nsp-section-title">Tableaux de bord</h3>
        <div v-for="d in navStore.customDashboards" :key="d.slug" class="nsp-dash-row">
          <span class="nsp-dash-icon">{{ d.icon || '◇' }}</span>
          <span class="nsp-dash-name">{{ d.name }}</span>
          <button class="nsp-dash-del" @click="handleDeleteDashboard(d.slug)" title="Supprimer">×</button>
        </div>
        <div v-if="!navStore.customDashboards.length" class="nsp-empty mono">Aucun tableau de bord</div>
      </section>

      <button class="nsp-create-btn" @click="showCreate = true">+ Nouveau tableau de bord</button>

      <DashboardCreateModal v-if="showCreate" @close="showCreate = false" @saved="onDashboardCreated" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useNavStore } from '@/stores/nav'
import { useDashboardsStore } from '@/stores/dashboards'
import { useRouter } from 'vue-router'
import DashboardCreateModal from '@/components/dashboard-editor/DashboardCreateModal.vue'

defineEmits<{ close: [] }>()

const navStore = useNavStore()
const dashStore = useDashboardsStore()
const router = useRouter()
const showCreate = ref(false)

function isHidden(tabId: string) {
  return navStore.hiddenTabs.includes(tabId)
}

async function toggleTab(tabId: string) {
  const hidden = [...navStore.hiddenTabs]
  const idx = hidden.indexOf(tabId)
  if (idx >= 0) {
    hidden.splice(idx, 1)
  } else {
    hidden.push(tabId)
  }
  await navStore.updateHiddenTabs(hidden)
}

async function handleDeleteDashboard(slug: string) {
  await dashStore.deleteDashboard(slug)
}

function onDashboardCreated(slug: string) {
  showCreate.value = false
  router.push(`/d/${slug}`)
}
</script>

<style scoped>
.nav-settings-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; justify-content: flex-start; }
.nav-settings-panel { width: 340px; height: 100vh; background: var(--surface); border-right: 1px solid var(--border); padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 24px; }

.nsp-header { display: flex; justify-content: space-between; align-items: center; }
.nsp-title { font-size: 18px; font-weight: 600; }
.nsp-close { background: none; border: none; color: var(--text-muted); font-size: 22px; cursor: pointer; padding: 0; line-height: 1; }
.nsp-close:hover { color: var(--text); }

.nsp-section { display: flex; flex-direction: column; gap: 8px; }
.nsp-section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); font-weight: 600; }

.nsp-toggle-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
.nsp-toggle-icon { font-size: 14px; width: 18px; text-align: center; }
.nsp-toggle-label { flex: 1; font-size: 14px; }
.nsp-toggle-btn { padding: 4px 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); color: var(--text-dim); font-size: 11px; font-family: var(--mono); cursor: pointer; transition: all 0.15s; }
.nsp-toggle-btn.active { border-color: var(--teal); color: var(--teal); background: var(--teal-dim); }

.nsp-dash-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
.nsp-dash-icon { font-size: 16px; }
.nsp-dash-name { flex: 1; font-size: 14px; }
.nsp-dash-del { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px 6px; }
.nsp-dash-del:hover { color: var(--orange); }

.nsp-empty { font-size: 13px; color: var(--text-dim); padding: 8px 0; }

.nsp-create-btn { padding: 10px; border: 1px dashed var(--border); border-radius: var(--radius); background: transparent; color: var(--text-muted); font-family: var(--sans); font-size: 13px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.nsp-create-btn:hover { border-color: var(--teal); color: var(--teal); }
</style>
