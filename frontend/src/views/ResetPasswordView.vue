<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <span class="logo-icon">⬡</span>
        <span class="logo-text">Garmin<br><strong>Dashboard</strong></span>
      </div>

      <h1 class="page-title">Nouveau mot de passe</h1>

      <p v-if="!token" class="error-msg">
        Lien incomplet : le jeton de réinitialisation est absent de l'adresse.
      </p>

      <template v-else-if="!termine">
        <p class="page-sub">Choisissez un mot de passe d'au moins 8 caractères.</p>

        <form @submit.prevent="handleSubmit" class="login-form">
          <div class="field">
            <label for="pwd">Nouveau mot de passe</label>
            <input id="pwd" v-model="motDePasse" type="password" placeholder="••••••••" required autocomplete="new-password" />
          </div>

          <div class="field">
            <label for="pwd2">Confirmation</label>
            <input id="pwd2" v-model="confirmation" type="password" placeholder="••••••••" required autocomplete="new-password" />
          </div>

          <p v-if="erreur" class="error-msg">{{ erreur }}</p>

          <button type="submit" class="submit-btn" :disabled="loading">
            {{ loading ? 'Enregistrement…' : 'Valider' }}
          </button>
        </form>
      </template>

      <p v-else class="confirmation">
        Mot de passe mis à jour. Vous pouvez vous connecter.
      </p>

      <RouterLink to="/login" class="retour">← Retour à la connexion</RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const token = computed(() => (route.query.token as string) ?? '')
const motDePasse = ref('')
const confirmation = ref('')
const loading = ref(false)
const termine = ref(false)
const erreur = ref<string | null>(null)

async function handleSubmit() {
  erreur.value = null
  if (motDePasse.value !== confirmation.value) {
    erreur.value = 'Les deux mots de passe ne correspondent pas'
    return
  }
  loading.value = true
  try {
    await authStore.resetPassword(token.value, motDePasse.value)
    termine.value = true
  } catch (e: any) {
    erreur.value = e.response?.data?.detail ?? 'Une erreur est survenue'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); padding: 20px; }
.login-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 40px 36px; width: 100%; max-width: 400px; }
.login-logo { display: flex; align-items: center; gap: 10px; justify-content: center; margin-bottom: 28px; }
.logo-icon { font-size: 26px; color: var(--teal); }
.logo-text { font-family: var(--sans); font-size: 12px; color: var(--text-muted); line-height: 1.4; text-transform: uppercase; letter-spacing: 0.05em; }
.logo-text strong { color: var(--text); font-weight: 600; font-size: 14px; text-transform: none; letter-spacing: 0; }

.page-title { font-size: 16px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
.page-sub { font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 24px; }

.login-form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
.field input { padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text); font-family: var(--mono); font-size: 14px; outline: none; transition: border-color 0.15s; }
.field input:focus { border-color: var(--teal); }
.field input::placeholder { color: var(--text-dim); }

.error-msg { color: var(--orange); font-size: 13px; font-family: var(--mono); text-align: center; padding: 8px; background: rgba(255, 107, 53, 0.08); border-radius: var(--radius); }
.confirmation { font-size: 13px; color: var(--teal); line-height: 1.5; padding: 12px; background: var(--teal-dim); border-radius: var(--radius); }

.submit-btn { padding: 11px 0; background: var(--teal); color: #000; border: none; border-radius: var(--radius); font-family: var(--sans); font-size: 14px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; margin-top: 4px; }
.submit-btn:hover:not(:disabled) { opacity: 0.9; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.retour { display: block; text-align: center; margin-top: 22px; font-size: 13px; color: var(--text-muted); text-decoration: none; transition: color 0.15s; }
.retour:hover { color: var(--teal); }
</style>
