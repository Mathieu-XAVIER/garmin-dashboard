<template>
  <div class="view">
    <header class="view-header">
      <div>
        <h1 class="view-title">{{ dashboard?.name || 'Dashboard' }}</h1>
        <p class="view-sub mono" v-if="dashboard?.config?.description">{{ dashboard.config.description }}</p>
      </div>
      <div class="view-actions">
        <button class="edit-toggle" @click="toggleEdit" :class="{ active: editMode }">
          {{ editMode ? 'Terminé' : 'Modifier' }}
        </button>
      </div>
    </header>

    <SkeletonLoader v-if="store.loading" type="kpi" :count="4" />

    <template v-else-if="store.currentDashboard">
      <div class="widget-grid" :class="{ editing: editMode }">
        <div v-for="(widget, idx) in localWidgets" :key="widget.id"
             class="widget-cell" :class="[`width-${widget.width}`, {
               dragging: dragIdx === idx,
               'drag-over': dropIdx === idx && dropIdx !== dragIdx,
             }]"
             :draggable="editMode"
             @dragstart="onDragStart(idx, $event)"
             @dragover.prevent="onDragOver(idx)"
             @dragleave="onDragLeave(idx)"
             @drop.prevent="onDrop(idx)"
             @dragend="onDragEnd">
          <div v-if="editMode" class="widget-toolbar">
            <span class="wt-handle" title="Déplacer">⠿</span>
            <span class="wt-title mono">{{ widget.widget_type }}</span>
            <div class="wt-actions">
              <select class="wt-width-select" :value="widget.width" @change="onWidthChange(widget.id, ($event.target as HTMLSelectElement).value)">
                <option value="quarter">1/4</option>
                <option value="half">1/2</option>
                <option value="full">Plein</option>
              </select>
              <button class="wt-del" @click="handleDeleteWidget(widget.id)" title="Supprimer">×</button>
            </div>
          </div>
          <WidgetRenderer :widget="widget" :dashboard="dashboard!" />
        </div>
      </div>

      <div v-if="editMode" class="add-widget-area">
        <button class="add-widget-btn" @click="showWidgetModal = true">+ Ajouter un widget</button>
        <button class="edit-dashboard-btn" @click="showDashboardEdit = true">Paramètres du dashboard</button>
      </div>

      <WidgetAddModal v-if="showWidgetModal" :slug="slug" @close="showWidgetModal = false" @added="onWidgetAdded" />
      <DashboardCreateModal v-if="showDashboardEdit" :dashboard="dashboard" @close="showDashboardEdit = false" @saved="onDashboardSaved" />
    </template>

    <div v-else-if="store.error" class="error-state">{{ store.error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDashboardsStore, type Widget } from '@/stores/dashboards'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import WidgetRenderer from '@/components/widgets/WidgetRenderer.vue'
import WidgetAddModal from '@/components/dashboard-editor/WidgetAddModal.vue'
import DashboardCreateModal from '@/components/dashboard-editor/DashboardCreateModal.vue'

const route = useRoute()
const router = useRouter()
const store = useDashboardsStore()

const editMode = ref(false)
const showWidgetModal = ref(false)
const showDashboardEdit = ref(false)

const slug = computed(() => route.params.slug as string)
const dashboard = computed(() => store.currentDashboard?.dashboard ?? null)
const widgets = computed(() => store.currentDashboard?.widgets ?? [])

const localWidgets = ref<Widget[]>([])
const orderDirty = ref(false)

watch(widgets, (w) => {
  localWidgets.value = [...w]
  orderDirty.value = false
}, { immediate: true })

// --- Drag & drop ---
const dragIdx = ref<number | null>(null)
const dropIdx = ref<number | null>(null)

function onDragStart(idx: number, e: DragEvent) {
  dragIdx.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx))
  }
}

function onDragOver(idx: number) {
  dropIdx.value = idx
}

function onDragLeave(idx: number) {
  if (dropIdx.value === idx) dropIdx.value = null
}

