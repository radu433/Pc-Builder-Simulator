<template>
  <div class="app-wrapper">
    <header class="pcpp-header">
      
      <div class="top-tier">
        <div class="container top-tier-content">
          <router-link to="/" class="logo" style="text-decoration: none; cursor: pointer;">
            <span class="logo-box">📦</span>
            <span class="logo-text">PC BUILDER <span class="text-light">SIMULATOR</span></span>
          </router-link>
          
          <div class="user-actions">

            <template v-if="!isLoggedIn">
              <router-link to="/login" class="text-link">Log In</router-link>
              <span class="divider"></span>
              <router-link to="/register" class="text-link">Register</router-link>
              <span class="divider"></span>
              <button class="lang-select">🇷🇴 Romania <span class="arrow">▼</span></button>
            </template>

            <template v-else>
              <div class="account-menu" @click="toggleDropdown" ref="accountMenuRef">
                <div class="account-btn">
                  <div class="account-avatar">{{ userInitial }}</div>
                  <span class="account-name">{{ username }}</span>
                  <span class="arrow">▼</span>
                </div>

                <div v-if="dropdownOpen" class="account-dropdown">
                  <div class="dropdown-header">
                    <div class="dropdown-avatar">{{ userInitial }}</div>
                    <div>
                      <div class="dropdown-name">{{ username }}</div>
                      <div class="dropdown-role">Utilizator</div>
                    </div>
                  </div>
                  <div class="dropdown-divider"></div>
                  <router-link to="/completed-builds" class="dropdown-item" @click="dropdownOpen = false">
                    📂 Build-urile mele
                  </router-link>
                  <router-link to="/profile" class="dropdown-item" @click="dropdownOpen = false">
                    ⚙️ Preferințele mele
                  </router-link>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item dropdown-logout" @click="logout">
                    🚪 Deconectare
                  </button>
                </div>
              </div>
            </template>

            <button class="theme-toggle">🌙</button>
          </div>
        </div>
      </div>

      <div class="bottom-tier">
        <div class="container bottom-tier-content">
          <nav class="main-nav">
            <router-link to="/" class="nav-button" active-class="active-nav">
              <span class="icon">🔧</span> Builder
            </router-link>
            
            <router-link to="/chat-ai" class="nav-button ai-nav-button" active-class="active-nav-ai">
              <span class="icon spark-icon">✨</span> Build AI
            </router-link>

            <div class="nav-item-dropdown">
  <button class="nav-button">
    <span class="icon">🪪</span> Products <span class="arrow">▼</span>
  </button>
  
                <div class="nav-submenu products-mega-menu">
                  <div class="mega-menu-grid">
                    <router-link to="/products/cpus" class="submenu-item">
                      <span class="icon">🧠</span> Procesoare (CPU)
                    </router-link>
                    <router-link to="/products/gpus" class="submenu-item">
                      <span class="icon">🎮</span> Plăci Video (GPU)
                    </router-link>
                    <router-link to="/products/motherboards" class="submenu-item">
                      <span class="icon">🛹</span> Plăci de bază
                    </router-link>
                    <router-link to="/products/rams" class="submenu-item">
                      <span class="icon">⚡</span> Memorie RAM
                    </router-link>
                    <router-link to="/products/storages" class="submenu-item">
                      <span class="icon">💾</span> Stocare
                    </router-link>
                    <router-link to="/products/psus" class="submenu-item">
                      <span class="icon">🔌</span> Surse (PSU)
                    </router-link>
                    <router-link to="/products/cases" class="submenu-item">
                      <span class="icon">🖥️</span> Carcase
                    </router-link>
                    <router-link to="/products/coolers" class="submenu-item">
                      <span class="icon">❄️</span> Coolere
                    </router-link>
                  </div>
                </div>
              </div>
            <div class="nav-item-dropdown">
              <button class="nav-button">
                <span class="icon">📝</span> Guides <span class="arrow">▼</span>
              </button>
              
              <div class="nav-submenu">
                <router-link to="/documentatii" class="submenu-item">
                  📄 Documentații
                </router-link>
                </div>
            </div>
            <router-link to="/completed-builds" class="nav-button" active-class="active-nav">
              <span class="icon">✅</span> Completed Builds
            </router-link>
          </nav>

          <div class="search-bar">
            <input type="text" placeholder="Search components..." />
            <span class="search-icon">🔍</span>
          </div>
        </div>
      </div>
    </header>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="footer">
      <div class="container">
        <p>&copy; 2024 PC Builder Simulator - Proiect MDS</p>
      </div>
    </footer>

    <div v-if="toastMessage" :class="['custom-toast', toastType]">
      <span v-if="toastType === 'success'">✅</span>
      <span v-if="toastType === 'error'">❌</span>
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toastMessage, toastType } from './toast'

