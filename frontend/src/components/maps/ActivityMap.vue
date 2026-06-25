<template>
  <div v-if="hasGps" class="map-section">
    <h2 class="section-title">Parcours</h2>

    <div class="map-card" :class="{ fullscreen: isFullscreen }">
      <div v-if="loading" class="map-loading">
        <SkeletonLoader type="chart" />
      </div>
      <template v-else>
        <button class="expand-btn" @click="toggleFullscreen" :title="isFullscreen ? 'Réduire' : 'Agrandir'">
          {{ isFullscreen ? '✕' : '⛶' }}
        </button>
        <div ref="mapContainer" class="map-container"></div>
      </template>
    </div>

    <div v-if="elevationData.length" class="chart-card">
      <AreaChart
        :data="elevationData"
        label="Altitude"
        color="#7C6FCD"
        :height="120"
        unit="m"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import api from '@/api'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import SkeletonLoader from '../SkeletonLoader.vue'
import AreaChart from '../charts/AreaChart.vue'

interface TrackPoint {
  lat: number
  lon: number
  altitude?: number
  time?: number
  speed?: number
  hr?: number
}

const props = defineProps<{
  garminId: string
}>()

const loading = ref(true)
const hasGps = ref(false)
const track = ref<TrackPoint[]>([])
const mapContainer = ref<HTMLElement | null>(null)
const isFullscreen = ref(false)
let mapInstance: L.Map | null = null

const elevationData = ref<{ x: string | number; y: number | null }[]>([])

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
  setTimeout(() => {
    mapInstance?.invalidateSize()
    if (mapInstance && track.value.length) {
      const latLngs: L.LatLngTuple[] = track.value.map(pt => [pt.lat, pt.lon])
      mapInstance.fitBounds(L.latLngBounds(latLngs), { padding: [30, 30] })
    }
  }, 100)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isFullscreen.value) {
    toggleFullscreen()
  }
}

onUnmounted(() => {
  document.body.style.overflow = ''
  document.removeEventListener('keydown', onKeydown)
})

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  try {
    const { data } = await api.get(`/activities/${props.garminId}/gps`)
    if (data.has_gps && data.track?.length) {
      track.value = data.track
      hasGps.value = true
      buildElevationData()
    }
  } catch {
    hasGps.value = false
  } finally {
    loading.value = false
  }
})

watch([hasGps, loading], async ([gps, load]) => {
  if (gps && !load) {
    await nextTick()
    initMap()
  }
})

function buildElevationData() {
  let distAccum = 0
  const points = track.value.filter((pt): pt is TrackPoint & { altitude: number } => pt.altitude != null)
  elevationData.value = points.map((pt, i, arr) => {
    if (i > 0) {
      distAccum += haversine(arr[i - 1]!, pt)
    }
    return {
      x: (distAccum / 1000).toFixed(1),
      y: Math.round(pt.altitude!),
    }
  })
}

function initMap() {
  if (!mapContainer.value || !track.value.length) return

  const latLngs: L.LatLngTuple[] = track.value.map(pt => [pt.lat, pt.lon])

  const map = L.map(mapContainer.value, {
    zoomControl: true,
    attributionControl: false,
  })
  mapInstance = map

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd',
  }).addTo(map)

  L.polyline(latLngs, {
    color: '#00D4AA',
    weight: 3,
    opacity: 0.9,
    smoothFactor: 1,
  }).addTo(map)

  const start = latLngs[0]
  const end = latLngs[latLngs.length - 1]

  if (start) {
    L.circleMarker(start, {
      radius: 7,
      color: '#00D4AA',
      fillColor: '#00D4AA',
      fillOpacity: 1,
      weight: 2,
    }).addTo(map).bindTooltip('Départ', { direction: 'top', offset: [0, -8] })
  }

  if (end) {
    L.circleMarker(end, {
      radius: 7,
      color: '#FF6B35',
      fillColor: '#FF6B35',
      fillOpacity: 1,
      weight: 2,
    }).addTo(map).bindTooltip('Arrivée', { direction: 'top', offset: [0, -8] })
  }

  const bounds = L.latLngBounds(latLngs)
  map.fitBounds(bounds, { padding: [30, 30] })
}

function haversine(a: TrackPoint, b: TrackPoint): number {
  const R = 6371000
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLon = toRad(b.lon - a.lon)
  const sinLat = Math.sin(dLat / 2)
  const sinLon = Math.sin(dLon / 2)
  const h = sinLat * sinLat + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * sinLon * sinLon
  return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h))
}
</script>

<style scoped>
.map-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-weight: 500;
  margin-bottom: 14px;
}

.map-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  position: relative;
}

.map-card.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  border-radius: 0;
  border: none;
}

.map-card.fullscreen .map-container {
  height: 100vh;
}

.map-container {
  height: 400px;
  width: 100%;
}

.expand-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10000;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  line-height: 1;
}

.expand-btn:hover {
  background: var(--surface-2);
  color: var(--text);
  border-color: var(--teal);
}

.map-loading {
  padding: 16px;
}

.chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 12px 8px;
  margin-top: 12px;
}

:deep(.leaflet-control-zoom a) {
  background: var(--surface) !important;
  color: var(--text-muted) !important;
  border-color: var(--border) !important;
}

:deep(.leaflet-control-zoom a:hover) {
  background: var(--surface-2) !important;
  color: var(--text) !important;
}

:deep(.leaflet-tooltip) {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  font-family: var(--mono);
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

:deep(.leaflet-tooltip-top::before) {
  border-top-color: var(--border);
}
</style>
