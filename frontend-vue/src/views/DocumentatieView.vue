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
}

/* --- HERO SECTION --- */
.hero-section {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border: 1px solid #2a2d3e;
  border-radius: 16px;
  padding: 50px 40px;
  margin-bottom: 40px;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: -50%; right: -10%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
  border-radius: 50%;
}

.featured-badge {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid rgba(245, 158, 11, 0.2);
  display: inline-block;
  margin-bottom: 20px;
}

.hero-title {
  font-size: 2.2rem;
  color: white;
  margin-bottom: 15px;
  font-weight: 800;
}

.hero-desc {
  color: #94a3b8;
  font-size: 1.1rem;
  max-width: 600px;
  line-height: 1.6;
  margin-bottom: 25px;
}

.btn-primary {
  display: inline-block;
  background-color: #3b82f6;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  transition: background 0.2s;
}
.btn-primary:hover { background-color: #2563eb; }

/* --- FILTRE --- */
.filters-container {
  display: flex;
  gap: 15px;
  margin-bottom: 30px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.filter-btn {
  background-color: #1a1b26;
  border: 1px solid #2a2d3e;
  color: #94a3b8;
  padding: 10px 20px;
  border-radius: 30px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.filter-btn:hover {
  background-color: #232533;
  color: white;
}

.filter-btn.active {
  background-color: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* --- GRID ARTICOLE --- */
.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 25px;
}

.article-card {
  background-color: #1a1b26;
  border: 1px solid #2a2d3e;
  border-radius: 12px;
  padding: 25px;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, border-color 0.2s;
}

.article-card:hover {
  transform: translateY(-5px);
  border-color: #3f4455;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.category-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.bg-blue { background: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.2); }
.bg-green { background: rgba(16,185,129,0.1); color: #34d399; border: 1px solid rgba(16,185,129,0.2); }
.bg-purple { background: rgba(168,85,247,0.1); color: #c084fc; border: 1px solid rgba(168,85,247,0.2); }

.diff-badge {
  font-size: 0.8rem;
  color: #94a3b8;
  background: #0f111a;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #2a2d3e;
}

.card-title {
  color: white;
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 20px;
  flex-grow: 1;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #2a2d3e;
  padding-top: 15px;
  margin-top: auto;
}

.meta-info {
  font-size: 0.85rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 5px;
}

.read-btn {
  background: none;
  border: none;
  color: #3b82f6;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.read-btn:hover {
  color: #60a5fa;
  text-decoration: underline;
}

.read-btn.external {
  color: #a855f7;
}
.read-btn.external:hover {
  color: #c084fc;
}
</style>