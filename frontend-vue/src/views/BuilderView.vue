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
          Nu s-a încărcat nicio componentă de la API. Verifică dacă serverul Django rulează.
        </div>

        <div 
          v-else
          v-for="category in categories" 
          :key="category.id" 
          class="category-container"
        >
          <div class="build-row" :class="{ 'has-part': category.selectedPart }">
            <div class="category-icon">{{ category.icon }}</div>
            
            <div class="category-info">
              <div class="category-name">{{ category.name }}</div>
              <div v-if="category.selectedPart" class="selected-name">
                {{ displayPartName(category.selectedPart) }}
              </div>
              <div v-else class="empty-state">Nicio componentă selectată</div>
            </div>

            <div class="price-section">
              <span v-if="category.selectedPart">{{ displayPartPrice(category.selectedPart) }} RON</span>
            </div>

            <div class="actions">
              <button v-if="!category.selectedPart" class="btn btn-outline" @click="openPartSelector(category.id)">
                {{ openCategoryId === category.id ? 'Închide' : '+ Alege' }}
              </button>
              <button v-else class="btn-remove" @click="removePart(category.id)">
                ✕
              </button>
            </div>
          </div>

          <div v-if="openCategoryId === category.id" class="parts-selector-box">
            <div v-if="category.parts.length === 0" class="mini-loading">Nu există piese disponibile în această categorie.</div>
            <div 
              v-else
              v-for="part in category.parts" 
              :key="part.id" 
              class="part-option"
              @click="selectPart(category.id, part)"
            >
              <div class="part-main-info">
                <span class="p-name">{{ displayPartName(part) }}</span>
                <span class="p-specs" v-if="part.frecventa || part.capacitate">{{ part.frecventa }} {{ part.capacitate }}</span>
              </div>
              <span class="p-price">{{ displayPartPrice(part) }} RON</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="summary-panel">
      <div class="summary-card">
        <h3>Sumar Build</h3>
        <div class="divider"></div>
        
        <div class="summary-row">
          <span>Componente:</span>
          <span>{{ selectedPartsCount }} / {{ categories.length }}</span>
        </div>
        
        <div class="summary-row total">
          <span>Total Estimativ:</span>
          <strong class="price-highlight">{{ totalPrice.toFixed(2) }} RON</strong>
        </div>

        <button 
          class="btn btn-primary btn-block" 
          :disabled="selectedPartsCount === 0"
          @click="salveazaPC"
        >
          🚀 Salvează Configurația
        </button>
      </div>

      <div class="info-box">
  <h4>🤖 Analiză AI</h4>

  <div v-if="selectedPartsCount === 0">
    <p>Începe prin a alege un <strong>Procesor</strong>. Acesta este inima sistemului tău.</p>
  </div>

  <div v-else>
    <button class="btn btn-analyze" :disabled="agentLoading" @click="analizeazaBuild">
      {{ agentLoading ? '⏳ Se analizează...' : '🔍 Analizează Build-ul' }}
    </button>

    <div v-if="agentError" class="agent-error">⚠️ {{ agentError }}</div>

    <div v-if="agentResult" class="agent-result">
      <div class="agent-badge" :class="'badge-' + agentResult.severitate">
        {{ agentResult.severitate === 'ok' ? '✅ Compatibil' : agentResult.severitate === 'warning' ? '⚠️ Atenție' : '❌ Probleme' }}
      </div>

      <div v-if="agentResult.probleme?.length > 0" class="agent-section">
        <strong>Probleme:</strong>
        <ul><li v-for="p in agentResult.probleme" :key="p">{{ p }}</li></ul>
      </div>

      <div v-if="agentResult.bottleneck?.are_bottleneck" class="agent-section">
        <strong>Bottleneck:</strong>
        <p>{{ agentResult.bottleneck.componenta_limitatoare }} limitează {{ agentResult.bottleneck.componenta_limitata }} cu {{ agentResult.bottleneck.procentaj_bottleneck }}%</p>
      </div>

      <div v-if="agentResult.analiza_ai" class="agent-section">
        <strong>Feedback AI:</strong>
        <p>{{ agentResult.analiza_ai }}</p>
      </div>

      <div v-if="Object.keys(agentResult.sugestii || {}).length > 0" class="agent-section">
        <strong>Sugestii:</strong>
        <div v-for="(lista, tip) in agentResult.sugestii" :key="tip">
          <em>{{ tip.toUpperCase() }}:</em>
          <div v-for="s in lista" :key="s.id" class="sugestie-item">{{ s.nume || s.model }} — {{ s.pret }} RON</div>
        </div>
      </div>
    </div>
  </div>
