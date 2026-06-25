<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <span class="logo-icon">⬡</span>
        <span class="logo-text">Garmin<br><strong>Dashboard</strong></span>
      </div>

      <div class="tab-toggle">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">Connexion</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">Inscription</button>
      </div>

      <form @submit.prevent="handleSubmit" class="login-form">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" placeholder="votre@email.com" required autocomplete="email" />
        </div>

        <div class="field">
          <label for="password">Mot de passe</label>
          <input id="password" v-model="password" type="password" placeholder="••••••••" required autocomplete="current-password" />
        </div>

        <p v-if="mode === 'register'" class="hint">6 caractères minimum</p>

        <p v-if="authStore.error" class="error-msg">{{ authStore.error }}</p>

        <button type="submit" class="submit-btn" :disabled="authStore.loading">
          {{ authStore.loading ? 'Chargement…' : (mode === 'login' ? 'Se connecter' : 'Créer un compte') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')

async function handleSubmit() {
  authStore.error = null
  try {
    if (mode.value === 'login') {
      await authStore.login(email.value, password.value)
    } else {
      await authStore.register(email.value, password.value)
    }
  } catch {
    // error is handled in the store
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 20px;
}

.login-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 40px 36px;
  width: 100%;
  max-width: 400px;
}

.login-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  margin-bottom: 32px;
}
.logo-icon { font-size: 26px; color: var(--teal); }
.logo-text {
  font-family: var(--sans);
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.logo-text strong {
  color: var(--text);
  font-weight: 600;
  font-size: 14px;
  text-transform: none;
  letter-spacing: 0;
}

.tab-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  background: var(--surface-2);
  border-radius: var(--radius);
  padding: 3px;
  margin-bottom: 28px;
}
.tab-toggle button {
  padding: 8px 0;
  border: none;
  border-radius: calc(var(--radius) - 2px);
  background: transparent;
  color: var(--text-muted);
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.tab-toggle button.active {
  background: var(--surface);
  color: var(--text);
}

.login-form { display: flex; flex-direction: column; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  font-weight: 500;
}
.field input {
  padding: 10px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--mono);
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.field input:focus {
  border-color: var(--teal);
}
.field input::placeholder {
  color: var(--text-dim);
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--mono);
  margin-top: -8px;
}

.error-msg {
  color: var(--orange);
  font-size: 13px;
  font-family: var(--mono);
  text-align: center;
  padding: 8px;
  background: rgba(255, 107, 53, 0.08);
  border-radius: var(--radius);
}

.submit-btn {
  padding: 11px 0;
  background: var(--teal);
  color: #000;
  border: none;
  border-radius: var(--radius);
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  margin-top: 4px;
}
.submit-btn:hover:not(:disabled) { opacity: 0.9; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
