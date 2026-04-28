<template>
  <div class="app-wrapper">
    <header class="pcpp-header">
      
      <div class="top-tier">
        <div class="container top-tier-content">
          <div class="logo" @click="currentTab = 'builder'">
            <span class="logo-box">📦</span>
            <span class="logo-text">PC BUILDER <span class="text-light">SIMULATOR</span></span>
          </div>
          
          <div class="user-actions">
<<<<<<< HEAD
            <button class="text-link">Log In</button>
            <span class="divider"></span>
            <button class="text-link">Register</button>
=======
            <button class="text-link" @click="currentTab = 'login'">Log In</button>
            <span class="divider"></span>
            <button class="text-link" @click="currentTab = 'register'">Register</button>
>>>>>>> origin/radu
            <span class="divider"></span>
            <button class="lang-select">
              🇷🇴 Romania <span class="arrow">▼</span>
            </button>
            <button class="theme-toggle">🌙</button>
          </div>
        </div>
      </div>

      <div class="bottom-tier">
        <div class="container bottom-tier-content">
          <nav class="main-nav">
            <button 
              @click="currentTab = 'builder'" 
              :class="{ active: currentTab === 'builder' }"
            >
              <span class="icon">🔧</span> Builder
            </button>

            <button 
              @click="currentTab = 'products'" 
              :class="{ active: currentTab === 'products' }"
            >
              <span class="icon">🪪</span> Products <span class="arrow">▼</span>
            </button>

            <button 
              @click="currentTab = 'guides'" 
              :class="{ active: currentTab === 'guides' }"
            >
              <span class="icon">📄</span> Guides
            </button>

            <button 
              @click="currentTab = 'completed'" 
              :class="{ active: currentTab === 'completed' }"
            >
              <span class="icon">🖥️</span> Completed Builds
            </button>

            <button 
              @click="currentTab = 'trends'" 
              :class="{ active: currentTab === 'trends' }"
            >
              <span class="icon">📈</span> Trends
            </button>

            <button 
              @click="currentTab = 'benchmarks'" 
              :class="{ active: currentTab === 'benchmarks' }"
            >
              <span class="icon">⏱️</span> Benchmarks
            </button>
          </nav>

          <div class="search-bar">
            <button class="search-btn">🔍</button>
          </div>
        </div>
      </div>
    </header>

    <main class="main-content">
      
      <BuilderView v-if="currentTab === 'builder'" />
<<<<<<< HEAD
=======

      <div v-else-if="currentTab === 'login'" class="auth-wrapper">
        <Login />
      </div>

      <div v-else-if="currentTab === 'register'" class="auth-wrapper">
        <Register />
      </div>
>>>>>>> origin/radu
      
      <div v-else class="page-placeholder container">
        <h2>Secțiunea: {{ currentTab.toUpperCase() }}</h2>
        <p>Aici va veni conținutul pentru această pagină.</p>
        <button class="btn btn-outline" @click="currentTab = 'builder'">Întoarce-te la Builder</button>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
<<<<<<< HEAD
// Asigură-te că calea către BuilderView este corectă pentru proiectul tău
import BuilderView from './components/BuilderView.vue'

// Setăm 'builder' ca pagină implicită, exact cum face site-ul original
=======
import BuilderView from './components/BuilderView.vue'
// Importuri Noi:
import Login from './components/Login.vue'
import Register from './components/Register.vue'

>>>>>>> origin/radu
const currentTab = ref('builder') 
</script>

<style scoped>
<<<<<<< HEAD
/* Reset și setări de bază pentru a nu fi afectate de CSS-ul global */
=======
/* Păstrăm tot CSS-ul tău original neschimbat */
>>>>>>> origin/radu
.app-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

button {
  font-family: inherit;
  background: none;
  border: none;
  cursor: pointer;
}

<<<<<<< HEAD
/* --- HEADER PRINCIPAL --- */
=======
>>>>>>> origin/radu
.pcpp-header {
  display: flex;
  flex-direction: column;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

<<<<<<< HEAD
/* --- NIVELUL 1: TOP TIER --- */
.top-tier {
  background-color: #111116; /* Negru închis */
=======
.top-tier {
  background-color: #111116;
>>>>>>> origin/radu
  border-bottom: 1px solid #1a1b26;
}

.top-tier-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 50px;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #ffffff;
}

.logo-box {
  font-size: 1.8rem;
}

.text-light {
  color: #b0b3c6;
  font-weight: 500;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.text-link, .lang-select {
  color: #b0b3c6;
  font-size: 0.85rem;
  font-weight: 600;
  transition: color 0.2s;
}

.text-link:hover, .lang-select:hover {
  color: #ffffff;
}

.divider {
  width: 1px;
  height: 14px;
  background-color: #3f4455;
}

.arrow {
  font-size: 0.6rem;
  margin-left: 4px;
}

.theme-toggle {
  background-color: #232533;
  border-radius: 4px;
  padding: 4px 8px;
  margin-left: 10px;
}

<<<<<<< HEAD
/* --- NIVELUL 2: BOTTOM TIER --- */
.bottom-tier {
  background-color: #1a1b26; /* Bleumarin închis / Gri închis */
=======
.bottom-tier {
  background-color: #1a1b26;
>>>>>>> origin/radu
  border-bottom: 1px solid #2a2d3e;
}

.bottom-tier-content {
  display: flex;
  justify-content: space-between;
<<<<<<< HEAD
  align-items: stretch; /* Pentru a face butoanele să ocupe toată înălțimea */
=======
  align-items: stretch;
>>>>>>> origin/radu
  height: 55px;
}

.main-nav {
  display: flex;
  height: 100%;
}

.main-nav button {
  color: #e2e8f0;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-right: 1px solid #2a2d3e;
  transition: background-color 0.2s;
}

.main-nav button:first-child {
  border-left: 1px solid #2a2d3e;
}

.main-nav button .icon {
  font-size: 1.1rem;
  opacity: 0.7;
}

.main-nav button:hover {
  background-color: #232533;
}

.main-nav button.active {
  background-color: #2a2d3e;
  color: #ffffff;
}

.search-bar {
  display: flex;
  align-items: center;
  padding-right: 20px;
}

.search-btn {
  color: #b0b3c6;
  font-size: 1.2rem;
}

.search-btn:hover {
  color: #ffffff;
}

<<<<<<< HEAD
/* --- STILURI PLACEHOLDER PAGINI --- */
.page-placeholder {
  text-align: center;
  padding: 80px 20px;
  background-color: var(--panel-bg);
  border-radius: 8px;
  margin-top: 40px;
  border: 1px solid var(--panel-border);
=======
.page-placeholder {
  text-align: center;
  padding: 80px 20px;
  background-color: #1a1b26;
  border-radius: 8px;
  margin-top: 40px;
  border: 1px solid #2a2d3e;
}

/* Stil nou pentru centrarea formularelor de login/register */
.auth-wrapper {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 60px;
  min-height: 400px;
>>>>>>> origin/radu
}
</style>