</div>
    </div>
  </div>
</template>

<script setup>

import { ref, computed, onMounted } from 'vue'
import axios from 'axios' // Importat pentru citire (fără token)
import api from '../plugins/axios.js' // Importat pentru salvare (cu token)

const agentLoading = ref(false)
const agentResult = ref(null)
const agentError = ref(null)

const loading = ref(true)
const openCategoryId = ref(null)

// ID-urile trebuie să fie la plural pentru a se potrivi cu rutele tale Django (/api/cpus/)
const categories = ref([
  { id: 'cpus', name: 'Procesor', icon: '🧠', parts: [], selectedPart: null },
  { id: 'motherboards', name: 'Placă de Bază', icon: '🛹', parts: [], selectedPart: null },
  { id: 'gpus', name: 'Placă Video', icon: '🎮', parts: [], selectedPart: null },
  { id: 'rams', name: 'Memorie RAM', icon: '⚡', parts: [], selectedPart: null },
  { id: 'storages', name: 'Stocare', icon: '💾', parts: [], selectedPart: null },
  { id: 'psus', name: 'Sursă', icon: '🔌', parts: [], selectedPart: null },
  { id: 'cases', name: 'Carcasă', icon: '📦', parts: [], selectedPart: null },
  { id: 'coolers', name: 'Cooler CPU', icon: '❄️', parts: [], selectedPart: null },
])

// FUNCȚIA DE ÎNCĂRCARE REPARATĂ
const fetchParts = async () => {
  loading.value = true
  try {
    for (const category of categories.value) {
      // Folosim axios simplu pentru a evita eroarea 401
      const response = await axios.get(`http://127.0.0.1:8000/api/${category.id}/`)
      
      // Verificăm dacă datele sunt în .results (paginare) sau direct array
      category.parts = response.data.results || response.data
      console.log(`✅ Încărcat ${category.id}: ${category.parts.length} piese`);
    }
  } catch (err) {
    console.error("Eroare la citirea bazei de date:", err)
  } finally {
    loading.value = false
  }
}

const openPartSelector = (categoryId) => {
  openCategoryId.value = openCategoryId.value === categoryId ? null : categoryId
}

const selectPart = (categoryId, part) => {
  const category = categories.value.find(c => c.id === categoryId)
  if (category) {
    category.selectedPart = part
    openCategoryId.value = null
  }
}

const removePart = (categoryId) => {
  const category = categories.value.find(c => c.id === categoryId)
  if (category) category.selectedPart = null
}

const salveazaPC = async () => {
  try {
    const payload = {
      cpu: categories.value.find(c => c.id === 'cpus')?.selectedPart?.id || null,
      gpu: categories.value.find(c => c.id === 'gpus')?.selectedPart?.id || null,
      motherboard: categories.value.find(c => c.id === 'motherboards')?.selectedPart?.id || null,
      ram: categories.value.find(c => c.id === 'rams')?.selectedPart?.id || null,
      storage: categories.value.find(c => c.id === 'storages')?.selectedPart?.id || null,
      psu: categories.value.find(c => c.id === 'psus')?.selectedPart?.id || null,
      case: categories.value.find(c => c.id === 'cases')?.selectedPart?.id || null,
      cooler: categories.value.find(c => c.id === 'coolers')?.selectedPart?.id || null,
      pret_total: totalPrice.value
    };

    const response = await api.post('saved-builds/', payload);
    alert(`Build salvat cu succes sub numele: ${response.data.nume}`);
  } catch (error) {
    console.error("Eroare la salvare:", error);
    alert(error.response?.status === 401 ? "Loghează-te pentru a salva!" : "Eroare server.");
  }
}


