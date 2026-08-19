import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import router from '@/router'
import { useNavStore } from './nav'

interface AuthUser {
  id: number
  email: string
  has_garmin_credentials: boolean
  garmin_mfa_pending: boolean
  garmin_email: string | null
  created_at: string
  nav_preferences?: { hidden_tabs?: string[] } | null
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const params = new URLSearchParams()
      params.append('username', email)
      params.append('password', password)
      const { data } = await api.post('/auth/login', params)
      token.value = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await fetchMe()
      router.push('/')
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Erreur de connexion'
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post('/auth/register', { email, password })
      token.value = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await fetchMe()
      router.push('/')
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Erreur lors de l\'inscription'
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    router.push('/login')
  }

  async function fetchMe() {
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
      const navStore = useNavStore()
      navStore.syncFromAuth(data)
    } catch (e: any) {
      // Seul un token réellement invalide justifie une déconnexion :
      // une coupure réseau ou un backend qui redémarre ne doit rien effacer.
      if (e.response?.status === 401) {
        logout()
      }
    }
  }

  async function updateGarminCredentials(garminEmail: string, garminPassword: string) {
    const { data } = await api.put('/auth/garmin-credentials', {
      garmin_email: garminEmail,
      garmin_password: garminPassword,
    })
    if (user.value) {
      user.value.has_garmin_credentials = true
      user.value.garmin_email = garminEmail
      user.value.garmin_mfa_pending = data.mfa_required
    }
    return data
  }

  async function submitGarminMfa(code: string) {
    const { data } = await api.post('/auth/garmin-mfa', { code })
    if (user.value) {
      user.value.garmin_mfa_pending = false
    }
    return data
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    await api.put('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  }

  async function forgotPassword(emailAddress: string) {
    const { data } = await api.post('/auth/forgot-password', { email: emailAddress })
    return data.message as string
  }

  async function resetPassword(resetToken: string, newPassword: string) {
    await api.post('/auth/reset-password', {
      token: resetToken,
      new_password: newPassword,
    })
  }

  async function deleteGarminCredentials() {
    await api.delete('/auth/garmin-credentials')
    if (user.value) {
      user.value.has_garmin_credentials = false
      user.value.garmin_email = null
    }
  }

  return {
    user, token, loading, error, isAuthenticated,
    login, register, logout, fetchMe,
    updateGarminCredentials, deleteGarminCredentials, submitGarminMfa,
    changePassword, forgotPassword, resetPassword,
  }
})
