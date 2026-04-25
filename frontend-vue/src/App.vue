<template>
  <header class="navbar">
    <div class="nav-content container">
      <h1>💻 PC Builder Simulator</h1>
      <nav>
        <span>Proiect MDS</span>
      </nav>
    </div>
  </header>

  <main>
    <BuilderView />
  </main>
</template>

<script setup>
// Deocamdată importăm direct pagina de Builder, fără Router, ca să vezi rapid rezultatul
import BuilderView from './components/BuilderView.vue'
</script>

<style scoped>
.navbar {
  background-color: var(--panel-bg);
  border-bottom: 1px solid var(--border-color);
}
.nav-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
}
.nav-content h1 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--accent-color);
}
</style>