const router = useRouter()
const route = useRoute()
const dropdownOpen = ref(false)
const accountMenuRef = ref(null)

// ✅ ref reactiv în loc de computed direct pe localStorage
const accessToken = ref(localStorage.getItem('access_token'))
const usernameStored = ref(localStorage.getItem('username'))

// ✅ Se actualizează la fiecare schimbare de rută
watch(route, () => {
  accessToken.value = localStorage.getItem('access_token')
  usernameStored.value = localStorage.getItem('username')
})

const isLoggedIn = computed(() => !!accessToken.value)
const username = computed(() => usernameStored.value || 'Cont')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())

const toggleDropdown = () => {
  dropdownOpen.value = !dropdownOpen.value
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('username')
  accessToken.value = null
  usernameStored.value = null
  dropdownOpen.value = false
  router.push('/login')
}

const handleClickOutside = (e) => {
  if (accountMenuRef.value && !accountMenuRef.value.contains(e.target)) {
    dropdownOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

body {
  background-color: #0f111a;
  color: #e2e8f0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.pcpp-header { width: 100%; }

.top-tier {
  background-color: #0f111a;
  border-bottom: 1px solid #2a2d3e;
  padding: 12px 0;
}

.top-tier-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-box {
  background-color: #3b82f6;
  color: white;
  padding: 5px;
  border-radius: 4px;
  font-size: 1.2rem;
}

.logo-text {
  color: white;
  font-weight: 800;
  font-size: 1.2rem;
  letter-spacing: 1px;
}

.text-light {
  font-weight: 300;
  color: #94a3b8;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.text-link {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 0.85rem;
  cursor: pointer;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.2s;
}
.text-link:hover { color: white; }

.divider {
  width: 1px;
  height: 14px;
  background-color: #3f4455;
}

.lang-select {
  background: none;
  border: none;
  color: white;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.theme-toggle {
  background-color: #232533;
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
}

/* ── Account menu ── */
.account-menu {
  position: relative;
}

.account-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 8px;
  transition: background 0.2s;
  user-select: none;
}
.account-btn:hover { background: #232533; }

.account-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
}

.account-name {
  color: white;
  font-size: 0.85rem;
  font-weight: 500;
}

.account-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  background: #1a1b26;
  border: 1px solid #2a2d3e;
  border-radius: 10px;
  min-width: 200px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  z-index: 1000;
  overflow: hidden;
  animation: fadeDown 0.15s ease-out;
}

@keyframes fadeDown {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.dropdown-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}

.dropdown-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
}

.dropdown-name {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
}

.dropdown-role {
  color: #64748b;
  font-size: 0.75rem;
  margin-top: 2px;
}

.dropdown-divider {
  height: 1px;
  background: #2a2d3e;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 16px;
  color: #a9b1d6;
  font-size: 0.85rem;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;
  width: 100%;
  border: none;
  background: none;
  text-align: left;
}
.dropdown-item:hover { background: #232533; color: white; }

.dropdown-logout { color: #f43f5e; }
.dropdown-logout:hover { background: rgba(244,63,94,0.1); color: #f43f5e; }

/* ── Bottom nav ── */
.bottom-tier {
  background-color: #1a1b26;
  border-bottom: 1px solid #2a2d3e;
}

.bottom-tier-content {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  height: 55px;
}

.main-nav { display: flex; height: 100%; }

.nav-button {
  color: #e2e8f0;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  border-right: 1px solid #2a2d3e;
  background: transparent;
  cursor: pointer;
  text-decoration: none;
  transition: background-color 0.2s;
}
.nav-button:first-child { border-left: 1px solid #2a2d3e; }
.nav-button:hover { background-color: #232533; }

.active-nav {
  background-color: #232533;
  color: #3b82f6 !important;
  border-bottom: 3px solid #3b82f6;
}

/* ── Butonul special AI ── */
.ai-nav-button {
  color: #c084fc; 
  font-weight: 700;
  position: relative;
  overflow: hidden;
}

.ai-nav-button:hover {
  background-color: rgba(168, 85, 247, 0.1) !important;
  color: #d8b4fe;
}

.active-nav-ai {
  background-color: rgba(168, 85, 247, 0.15) !important;
  color: #c084fc !important;
  border-bottom: 3px solid #a855f7 !important;
}

.spark-icon {
  animation: pulse-spark 2s infinite;
}

@keyframes pulse-spark {
  0% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; text-shadow: 0 0 10px rgba(168, 85, 247, 0.8); }
  100% { transform: scale(1); opacity: 0.8; }
}

/* ── Dropdown Navigare (Guides) ── */
.nav-item-dropdown {
  position: relative;
  display: flex;
  height: 100%;
}

.nav-submenu {
  display: none;
  position: absolute;
  top: 100%; /* Fix sub buton */
  left: 0;
  background: #1a1b26;
  border: 1px solid #2a2d3e;
  border-top: none; /* Se lipește vizual de bara de navigație */
  min-width: 200px;
  z-index: 1000;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
  overflow: hidden;
}

/* Când pui mouse-ul pe zona butonului, apare submeniul */
.nav-item-dropdown:hover .nav-submenu {
  display: block;
  animation: fadeDown 0.15s ease-out;
}

/* Menține butonul 'Guides' luminat cât timp ești cu mouse-ul în submeniu */
.nav-item-dropdown:hover .nav-button {
  background-color: #232533;
}

.submenu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  color: #a9b1d6;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  border-bottom: 1px solid #2a2d3e;
}

.submenu-item:last-child {
  border-bottom: none;
}

.submenu-item:hover {
  background: #232533;
  color: #3b82f6; /* Se face albastru la hover, ca un link real */
}

.search-bar {
  display: flex;
  align-items: center;
  position: relative;
}

.search-bar input {
  background-color: #0f111a;
  border: 1px solid #2a2d3e;
  border-radius: 20px;
  padding: 8px 15px 8px 35px;
  color: white;
  font-size: 0.85rem;
  width: 250px;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 0.9rem;
  color: #64748b;
}

.main-content { min-height: calc(100vh - 160px); }

.footer {
  background-color: #1a1b26;
  border-top: 1px solid #2a2d3e;
  padding: 30px 0;
  text-align: center;
  color: #64748b;
  font-size: 0.85rem;
}

.custom-toast {
  position: fixed;
  bottom: 30px;
  right: 30px;
  padding: 15px 25px;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  box-shadow: 0 10px 25px rgba(0,0,0,0.4);
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: slideIn 0.3s ease-out;
}
.custom-toast.success { background-color: #1a1b26; border: 1px solid #10b981; }
.custom-toast.error   { background-color: #1a1b26; border: 1px solid #f43f5e; }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}
.products-mega-menu {
  min-width: 450px; /* Mai lat ca să încapă 2 coloane confortabil */
  padding: 10px;
}

.mega-menu-grid {
  display: grid;
  grid-template-columns: 1fr 1fr; /* Împarte meniul în 2 coloane egale */
  gap: 5px;
}

.mega-menu-grid .submenu-item {
  border-bottom: none; /* Scoatem linia de dedesubt ca să arate ca niște butoane */
  border-radius: 6px;
  padding: 10px 15px;
}

/* Culoare fundal la hover pentru fiecare item din grid */
.mega-menu-grid .submenu-item:hover {
  background: #232533;
}
</style>