<template>
  <div class="app-wrapper">
    <header class="customrig-navbar">
      <div class="container navbar-content">
        <!-- Left: Logo -->
        <router-link to="/" class="brand-logo">
          <div class="logo-circle">C</div>
          <div class="brand-text">
            <span class="logo-title">CUSTOMRIG</span>
            <span class="tagline">Build Your Custom PC</span>
          </div>
        </router-link>

        <!-- Center: Nav Links -->
        <nav class="main-nav">
          <div class="nav-item-dropdown">
            <button class="nav-link">PC Parts <span class="arrow">▼</span></button>
            <div class="nav-submenu products-mega-menu glass-panel">
              <div class="mega-menu-grid">
                <router-link to="/products/cpus" class="submenu-item"><span class="icon">🧠</span> Procesoare</router-link>
                <router-link to="/products/gpus" class="submenu-item"><span class="icon">🎮</span> Plăci Video</router-link>
                <router-link to="/products/motherboards" class="submenu-item"><span class="icon">🛹</span> Plăci de bază</router-link>
                <router-link to="/products/rams" class="submenu-item"><span class="icon">⚡</span> Memorie RAM</router-link>
                <router-link to="/products/storages" class="submenu-item"><span class="icon">💾</span> Stocare</router-link>
                <router-link to="/products/psus" class="submenu-item"><span class="icon">🔌</span> Surse</router-link>
                <router-link to="/products/cases" class="submenu-item"><span class="icon">🖥️</span> Carcase</router-link>
                <router-link to="/products/coolers" class="submenu-item"><span class="icon">❄️</span> Coolere</router-link>
              </div>
            </div>
          </div>
          
          <router-link to="/" class="nav-link" active-class="active-nav">Builds</router-link>
          <router-link to="/completed-builds" class="nav-link" active-class="active-nav">Community</router-link>
          
          <router-link to="/chat-ai" class="nav-link" active-class="active-nav">✨ Build AI</router-link>
          <router-link to="/documentatii" class="nav-link" active-class="active-nav">📄 Documentații</router-link>
        </nav>

        <!-- Right: User Actions -->
        <div class="user-actions">
          <template v-if="!isLoggedIn">
            <router-link to="/login" class="nav-link">Log In</router-link>
            <router-link to="/register" class="btn-primary" style="padding: 6px 12px; font-size: 0.85rem;">Register</router-link>
          </template>

          <template v-else>
            <div class="account-menu" @click="toggleDropdown" ref="accountMenuRef">
              <div class="account-btn">
                <span class="account-name">Account</span>
                <span class="arrow">▼</span>
              </div>

              <div v-if="dropdownOpen" class="account-dropdown glass-panel">
                <div class="dropdown-header">
                  <div class="dropdown-avatar">{{ userInitial }}</div>
                  <div>
                    <div class="dropdown-name">{{ username }}</div>
                    <div class="dropdown-role">Utilizator</div>
                  </div>
                </div>
                <div class="dropdown-divider"></div>
                <router-link to="/profile" class="dropdown-item" @click="dropdownOpen = false">⚙️ Profile</router-link>
                <div class="dropdown-divider"></div>
                <button class="dropdown-item dropdown-logout" @click="logout">🚪 Logout</button>
              </div>
            </div>
          </template>
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

// ── Dark/Light Mode Logic ──
const isLight = ref(false)

const toggleTheme = () => {
  isLight.value = !isLight.value
  if (isLight.value) {
    document.body.classList.add('light-theme')
    localStorage.setItem('theme', 'light')
  } else {
    document.body.classList.remove('light-theme')
    localStorage.setItem('theme', 'dark')
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  
  if (localStorage.getItem('theme') === 'light') {
    isLight.value = true
    document.body.classList.add('light-theme')
  }
})
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
  background-image: none;
  color: #e2e8f0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.customrig-navbar {
  background-color: rgba(13, 15, 20, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0 20px;
}

.navbar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 70px;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.logo-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #00e5a0, #7c3aed);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 800;
  box-shadow: 0 0 15px rgba(0, 229, 160, 0.4);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  color: white;
  font-weight: 800;
  font-size: 1.2rem;
  letter-spacing: 1px;
}

.tagline {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 500;
}

.main-nav {
  display: flex;
  align-items: center;
  gap: 30px;
}

.nav-link {
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  padding: 10px 0;
  position: relative;
  transition: color 0.2s;
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.nav-link:hover, .nav-item-dropdown:hover .nav-link {
  color: white;
}

.active-nav {
  color: var(--accent-color);
  font-weight: 600;
}

.active-nav::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: var(--accent-color);
  border-radius: 2px;
}

/* Dropdown */
.nav-item-dropdown {
  position: relative;
}

.nav-submenu {
  display: none;
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  min-width: 200px;
  border-radius: var(--card-radius);
  overflow: hidden;
  margin-top: 10px;
}

.nav-item-dropdown:hover .nav-submenu {
  display: block;
  animation: fadeDown 0.2s ease-out;
}

.submenu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.2s;
}

.submenu-item:last-child {
  border-bottom: none;
}

.submenu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.products-mega-menu {
  min-width: 400px;
}

.mega-menu-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.mega-menu-grid .submenu-item {
  border: none;
}

/* Account Menu */
.account-menu {
  position: relative;
}

.account-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: var(--btn-radius);
  transition: background 0.2s;
  color: var(--text-muted);
}

.account-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.account-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 220px;
  margin-top: 10px;
  border-radius: var(--card-radius);
  overflow: hidden;
  animation: fadeDown 0.2s ease-out;
}

.dropdown-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.dropdown-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--accent-secondary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.dropdown-name {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
}

.dropdown-role {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.dropdown-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.05);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: var(--text-muted);
  text-decoration: none;
  cursor: pointer;
  width: 100%;
  border: none;
  background: none;
  text-align: left;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.dropdown-logout:hover {
  color: #ff4757;
  background: rgba(255, 71, 87, 0.1);
}

@keyframes fadeDown {
  from { opacity: 0; transform: translateY(-10px) translateX(var(--tx, 0)); }
  to   { opacity: 1; transform: translateY(0) translateX(var(--tx, 0)); }
}

.nav-submenu {
  --tx: -50%;
}
.account-dropdown {
  --tx: 0;
}

/* Toast Notifications */
.custom-toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 9999;
  animation: slideIn 0.3s ease-out, fadeOut 0.3s ease-in 2.7s forwards;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  backdrop-filter: blur(8px);
}

.custom-toast.success {
  background-color: rgba(16, 185, 129, 0.2);
  border: 1px solid #10b981;
  color: #fff;
}

.custom-toast.error {
  background-color: rgba(239, 68, 68, 0.2);
  border: 1px solid #ef4444;
  color: #fff;
}

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; visibility: hidden; }
}
</style>