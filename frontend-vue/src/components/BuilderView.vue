<template>
  <div class="container builder-layout">
    
    <div class="main-panel">
      <div class="header-section">
        <h2>🛠️ Configurează-ți PC-ul</h2>
        
        <div class="progress-container">
          <div class="progress-info">
            <span>Progres Build</span>
            <span>{{ selectedPartsCount }} / {{ categories.length }} piese</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" :style="{ width: progressPercentage + '%' }"></div>
          </div>
        </div>
      </div>
      
      <div class="build-list">
        <div v-if="loading" class="loading">Se încarcă componentele...</div>
        <div v-else-if="totalPartsLoaded === 0" class="empty-state">
          Nu s-a încărcat nicio componentă de la API. Verifică backend-ul și consola browserului.
        </div>
        <div 
          v-else
          v-for="category in categories" 
          :key="category.id" 
          class="build-row"
          :class="{ 'has-part': category.selectedPart }"
        >
          <div class="category-icon">{{ category.icon }}</div>
          <div class="category-info">
            <div class="category-name">{{ category.name }}</div>
            <div v-if="category.selectedPart" class="selected-name">
              {{ displayPartName(category.selectedPart) }}
            </div>
            <div v-else class="empty-state">Nicio componentă selectată</div>
          </div>
          
          <div class="price-section">
            <span v-if="category.selectedPart">{{ formatCurrency(displayPartPrice(category.selectedPart)) }} RON</span>
          </div>
          
          <div class="actions">
            <button class="btn btn-outline" @click="openPartSelector(category.id)">
              {{ openCategoryId === category.id ? 'Închide' : '+ Alege' }} ({{ category.parts.length }} disponibile)
            </button>
            <button v-if="category.selectedPart" class="btn-remove" @click="removePart(category.id)">
              🗑️
            </button>
          </div>

          <div v-if="openCategoryId === category.id" class="parts-list">
            <div v-if="category.parts.length === 0" class="empty-state">
              Nu s-au găsit componente în această categorie.
            </div>
            <div v-for="part in category.parts" :key="part.id" class="part-row" @click="selectPart(category.id, part)">
              <div class="part-name">{{ displayPartName(part) }}</div>
              <div class="part-price">{{ displayPartPrice(part) }} RON</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="summary-panel">
      <h3>Sumar Build</h3>
      <div class="summary-card">
        <div class="summary-row">
          <span>⚡ Consum Estimat</span>
          <strong>{{ totalWattage }} W</strong>
        </div>
        <hr class="divider" />
        <div class="summary-row total">
          <span>💰 Total</span>
          <strong class="total-price">{{ formatCurrency(totalPrice) }} RON</strong>
        </div>
      </div>
      
      <button 
        class="btn checkout-btn" 
        :disabled="selectedPartsCount === 0"
        :class="{ 'btn-disabled': selectedPartsCount === 0 }"
      >
        🚀 Salvează Configurația
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// API base URL
const API_BASE = 'http://127.0.0.1:8000/api/'

// Loading state
const loading = ref(true)

// Am adăugat iconițe pentru fiecare categorie
const categories = ref([
  { id: 'cpus', name: 'Procesor', icon: '🧠', selectedPart: null, parts: [] },
  { id: 'coolers', name: 'Cooler', icon: '❄️', selectedPart: null, parts: [] },
  { id: 'motherboards', name: 'Placă de bază', icon: '🛹', selectedPart: null, parts: [] },
  { id: 'rams', name: 'Memorie RAM', icon: '📟', selectedPart: null, parts: [] },
  { id: 'storages', name: 'Stocare', icon: '💾', selectedPart: null, parts: [] },
  { id: 'gpus', name: 'Placă Video', icon: '🎮', selectedPart: null, parts: [] },
  { id: 'cases', name: 'Carcasă', icon: '🗄️', selectedPart: null, parts: [] },
  { id: 'psus', name: 'Sursă', icon: '🔌', selectedPart: null, parts: [] }
])

// Load parts from API
const loadParts = async () => {
  loading.value = true
  for (const category of categories.value) {
    try {
      const response = await axios.get(`${API_BASE}${category.id}/`)
      category.parts = response.data
      console.log(`Loaded ${category.id}:`, category.parts.length)
    } catch (error) {
      console.error(`Error loading ${category.id}:`, error)
      category.parts = []
    }
  }
  loading.value = false
}

// --- LOGICA PENTRU BARĂ DE PROGRES ---
const selectedPartsCount = computed(() => {
  return categories.value.filter(cat => cat.selectedPart !== null).length
})

const progressPercentage = computed(() => {
  return (selectedPartsCount.value / categories.value.length) * 100
})

// --- FUNCȚII ---
const openCategoryId = ref(null)

