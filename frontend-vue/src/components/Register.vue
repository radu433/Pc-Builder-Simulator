<template>
  <div class="box">
    <h2>Creare Cont Nou</h2>
    <form @submit.prevent="creeazaCont">
      <input type="text" v-model="username" placeholder="Nume utilizator" required />
      <input type="email" v-model="email" placeholder="Email" required />
      <input type="password" v-model="password" placeholder="Parola" required />
      <button type="submit">Înregistrare</button>
    </form>
    <p v-if="mesaj">{{ mesaj }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '../plugins/axios.js';

const username = ref('');
const email = ref('');
const password = ref('');
const mesaj = ref('');

const creeazaCont = async () => {
  try {
    // Trimitem datele la Django pe ruta de register
    await api.post('accounts/register/', {
      username: username.value,
      email: email.value,
      password: password.value
    });
    
    mesaj.value = "Cont creat cu succes! Te poți loga acum.";
    // Curatam casutele
    username.value = '';
    email.value = '';
    password.value = '';
    
  } catch (error) {
    mesaj.value = "Eroare! Poate userul sau emailul există deja.";
    console.error(error);
  }
};
</script>

<style scoped>
.box { border: 1px solid #ccc; padding: 20px; margin: 10px; display: flex; flex-direction: column; gap: 10px; width: 250px; }
input { padding: 5px; }
button { padding: 8px; cursor: pointer; }
</style>