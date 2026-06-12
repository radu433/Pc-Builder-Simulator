<template>
  <div class="ghid-page container" v-if="ghid">
    <router-link to="/documentatii" class="back-link">← Înapoi la documentații</router-link>
    <div class="ghid-header">
      <h1 class="title">{{ ghid.titlu }}</h1>
      <p class="meta">Scris de <strong>{{ ghid.autor }}</strong> • {{ ghid.data }}</p>
    </div>
    <div class="content" v-html="ghid.continut"></div>
  </div>
  <div v-else class="container not-found">
    <p>Ghidul nu a fost găsit.</p>
    <router-link to="/documentatii" class="back-link">Înapoi la lista de ghiduri</router-link>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { articoleFullContent } from '../data/articoleContent'

const route = useRoute()
const ghid = articoleFullContent[route.params.id]
</script>

<style scoped>
.ghid-page { 
  padding: 60px 20px; 
  max-width: 1000px; 
  color: #e2e8f0; 
  margin: 0 auto;
}

.back-link { 
  color: #a855f7; 
  text-decoration: none; 
  display: inline-block; 
  margin-bottom: 30px; 
  font-weight: 700;
  padding: 8px 16px;
  background: rgba(168, 85, 247, 0.1);
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: 8px;
  transition: 0.3s;
}
.back-link:hover { 
  background: rgba(168, 85, 247, 0.2); 
  color: white;
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.3);
  transform: translateX(-3px);
}

.ghid-header {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 24px;
  padding: 50px;
  margin-bottom: 40px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5), inset 0 0 20px rgba(0, 240, 255, 0.05);
  position: relative;
  overflow: hidden;
}
.ghid-header::before {
  content: '';
  position: absolute;
  top: -50%; right: -10%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.title { 
  font-size: 3rem; 
  margin: 0 0 20px; 
  color: white; 
  font-weight: 900;
  line-height: 1.2;
  text-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
  position: relative;
  z-index: 2;
}

.meta { 
  color: #94a3b8; 
  font-size: 1.15rem;
  margin: 0;
  position: relative;
  z-index: 2;
}
.meta strong { color: #c0caf5; }

.content { 
  line-height: 1.9; 
  font-size: 1.15rem; 
  color: #cbd5e1;
  background: rgba(0,0,0,0.3);
  padding: 50px;
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,0.05);
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

:deep(h2) { 
  color: #00f0ff; 
  margin: 50px 0 25px; 
  font-size: 2rem;
  font-weight: 800;
  border-bottom: 1px solid rgba(0, 240, 255, 0.2);
  padding-bottom: 15px;
}
:deep(h3) { 
  color: #c084fc; 
  margin: 40px 0 20px; 
  font-size: 1.5rem;
  font-weight: 800;
}
:deep(p) { margin-bottom: 25px; }
:deep(ul), :deep(ol) { margin-bottom: 25px; padding-left: 25px; }
:deep(li) { margin-bottom: 12px; }
:deep(strong) { color: white; }
:deep(img) { max-width: 100%; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); margin: 20px 0; }
:deep(blockquote) { 
  border-left: 4px solid #a855f7; 
  background: rgba(168, 85, 247, 0.05); 
  padding: 20px; 
  border-radius: 0 12px 12px 0; 
  margin: 30px 0; 
  font-style: italic; 
  color: #c0caf5;
}

.not-found {
  padding: 100px 20px;
  text-align: center;
  font-size: 1.2rem;
  color: #94a3b8;
}
.not-found p { margin-bottom: 20px; }

@media (max-width: 768px) {
  .title { font-size: 2.2rem; }
  .ghid-header { padding: 30px; }
  .content { padding: 30px; }
}
</style>