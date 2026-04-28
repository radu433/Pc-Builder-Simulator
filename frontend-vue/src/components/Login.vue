<template>
  <div class="box">
    <h2>Intră în Cont</h2>
    <form @submit.prevent="intraInCont">
      <input type="text" v-model="username" placeholder="Nume utilizator" required />
      <input type="password" v-model="password" placeholder="Parola" required />
      <button type="submit">Logare</button>
    </form>
    <p v-if="mesaj">{{ mesaj }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '../plugins/axios.js'; 

const username = ref('');
const password = ref('');
const mesaj = ref('');

const intraInCont = async () => {
  try {
    // Cerem token-ul de la Django
    const response = await api.post('login/', {
      username: username.value,
      password: password.value
    });
    
    // Daca a mers, Django ne da token-urile
    const token = response.data.access;
    const refresh = response.data.refresh;
    
    // Le salvam in memoria browserului
    localStorage.setItem('access_token', token);
    localStorage.setItem('refresh_token', refresh);
    
    mesaj.value = "Te-ai logat cu succes!";
    
  } catch (error) {
    mesaj.value = "Parolă sau utilizator greșit!";
    console.error(error);
  }
};
</script>

<style scoped>
.box { border: 1px solid #ccc; padding: 20px; margin: 10px; display: flex; flex-direction: column; gap: 10px; width: 250px; }
input { padding: 5px; }
button { padding: 8px; cursor: pointer; }
</style>