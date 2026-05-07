<template>
  <div class="ghid-page container" v-if="ghid">
    <router-link to="/documentatii" class="back-link">← Înapoi la documentații</router-link>
    <h1 class="title">{{ ghid.titlu }}</h1>
    <p class="meta">Scris de {{ ghid.autor }} • {{ ghid.data }}</p>
    <div class="content" v-html="ghid.continut"></div>
  </div>
  <div v-else class="container">
    <p>Ghidul nu a fost găsit.</p>
    <router-link to="/documentatii">Înapoi</router-link>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { articoleFullContent } from '../data/articoleContent'

const route = useRoute()
const ghid = articoleFullContent[route.params.id]
</script>

<style scoped>
.ghid-page { padding: 50px 20px; max-width: 900px; color: #e2e8f0; }
.back-link { color: #3b82f6; text-decoration: none; display: block; margin-bottom: 20px; }
.title { font-size: 2.5rem; margin-bottom: 10px; color: white; }
.meta { color: #64748b; margin-bottom: 40px; border-bottom: 1px solid #2a2d3e; padding-bottom: 20px; }
.content { line-height: 1.8; font-size: 1.1rem; }
:deep(h2) { color: #3b82f6; margin: 30px 0 15px; }
:deep(h3) { color: white; margin: 20px 0 10px; }
</style>