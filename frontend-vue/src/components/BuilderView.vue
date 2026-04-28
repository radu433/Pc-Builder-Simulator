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
        <div 
          v-for="category in categories" 
          :key="category.id" 
          class="build-row"
          :class="{ 'has-part': category.selectedPart }"
        >
          <div class="category-icon">{{ category.icon }}</div>
          <div class="category-info">
            <div class="category-name">{{ category.name }}</div>
            <div v-if="category.selectedPart" class="selected-name">
              {{ category.selectedPart.name }}
            </div>
            <div v-else class="empty-state">Nicio componentă selectată</div>
          </div>
          
          <div class="price-section">
            <span v-if="category.selectedPart">{{ category.selectedPart.price }} RON</span>
          </div>
          
          <div class="actions">
            <button v-if="!category.selectedPart" class="btn btn-outline" @click="openPartSelector(category.id)">
              + Alege
            </button>
            <button v-else class="btn-remove" @click="removePart(category.id)">
              🗑️
            </button>
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
          <strong class="total-price">{{ totalPrice }} RON</strong>
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
import { ref, computed } from 'vue'

// Am adăugat iconițe pentru fiecare categorie
const categories = ref([
  { id: 'cpu', name: 'Procesor', icon: '🧠', selectedPart: null },
  { id: 'cooler', name: 'Cooler', icon: '❄️', selectedPart: null },
  { id: 'motherboard', name: 'Placă de bază', icon: '🛹', selectedPart: null },
  { id: 'ram', name: 'Memorie RAM', icon: '📟', selectedPart: null },
  { id: 'storage', name: 'Stocare', icon: '💾', selectedPart: null },
  { id: 'gpu', name: 'Placă Video', icon: '🎮', selectedPart: null },
  { id: 'case', name: 'Carcasă', icon: '🗄️', selectedPart: null },
  { id: 'psu', name: 'Sursă', icon: '🔌', selectedPart: null }
])

// --- LOGICA PENTRU BARĂ DE PROGRES ---
const selectedPartsCount = computed(() => {
  return categories.value.filter(cat => cat.selectedPart !== null).length
})

const progressPercentage = computed(() => {
  return (selectedPartsCount.value / categories.value.length) * 100
})

// --- FUNCȚII SIMULATE ---
const openPartSelector = (categoryId) => {
  // Simulăm adăugarea unei piese direct ca să vezi efectele vizuale
  const catIndex = categories.value.findIndex(c => c.id === categoryId)
  if(catIndex !== -1) {
    categories.value[catIndex].selectedPart = { 
      name: `Componentă PRO ${categoryId.toUpperCase()}`, 
      price: Math.floor(Math.random() * 1000) + 300, 
      wattage: Math.floor(Math.random() * 100) + 50 
    }
  }
}

const removePart = (categoryId) => {
  const catIndex = categories.value.findIndex(c => c.id === categoryId)
  if(catIndex !== -1) {
    categories.value[catIndex].selectedPart = null
  }
}

const totalPrice = computed(() => {
  return categories.value.reduce((sum, cat) => sum + (cat.selectedPart ? cat.selectedPart.price : 0), 0)
})

const totalWattage = computed(() => {
  return categories.value.reduce((sum, cat) => sum + (cat.selectedPart ? cat.selectedPart.wattage : 0), 0)
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