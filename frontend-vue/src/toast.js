import { ref } from 'vue'

export const toastMessage = ref('')
export const toastType = ref('success') // Poate fi 'success' sau 'error'

export const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  
  // Ascundem pop-up-ul automat după 3 secunde
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}