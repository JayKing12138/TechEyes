import { defineStore } from 'pinia'
import { loginUser, registerUser, setAuthToken } from '@/services/api'

interface AuthUser {
  id: number
  username: string
}

interface AuthState {
  token: string
  user: AuthUser | null
}

const TOKEN_KEY = 'techeyes_auth_token'
const USER_KEY = 'techeyes_auth_user'

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: (() => {
      const raw = localStorage.getItem(USER_KEY)
      if (!raw) return null
      try {
        return JSON.parse(raw)
      } catch {
        return null
      }
    })(),
  }),

  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    username: (state) => state.user?.username || '',
  },

  actions: {
    async register(username: string, password: string) {
      await registerUser({ username, password })
      return this.login(username, password)
    },

    async login(username: string, password: string) {
      const data = await loginUser({ username, password })
      this.token = data.access_token
      this.user = data.user

      localStorage.setItem(TOKEN_KEY, this.token)
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      setAuthToken(this.token)
      return data
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      setAuthToken(null)
    },
  },
})
