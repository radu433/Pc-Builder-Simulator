<template>
  <div class="docs-container container">
    <div class="hero-section">
      <div class="hero-content">
        <span class="badge featured-badge">⭐️ Recomandat</span>
        <h1 class="hero-title">Ghidul Suprem de Asamblare PC (2026)</h1>
        <p class="hero-desc">Învață pas cu pas cum să îți construiești propriul calculator de la zero. Alegerea pieselor, montajul și instalarea sistemului de operare.</p>
        <router-link to="/ghid/asamblare" class="btn-primary">Începe Tutorialul</router-link>
      </div>
    </div>

    <div class="filters-container">
      <button 
        v-for="filter in filters" 
        :key="filter"
        :class="['filter-btn', { active: activeFilter === filter }]"
        @click="activeFilter = filter"
      >
        {{ filter }}
      </button>
    </div>

    <div class="articles-grid">
      <div 
        v-for="item in filteredArticles" 
        :key="item.id" 
        class="article-card"
      >
        <div class="card-header">
          <span :class="['category-badge', getCategoryClass(item.tip)]">{{ item.tip }}</span>
          <span v-if="item.dificultate" class="diff-badge">
            {{ getDiffIcon(item.dificultate) }} {{ item.dificultate }}
          </span>
        </div>
        
        <h3 class="card-title">{{ item.titlu }}</h3>
        
        <div class="card-footer">
          <div v-if="item.timp" class="meta-info">
            <span class="icon">⏱️</span> {{ item.timp }}
          </div>
          <div v-if="item.sursa" class="meta-info">
            <span class="icon">📰</span> {{ item.sursa }} &bull; {{ item.data }}
          </div>

          <router-link v-if="!item.esteStire" :to="'/ghid/' + item.id" class="read-btn">
            Citește
          </router-link>
          <a v-else :href="item.link" target="_blank" class="read-btn external">
            Sursa ↗
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// 1. Filtrele
const filters = ['Toate', 'Tutoriale', 'Ghiduri Achiziție', 'Știri']
const activeFilter = ref('Toate')

// 2. GHIDURILE TALE (Hardcodate)
// Pe acestea le iei din fișierul tău local sau le definești aici, ele nu se schimbă.
const ghiduri = ref([
  { id: 1, tip: 'Tutoriale', titlu: 'Cum alegi sursa (PSU) corectă?', dificultate: 'Începător', timp: '5 min', esteStire: false },
  { id: 2, tip: 'Tutoriale', titlu: 'Diferența dintre RAM DDR4 și DDR5', dificultate: 'Intermediar', timp: '8 min', esteStire: false },
  { id: 4, tip: 'Ghiduri Achiziție', titlu: 'Cele mai bune carcase sub 400 RON', dificultate: 'Începător', timp: '10 min', esteStire: false },
])

// 3. ȘTIRILE (Dinamice - goale la început)
const stiriDinApi = ref([])

// 4. Funcția care trage știrile live când se deschide pagina
onMounted(async () => {
  try {
    const apiKey = import.meta.env.VITE_NEWS_API_KEY;
    const response = await fetch(`https://newsapi.org/v2/everything?q=pc+hardware&language=en&sortBy=publishedAt&apiKey=${apiKey}`)
    
    const data = await response.json()

    if (data.articles) {
      stiriDinApi.value = data.articles.slice(0, 4).map((articol, index) => ({
        id: 'stire-' + index,
        tip: 'Știri',
        titlu: articol.title,
        sursa: articol.source.name,
        data: new Date(articol.publishedAt).toLocaleDateString('ro-RO'),
        esteStire: true,
        link: articol.url 
      }))
    } else {
      console.warn('Eroare de la API-ul de știri:', data.message)
    }
  } catch (error) {
    console.error('Nu am putut aduce știrile:', error)
  }
})

// 5. COMBINĂM GHIDURILE + ȘTIRILE
// Asta este lista finală care merge în HTML-ul paginii
const toateArticolele = computed(() => {
  return [...ghiduri.value, ...stiriDinApi.value]
})

// 6. Logica de filtrare
const filteredArticles = computed(() => {
  if (activeFilter.value === 'Toate') {
    return toateArticolele.value
  }
  return toateArticolele.value.filter(articol => articol.tip === activeFilter.value)
})

// Funcții ajutătoare pentru culori (rămân la fel)
const getCategoryClass = (tip) => {
  if (tip === 'Tutoriale') return 'bg-blue'
  if (tip === 'Știri') return 'bg-purple'
  return 'bg-green'
}

