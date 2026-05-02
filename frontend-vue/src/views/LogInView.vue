<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <span class="logo-box">📦</span>
        <h2>Autentificare</h2>
        <p>Introdu datele tale pentru a continua</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="input-group">
          <label>Utilizator sau Email</label>
          <input 
            type="text" 
            v-model="identifier" 
            placeholder="Username sau adresa de email" 
            required
          >
        </div>

        <div class="input-group">
          <label>Parolă</label>
          <input 
            type="password" 
            v-model="password" 
            placeholder="••••••••" 
            required
          >
        </div>

        <button type="submit" class="btn-submit">Conectare</button>
      </form>

      <div class="login-footer">
        Nu ai cont? <router-link to="/register">Creează unul aici</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../plugins/axios'
import { showToast } from '../toast'

// Variabila generică pentru username sau email
const identifier = ref('')
const password = ref('')
const router = useRouter()

const handleLogin = async () => {
  try {
    // 1. Facem cererea la adresa ta corectă de JWT
    const response = await api.post('login/', { 
      username: identifier.value,
      password: password.value
    });

    // 2. JWT returnează "access" în loc de "token"
    const realToken = response.data.access; 
    localStorage.setItem('access_token', realToken);
    
    showToast("Te-ai conectat cu succes!", "success");
    router.push('/');
    
  } catch (error) {
    console.error(error);
    showToast("Date de logare incorecte!", "error");
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center; /* Centrează pe orizontală */
  align-items: center;     /* Centrează pe verticală */
  
  /* Calculăm înălțimea: 100vh (toată înălțimea ecranului) 
     minus înălțimea aproximativă a header-ului și footer-ului */
  min-height: calc(100vh - 160px); 
  
  padding: 20px;
  background-color: #0f111a; /* Opțional: fundalul paginii */
}

.login-card {
  background-color: #1a1b26;
  border: 1px solid #2a2d3e;
  padding: 40px;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  
  /* Ne asigurăm că nu "fuge" cardul dacă e ecranul foarte mic */
  margin: auto; 
}

/* Restul stilurilor rămân la fel */
.login-header { text-align: center; margin-bottom: 30px; }
.logo-box { background: #3b82f6; padding: 10px; border-radius: 8px; display: inline-block; margin-bottom: 15px; }
h2 { color: white; margin-bottom: 5px; }
p { color: #94a3b8; font-size: 0.9rem; }
.input-group { margin-bottom: 20px; text-align: left; }
label { display: block; color: #e2e8f0; margin-bottom: 8px; font-size: 0.9rem; }
input { width: 100%; background: #0f111a; border: 1px solid #2a2d3e; padding: 12px; border-radius: 6px; color: white; outline: none; }
input:focus { border-color: #3b82f6; }
.btn-submit { width: 100%; background: #3b82f6; color: white; border: none; padding: 12px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-submit:hover { background: #2563eb; }
.login-footer { margin-top: 20px; text-align: center; color: #94a3b8; font-size: 0.85rem; }
.login-footer a { color: #3b82f6; text-decoration: none; }
</style>