<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <span class="logo-box">📦</span>
        <h2>Cont Nou</h2>
        <p>Alătură-te comunității PC Builder</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="input-group">
          <label>Nume Utilizator</label>
          <input type="text" v-model="username" placeholder="Username" required>
        </div>

        <div class="input-group">
          <label>Adresă Email</label>
          <input type="email" v-model="email" placeholder="email@exemplu.com" required>
        </div>

        <div class="input-group">
          <label>Parolă</label>
          <input type="password" v-model="password" placeholder="••••••••" required>
        </div>

        <div class="input-group">
          <label>Confirmă Parolă</label>
          <input type="password" v-model="confirmPassword" placeholder="••••••••" required>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button type="submit" class="btn-submit">Creează Cont</button>
      </form>

      <div class="register-footer">
        Ai deja cont? <router-link to="/login">Conectează-te aici</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const router = useRouter()

const handleRegister = () => {
  error.value = ''
  
  if (password.value !== confirmPassword.value) {
    error.value = "Parolele nu coincid!"
    return
  }

  console.log("Inregistrare:", { username: username.value, email: email.value })
  alert("Cont creat cu succes! (Simulare)")
  router.push('/login')
}
</script>

<style scoped>
/* Folosim aceleasi stiluri de la Login pentru uniformitate */
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 160px);
  padding: 20px;
}
.register-card {
  background-color: #1a1b26;
  border: 1px solid #2a2d3e;
  padding: 30px 40px;
  border-radius: 12px;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.5);
}
.register-header { text-align: center; margin-bottom: 25px; }
.logo-box { background: #3b82f6; padding: 10px; border-radius: 8px; display: inline-block; margin-bottom: 15px; }
h2 { color: white; margin-bottom: 5px; }
p { color: #94a3b8; font-size: 0.9rem; }
.input-group { margin-bottom: 15px; text-align: left; }
label { display: block; color: #e2e8f0; margin-bottom: 5px; font-size: 0.85rem; }
input { width: 100%; background: #0f111a; border: 1px solid #2a2d3e; padding: 10px; border-radius: 6px; color: white; outline: none; }
input:focus { border-color: #3b82f6; }
.error-msg { color: #ef4444; font-size: 0.8rem; margin-bottom: 10px; text-align: center; }
.btn-submit { width: 100%; background: #3b82f6; color: white; border: none; padding: 12px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s; margin-top: 10px; }
.btn-submit:hover { background: #2563eb; }
.register-footer { margin-top: 20px; text-align: center; color: #94a3b8; font-size: 0.85rem; }
.register-footer a { color: #3b82f6; text-decoration: none; }
</style>