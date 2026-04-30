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
            <router-link to="/login" class="text-link">Log In</router-link>
            
            <span class="divider"></span>
            
            <router-link to="/register" class="text-link">Register</router-link>
            
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
            <router-link to="/" class="nav-button" active-class="active-nav">
              <span class="icon">🔧</span> Builder
            </router-link>

            <button class="nav-button">
              <span class="icon">🪪</span> Products <span class="arrow">▼</span>
            </button>

            <button class="nav-button">
              <span class="icon">📝</span> Guides <span class="arrow">▼</span>
            </button>

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
  </div>
</template>

<script setup>
// Nu avem nevoie de logica suplimentară aici, router-ul gestionează totul
</script>

<style>
/* Reset și stiluri globale */
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

/* Header Styles */
.pcpp-header {
  width: 100%;
}

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

/* Link-urile din header (Login/Register) */
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

.text-link:hover {
  color: white;
}

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

/* Bottom Tier / Navigation */
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

.main-nav {
  display: flex;
  height: 100%;
}

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

.nav-button:first-child {
  border-left: 1px solid #2a2d3e;
}

.nav-button:hover {
  background-color: #232533;
}

.active-nav {
  background-color: #232533;
  color: #3b82f6 !important;
  border-bottom: 3px solid #3b82f6;
}

/* Search bar */
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

/* Content Area */
.main-content {
  min-height: calc(100vh - 160px);
}

/* Footer */
.footer {
  background-color: #1a1b26;
  border-top: 1px solid #2a2d3e;
  padding: 30px 0;
  text-align: center;
  color: #64748b;
  font-size: 0.85rem;
}
</style>