const openPartSelector = (categoryId) => {
  if (openCategoryId.value === categoryId) {
    openCategoryId.value = null
    return
  }
  openCategoryId.value = categoryId
}

const selectPart = (categoryId, part) => {
  const cat = categories.value.find(c => c.id === categoryId)
  if (cat) {
    cat.selectedPart = part
    openCategoryId.value = null
  }
}

const removePart = (categoryId) => {
  const cat = categories.value.find(c => c.id === categoryId)
  if (cat) {
    cat.selectedPart = null
  }
}

const displayPartName = (part) => {
  if (!part) return ''
  return part.nume || part.name || part.model || 'Componentă'
}

const displayPartPrice = (part) => {
  if (!part) return 0
  const rawPrice = part.pret ?? part.price ?? 0
  const parsed = Number(rawPrice)
  return Number.isFinite(parsed) ? parsed : 0
}

const displayPartWattage = (part) => {
  if (!part) return 0
  const rawWattage = part.consum_tdp ?? part.wattage ?? 0
  const parsed = Number(rawWattage)
  return Number.isFinite(parsed) ? parsed : 0
}

const totalPrice = computed(() => {
  return categories.value.reduce((sum, cat) => sum + displayPartPrice(cat.selectedPart), 0)
})

const totalWattage = computed(() => {
  return categories.value.reduce((sum, cat) => sum + displayPartWattage(cat.selectedPart), 0)
})

const formatCurrency = (value) => {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(2) : '0.00'
}

const totalPartsLoaded = computed(() => {
  return categories.value.reduce((sum, cat) => sum + (cat.parts?.length || 0), 0)
})

// Load data on mount
onMounted(() => {
  loadParts()
})
</script>

<style scoped>
.builder-layout {
  display: grid;
  grid-template-columns: 3fr 1fr;
  gap: 30px;
  margin-top: 20px;
}

.main-panel, .summary-panel {
  background-color: var(--panel-bg);
  padding: 30px;
  border-radius: 12px;
  border: 1px solid var(--panel-border);
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.header-section { margin-bottom: 30px; }
.header-section h2 { margin-top: 0; color: white; }

/* BARA DE PROGRES */
.progress-info { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem; color: var(--text-muted); }
.progress-bar-bg { width: 100%; height: 8px; background-color: var(--panel-border); border-radius: 4px; overflow: hidden; }
.progress-bar-fill { height: 100%; background-color: var(--accent-color); transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 0 10px var(--accent-color); }

/* RÂNDURILE DE PIESE */
.build-list { display: flex; flex-direction: column; gap: 12px; }
.build-row {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  background-color: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  transition: all 0.2s;
}

.build-row:hover { background-color: rgba(255, 255, 255, 0.05); border-color: #3f4455; transform: translateX(5px); }
.build-row.has-part { border-left: 4px solid var(--accent-color); }

.parts-list {
  margin-top: 12px;
  padding: 14px 18px;
  background-color: rgba(255,255,255,0.04);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.08);
}
.part-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}
.part-row:hover {
  background-color: rgba(255,255,255,0.08);
  transform: translateX(4px);
}
.part-name { color: white; }
.part-price { color: var(--accent-color); font-weight: 600; }

.category-icon { font-size: 1.5rem; margin-right: 20px; width: 30px; text-align: center; }
.category-info { flex-grow: 1; }
.category-name { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 4px; }
.selected-name { font-weight: 600; color: white; font-size: 1.1rem; }
.empty-state { color: var(--text-muted); font-style: italic; font-size: 0.95rem; }

.price-section { width: 120px; text-align: right; font-weight: bold; margin-right: 20px; color: var(--text-main); }
.actions { width: 100px; text-align: right; }

.btn-remove { background: none; border: none; font-size: 1.2rem; cursor: pointer; opacity: 0.7; transition: 0.2s; }
.btn-remove:hover { opacity: 1; transform: scale(1.2); }

/* SUMAR */
.summary-panel { position: sticky; top: 20px; height: fit-content; }
.summary-card { background-color: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px; margin-bottom: 20px; }
.summary-row { display: flex; justify-content: space-between; margin-bottom: 15px; }
.divider { border: 0; height: 1px; background: var(--panel-border); margin: 15px 0; }
.total { font-size: 1.2rem; align-items: center; }
.total-price { font-size: 1.8rem; color: var(--accent-color); text-shadow: 0 0 10px var(--accent-glow); }
.checkout-btn { width: 100%; padding: 15px; font-size: 1.1rem; }
.btn-disabled { background-color: var(--panel-border); color: var(--text-muted); box-shadow: none; cursor: not-allowed; }
.btn-disabled:hover { transform: none; box-shadow: none; filter: none; }

@media (max-width: 900px) {
  .builder-layout { grid-template-columns: 1fr; }
  .summary-panel { position: relative; top: 0; }
}
</style>