const getDiffIcon = (diff) => {
  if (diff === 'Începător') return '🟢'
  if (diff === 'Intermediar') return '🟡'
  return '🔴' 
}
</script>

<style scoped>
.docs-container {
  padding: 40px 15px;
  color: #e2e8f0;
}

/* --- HERO SECTION --- */
.hero-section {
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 24px;
  padding: 60px 50px;
  margin-bottom: 50px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5), inset 0 0 20px rgba(0, 240, 255, 0.05);
}

.hero-section::before {
  content: '';
  position: absolute;
  top: -50%; right: -10%;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.15) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-section::after {
  content: '';
  position: absolute;
  bottom: -20%; left: -5%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.15) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-content {
  position: relative;
  z-index: 2;
}

.featured-badge {
  background-color: rgba(0, 240, 255, 0.1);
  color: #00f0ff;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 800;
  border: 1px solid rgba(0, 240, 255, 0.3);
  display: inline-block;
  margin-bottom: 25px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.hero-title {
  font-size: 2.8rem;
  color: white;
  margin-bottom: 20px;
  font-weight: 900;
  line-height: 1.2;
  text-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
}

.hero-desc {
  color: #c0caf5;
  font-size: 1.15rem;
  max-width: 650px;
  line-height: 1.7;
  margin-bottom: 35px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(90deg, #10b981, #00f0ff);
  color: white;
  padding: 14px 30px;
  border-radius: 12px;
  text-decoration: none;
  font-weight: 800;
  font-size: 1.1rem;
  transition: 0.3s;
  border: none;
  box-shadow: 0 5px 20px rgba(16, 185, 129, 0.3);
}
.btn-primary:hover { 
  transform: translateY(-3px); 
  box-shadow: 0 10px 30px rgba(0, 240, 255, 0.4); 
}

/* --- FILTRE --- */
.filters-container {
  display: flex;
  gap: 15px;
  margin-bottom: 40px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.filters-container::-webkit-scrollbar { height: 6px; }
.filters-container::-webkit-scrollbar-thumb { background: rgba(0, 240, 255, 0.3); border-radius: 3px; }

.filter-btn {
  background-color: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.05);
  color: #94a3b8;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: 0.3s;
  white-space: nowrap;
}

.filter-btn:hover {
  background-color: rgba(0, 240, 255, 0.05);
  border-color: rgba(0, 240, 255, 0.3);
  color: #00f0ff;
}

.filter-btn.active {
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.8), rgba(0, 240, 255, 0.8));
  color: white;
  border-color: transparent;
  box-shadow: 0 5px 15px rgba(168, 85, 247, 0.3);
}

/* --- GRID ARTICOLE --- */
.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 30px;
}

.article-card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  transition: 0.3s;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.article-card:hover {
  transform: translateY(-8px);
  border-color: rgba(168, 85, 247, 0.5);
  box-shadow: 0 15px 40px rgba(168, 85, 247, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.category-badge {
  font-size: 0.75rem;
  font-weight: 800;
  padding: 6px 12px;
  border-radius: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.bg-blue { background: rgba(0, 240, 255, 0.1); color: #00f0ff; border: 1px solid rgba(0, 240, 255, 0.3); }
.bg-green { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.bg-purple { background: rgba(168, 85, 247, 0.1); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }

.diff-badge {
  font-size: 0.8rem;
  color: #cbd5e1;
  background: rgba(0,0,0,0.4);
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.05);
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-title {
  color: white;
  font-size: 1.25rem;
  font-weight: 800;
  line-height: 1.5;
  margin-bottom: 25px;
  flex-grow: 1;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 20px;
  margin-top: auto;
}

.meta-info {
  font-size: 0.85rem;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.read-btn {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  padding: 8px 16px;
  border-radius: 8px;
  color: #00f0ff;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  transition: 0.3s;
}

.read-btn:hover {
  background: rgba(0, 240, 255, 0.2);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
  color: white;
}

.read-btn.external {
  background: rgba(168, 85, 247, 0.1);
  border-color: rgba(168, 85, 247, 0.3);
  color: #c084fc;
}
.read-btn.external:hover {
  background: rgba(168, 85, 247, 0.2);
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.3);
  color: white;
}

@media (max-width: 768px) {
  .hero-section { padding: 40px 30px; }
  .hero-title { font-size: 2.2rem; }
}
</style>