const analizeazaBuild = async () => {
  agentLoading.value = true
  agentError.value = null
  agentResult.value = null
  try {
    const payload = {
      cpu:         categories.value.find(c => c.id === 'cpus')?.selectedPart || null,
      gpu:         categories.value.find(c => c.id === 'gpus')?.selectedPart || null,
      motherboard: categories.value.find(c => c.id === 'motherboards')?.selectedPart || null,
      ram:         categories.value.find(c => c.id === 'rams')?.selectedPart || null,
      psu:         categories.value.find(c => c.id === 'psus')?.selectedPart || null,
      case:        categories.value.find(c => c.id === 'cases')?.selectedPart || null,
      cooler:      categories.value.find(c => c.id === 'coolers')?.selectedPart || null,
      storage:     categories.value.find(c => c.id === 'storages')?.selectedPart || null,
    }
    const response = await axios.post('http://127.0.0.1:8002/analizeaza-build', payload)
    agentResult.value = response.data
  } catch (err) {
    agentError.value = 'Nu s-a putut contacta agentul. Verifică dacă rulează pe portul 8002.'
  } finally {
    agentLoading.value = false
  }
}
// Helpers
const selectedPartsCount = computed(() => categories.value.filter(cat => cat.selectedPart).length)
const totalPartsLoaded = computed(() => categories.value.reduce((acc, cat) => acc + (cat.parts?.length || 0), 0))
const totalPrice = computed(() => categories.value.reduce((sum, cat) => sum + parseFloat(cat.selectedPart?.pret || 0), 0))
const progressPercentage = computed(() => (selectedPartsCount.value / categories.value.length) * 100)
const displayPartName = (part) => part.nume || part.model || 'Componentă'
const displayPartPrice = (part) => part.pret || '0.00'

onMounted(fetchParts)

</script>

<style scoped>
/* Layout principal */
.builder-layout { 
  display: grid; 
  grid-template-columns: 1fr 350px; 
  gap: 30px; 
  padding: 40px 20px; 
  color: white; 
}

.main-panel { 
  background-color: #1a1b26; 
  border-radius: 12px; 
  border: 1px solid #2a2d3e; 
  padding: 25px; 
}

/* Rândul de categorie */
.build-row { 
  display: flex; 
  align-items: center; 
  padding: 20px; 
  border-bottom: 1px solid #2a2d3e; 
  transition: 0.3s;
}

.category-container { 
  border-bottom: 1px solid #232533; 
}

/* --- ALINIEREA BUTOANELOR LA CAPĂT --- */
.category-info { 
  flex: 1; /* Ocupă tot spațiul disponibil, împingând restul elementelor la dreapta */
  display: flex; 
  flex-direction: column; 
  margin-left: 15px;
}

.price-section { 
  margin-left: auto; /* Magnet pentru aliniere la dreapta */
  margin-right: 25px; 
  min-width: 120px; 
  text-align: right; 
  font-weight: bold;
}

.actions { 
  width: 120px; 
  display: flex; 
  justify-content: flex-end; 
}
/* -------------------------------------- */

/* Stil pentru listele de piese (Dropdown) */
.parts-selector-box {
  background-color: #16161e;
  max-height: 350px;
  overflow-y: auto;
  border-left: 3px solid #3b82f6;
  margin: 0 10px 15px 10px;
  border-radius: 0 0 8px 8px;
  box-shadow: inset 0 4px 10px rgba(0,0,0,0.3);
}

.part-option {
  display: flex; 
  justify-content: space-between; 
  align-items: center;
  padding: 15px 25px; 
  cursor: pointer; 
  border-bottom: 1px solid #232533;
  transition: 0.2s;
}

.part-option:hover { 
  background-color: rgba(59, 130, 246, 0.1); 
}

.p-name { font-weight: 500; color: #a9b1d6; }
.p-price { color: #10b981; font-weight: bold; }

/* Butoane */
.btn { 
  padding: 8px 18px; 
  border-radius: 6px; 
  cursor: pointer; 
  font-weight: 600; 
  transition: 0.2s;
}

.btn-outline { 
  background: transparent; 
  border: 1px solid #3b82f6; 
  color: #3b82f6; 
}

.btn-outline:hover { 
  background: #3b82f6; 
  color: white; 
}

.btn-primary { 
  background: #10b981; 
  border: none; 
  color: white; 
  padding: 15px; 
  font-size: 1rem;
}

.btn-primary:hover:not(:disabled) { 
  background: #059669; 
  transform: translateY(-1px);
}

.btn-primary:disabled { 
  background: #334155; 
  cursor: not-allowed; 
  opacity: 0.5;
}

/* Sidebar & Sumar */
.summary-card { 
  background: #1a1b26; 
  border: 1px solid #2a2d3e; 
  padding: 25px; 
  border-radius: 12px; 
  margin-bottom: 20px; 
}

.price-highlight { 
  color: #10b981; 
  font-size: 1.6rem; 
}

.info-box { 
  background: #1e293b; 
  padding: 20px; 
  border-radius: 12px; 
  border-left: 4px solid #3b82f6; 
}

.info-box h4 { 
  color: #3b82f6; 
  margin-bottom: 10px; 
}

/* Scrollbar personalizat pentru lista de piese */
.parts-selector-box::-webkit-scrollbar {
  width: 6px;
}
.parts-selector-box::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 10px;
}
</style>