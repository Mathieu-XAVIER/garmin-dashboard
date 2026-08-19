<template>
  <div class="objectif-carte" :class="{ atteint: objectif.atteint }">
    <div class="objectif-entete">
      <span class="objectif-libelle">{{ objectif.libelle }}</span>
      <span class="objectif-pourcentage mono">{{ objectif.pourcentage }} %</span>
    </div>

    <div class="jauge" role="progressbar" :aria-valuenow="objectif.pourcentage" aria-valuemin="0" aria-valuemax="100">
      <div class="jauge-remplissage" :style="{ width: Math.min(objectif.pourcentage, 100) + '%' }" />
    </div>

    <p class="objectif-detail mono">
      {{ formatValeur(objectif.actuel) }} / {{ formatValeur(objectif.cible) }}
      <span v-if="objectif.unite" class="objectif-unite">{{ objectif.unite }}</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import type { Progression } from '@/stores/goals'

defineProps<{ objectif: Progression }>()

function formatValeur(valeur: number): string {
  return Number.isInteger(valeur) ? String(valeur) : valeur.toFixed(1)
}
</script>

<style scoped>
.objectif-carte { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 14px 16px; }
.objectif-carte.atteint { border-color: rgba(0, 212, 170, 0.4); }

.objectif-entete { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
.objectif-libelle { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 600; }
.objectif-pourcentage { font-size: 13px; color: var(--text); font-weight: 600; }
.atteint .objectif-pourcentage { color: var(--teal); }

.jauge { height: 6px; background: var(--surface-2); border-radius: 3px; overflow: hidden; }
.jauge-remplissage { height: 100%; background: var(--teal); border-radius: 3px; transition: width 0.6s ease; }

.objectif-detail { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
.objectif-unite { color: var(--text-dim); }
</style>
