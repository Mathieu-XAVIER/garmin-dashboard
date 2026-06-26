import { ref } from 'vue'
import { defineStore } from 'pinia'

export type NotificationType = 'success' | 'error' | 'info' | 'warning'

export interface Notification {
  id: string
  type: NotificationType
  message: string
  duration: number
}

let _counter = 0

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])

  function push(opts: { type: NotificationType; message: string; duration?: number }): string {
    const id = `notif-${++_counter}`
    const duration = opts.duration ?? 4000

    if (items.value.length >= 5) items.value.shift()
    items.value.push({ id, type: opts.type, message: opts.message, duration })

    if (duration > 0) {
      setTimeout(() => dismiss(id), duration)
    }

    return id
  }

  function dismiss(id: string) {
    const idx = items.value.findIndex(n => n.id === id)
    if (idx !== -1) items.value.splice(idx, 1)
  }

  function clear() {
    items.value = []
  }

  const success = (message: string, duration?: number) => push({ type: 'success', message, duration })
  const error   = (message: string, duration?: number) => push({ type: 'error', message, duration })
  const info    = (message: string, duration?: number) => push({ type: 'info', message, duration })
  const warning = (message: string, duration?: number) => push({ type: 'warning', message, duration })

  return { items, push, dismiss, clear, success, error, info, warning }
})
