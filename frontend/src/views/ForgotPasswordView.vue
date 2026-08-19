<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <span class="logo-icon">⬡</span>
        <span class="logo-text">Garmin<br><strong>Dashboard</strong></span>
      </div>

      <h1 class="page-title">Mot de passe oublié</h1>
      <p class="page-sub">
        Saisissez votre adresse : si un compte y est rattaché, vous recevrez un
        lien pour choisir un nouveau mot de passe.
      </p>

      <form v-if="!envoye" @submit.prevent="handleSubmit" class="login-form">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" placeholder="votre@email.com" required autocomplete="email" />
        </div>

        <p v-if="erreur" class="error-msg">{{ erreur }}</p>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? 'Envoi…' : 'Envoyer le lien' }}
        </button>
      </form>

      <p v-else class="confirmation">{{ message }}</p>

      <RouterLink to="/login" class="retour">← Retour à la connexion</RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const email = ref('')
const loading = ref(false)
const envoye = ref(false)
const message = ref('')
const erreur = ref<string | null>(null)

async function handleSubmit() {
  loading.value = true
  erreur.value = null
  try {
    message.value = await authStore.forgotPassword(email.value)
    envoye.value = true
  } catch (e: any) {
    erreur.value = e.response?.status === 429
      ? 'Trop de demandes. Réessayez dans un moment.'
      : (e.response?.data?.detail ?? 'Une erreur est survenue')
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