function onDrop(idx: number) {
  if (dragIdx.value === null || dragIdx.value === idx) return
  const list = [...localWidgets.value]
  const [moved] = list.splice(dragIdx.value, 1)
  list.splice(idx, 0, moved)
  localWidgets.value = list
  orderDirty.value = true
  dragIdx.value = null
  dropIdx.value = null
}

function onDragEnd() {
  dragIdx.value = null
  dropIdx.value = null
}

async function saveOrder() {
  if (!orderDirty.value) return
  const order = localWidgets.value.map(w => w.id)
  await store.reorderWidgets(slug.value, order)
  orderDirty.value = false
  await load()
}

async function toggleEdit() {
  if (editMode.value) {
    await saveOrder()
  }
  editMode.value = !editMode.value
}

async function onWidthChange(widgetId: number, newWidth: string) {
  await store.updateWidget(slug.value, widgetId, { width: newWidth })
  await load()
}

// --- CRUD ---

async function load() {
  await store.fetchDashboardData(slug.value)
}

onMounted(load)
watch(slug, load)

async function handleDeleteWidget(widgetId: number) {
  await store.deleteWidget(slug.value, widgetId)
  await load()
}

async function onWidgetAdded() {
  showWidgetModal.value = false
  await load()
}

async function onDashboardSaved(newSlug?: string) {
  showDashboardEdit.value = false
  if (newSlug && newSlug !== slug.value) {
    router.replace(`/d/${newSlug}`)
  } else {
    await load()
  }
}
</script>

<style scoped>
.view { padding: 32px 40px; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
.view-title { font-size: 24px; font-weight: 600; }
.view-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.view-actions { display: flex; gap: 8px; }

.edit-toggle { padding: 6px 14px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-family: var(--sans); font-size: 12px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.edit-toggle:hover, .edit-toggle.active { border-color: var(--teal); color: var(--teal); }

.widget-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.widget-grid.editing .widget-cell { position: relative; }

.widget-cell.width-quarter { grid-column: span 1; }
.widget-cell.width-half { grid-column: span 2; }
.widget-cell.width-full { grid-column: span 4; }

.widget-cell.dragging { opacity: 0.3; }
.widget-cell.drag-over { outline: 2px dashed var(--teal); outline-offset: 4px; border-radius: var(--radius-lg); }

.widget-cell[draggable="true"] { cursor: grab; }
.widget-cell[draggable="true"]:active { cursor: grabbing; }

.widget-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.wt-handle { font-size: 16px; color: var(--text-dim); cursor: grab; user-select: none; line-height: 1; }
.wt-handle:active { cursor: grabbing; }
.wt-title { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; flex: 1; }
.wt-actions { display: flex; align-items: center; gap: 6px; }
.wt-width-select { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-muted); font-size: 11px; font-family: var(--mono); padding: 2px 6px; cursor: pointer; outline: none; }
.wt-width-select:focus { border-color: var(--teal); }
.wt-del { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px 6px; border-radius: var(--radius); }
.wt-del:hover { color: var(--orange); background: var(--surface-2); }

.add-widget-area { display: flex; gap: 12px; margin-top: 24px; }
.add-widget-btn, .edit-dashboard-btn { padding: 10px 20px; border: 1px dashed var(--border); border-radius: var(--radius-lg); background: transparent; color: var(--text-muted); font-family: var(--sans); font-size: 13px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.add-widget-btn:hover { border-color: var(--teal); color: var(--teal); }
.edit-dashboard-btn:hover { border-color: var(--purple); color: var(--purple); }

.error-state { padding: 64px; text-align: center; color: var(--text-muted); }

@media (max-width: 900px) {
  .view { padding: 20px 16px; }
  .widget-grid { grid-template-columns: repeat(2, 1fr); }
  .widget-cell.width-full { grid-column: span 2; }
  .widget-cell.width-quarter { grid-column: span 1; }
}
</style>
