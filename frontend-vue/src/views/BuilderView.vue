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
                <span v-if="category.incompatibil" class="incompatibil-warning">
                  ⚠️ Incompatibil cu selecția curentă
                </span>
              </div>
              <div v-else class="no-part">
                <span v-if="category.filterLocked" class="filter-hint">
                  {{ category.filterHint }}
                </span>
                <span v-else>Nicio componentă selectată</span>
              </div>
            </div>

            <div class="price-section">
              <span v-if="category.selectedPart">{{ displayPartPrice(category.selectedPart) }} RON</span>
            </div>

            <div v-if="category.activeFilter" class="filter-tag">
              🔗 {{ category.activeFilter }}
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
            <div v-if="category.parts.length === 0" class="mini-loading">
              {{ category.filterLocked
                ? 'Nicio piesă compatibilă găsită pentru filtrul activ.'
                : 'Nu există piese disponibile în această categorie.' }}
            </div>
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
import axios from 'axios'
import api from '../plugins/axios.js'

const agentLoading = ref(false)
const agentResult = ref(null)
const agentError = ref(null)
const loading = ref(true)
const openCategoryId = ref(null)

const categories = ref([
  { id: 'cpus',         name: 'Procesor',      icon: '🧠', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: '',                            incompatibil: false },
  { id: 'motherboards', name: 'Placă de Bază', icon: '🛹', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: 'Alege mai întâi un Procesor', incompatibil: false },
  { id: 'gpus',         name: 'Placă Video',   icon: '🎮', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: '',                            incompatibil: false },
  { id: 'rams',         name: 'Memorie RAM',   icon: '⚡', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: 'Alege mai întâi o Placă de Bază', incompatibil: false },
  { id: 'storages',     name: 'Stocare',       icon: '💾', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: '',                            incompatibil: false },
  { id: 'psus',         name: 'Sursă',         icon: '🔌', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: '',                            incompatibil: false },
  { id: 'cases',        name: 'Carcasă',       icon: '📦', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: '',                            incompatibil: false },
  { id: 'coolers',      name: 'Cooler CPU',    icon: '❄️', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false, filterHint: '',                            incompatibil: false },
])

const catToKeyMap = {
  'cpus': 'cpu', 'gpus': 'gpu', 'motherboards': 'motherboard',
  'rams': 'ram', 'storages': 'storage', 'psus': 'psu',
  'cases': 'case', 'coolers': 'cooler'
}

// ── Fetch ─────────────────────────────────────────────────
const fetchParts = async () => {
  loading.value = true
  try {
    for (const category of categories.value) {
      const response = await axios.get(`http://127.0.0.1:8000/api/${category.id}/`)
      const parts = response.data.results || response.data
      category.allParts = parts        
      category.parts = [...parts]      
      console.log(`✅ Încărcat ${category.id}: ${parts.length} piese`)
    }
  } catch (err) {
    console.error('Eroare la citirea bazei de date:', err)
  } finally {
    loading.value = false
  }
}

// ── Select cu filtre în cascadă ───────────────────────────
const selectPart = (categoryId, part) => {
  const category = categories.value.find(c => c.id === categoryId)
  category.selectedPart = part
  openCategoryId.value = null
  agentResult.value = null
  agentError.value = null

  const key = catToKeyMap[categoryId] || categoryId
  const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
  currentBuild[key] = part
  localStorage.setItem('current_build', JSON.stringify(currentBuild))

  if (categoryId === 'cpus') {
    const socket = part.socket
    const moboCat = categories.value.find(c => c.id === 'motherboards')

    if (socket) {
      moboCat.parts = moboCat.allParts.filter(m => m.socket === socket)
      moboCat.activeFilter = `Socket ${socket}`
      moboCat.filterLocked = true

      if (moboCat.selectedPart && moboCat.selectedPart.socket !== socket) {
        moboCat.incompatibil = true
      } else {
        moboCat.incompatibil = false
      }
    } else {
      moboCat.parts = [...moboCat.allParts]
      moboCat.activeFilter = null
      moboCat.filterLocked = false
      moboCat.incompatibil = false
    }

    const ramCat = categories.value.find(c => c.id === 'rams')
    ramCat.parts = [...ramCat.allParts]
    ramCat.activeFilter = null
    ramCat.filterLocked = false
    ramCat.incompatibil = false
  }

  if (categoryId === 'motherboards') {
    const tipRam = part.tip_ram
    const ramCat = categories.value.find(c => c.id === 'rams')

    if (tipRam) {
      ramCat.parts = ramCat.allParts.filter(r => r.tip === tipRam)
      ramCat.activeFilter = tipRam
      ramCat.filterLocked = true

      if (ramCat.selectedPart && ramCat.selectedPart.tip !== tipRam) {
        ramCat.incompatibil = true
      } else {
        ramCat.incompatibil = false
      }
    } else {
      ramCat.parts = [...ramCat.allParts]
      ramCat.activeFilter = null
      ramCat.filterLocked = false
      ramCat.incompatibil = false
    }
  }
}

// ── Remove cu reset filtre ────────────────────────────────
const removePart = (categoryId) => {
  const category = categories.value.find(c => c.id === categoryId)
  if (!category) return
  category.selectedPart = null
  category.incompatibil = false
  agentResult.value = null
  agentError.value = null

  const key = catToKeyMap[categoryId] || categoryId
  const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
  delete currentBuild[key]
  localStorage.setItem('current_build', JSON.stringify(currentBuild))

  if (categoryId === 'cpus') {
    const moboCat = categories.value.find(c => c.id === 'motherboards')
    moboCat.parts = [...moboCat.allParts]
    moboCat.activeFilter = null
    moboCat.filterLocked = false
    moboCat.incompatibil = false

    const ramCat = categories.value.find(c => c.id === 'rams')
    ramCat.parts = [...ramCat.allParts]
    ramCat.activeFilter = null
    ramCat.filterLocked = false
    ramCat.incompatibil = false
  }

  if (categoryId === 'motherboards') {
    const ramCat = categories.value.find(c => c.id === 'rams')
    ramCat.parts = [...ramCat.allParts]
    ramCat.activeFilter = null
    ramCat.filterLocked = false
    ramCat.incompatibil = false
  }
}

const openPartSelector = (categoryId) => {
  openCategoryId.value = openCategoryId.value === categoryId ? null : categoryId
}

// ── Salvare ───────────────────────────────────────────────
const salveazaPC = async () => {
  try {
    const payload = {
      cpu:         categories.value.find(c => c.id === 'cpus')?.selectedPart?.id || null,
      gpu:         categories.value.find(c => c.id === 'gpus')?.selectedPart?.id || null,
      motherboard: categories.value.find(c => c.id === 'motherboards')?.selectedPart?.id || null,
      ram:         categories.value.find(c => c.id === 'rams')?.selectedPart?.id || null,
      storage:     categories.value.find(c => c.id === 'storages')?.selectedPart?.id || null,
      psu:         categories.value.find(c => c.id === 'psus')?.selectedPart?.id || null,
      case:        categories.value.find(c => c.id === 'cases')?.selectedPart?.id || null,
      cooler:      categories.value.find(c => c.id === 'coolers')?.selectedPart?.id || null,
      pret_total:  totalPrice.value
    }
    const response = await api.post('saved-builds/', payload)
    alert(`Build salvat cu succes sub numele: ${response.data.nume}`)
  } catch (error) {
    console.error('Eroare la salvare:', error)
    alert(error.response?.status === 401 ? 'Loghează-te pentru a salva!' : 'Eroare server.')
  }
}

// ── Agent AI ──────────────────────────────────────────────
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

// ── Helpers ───────────────────────────────────────────────
const selectedPartsCount = computed(() => categories.value.filter(cat => cat.selectedPart).length)
const totalPartsLoaded = computed(() => categories.value.reduce((acc, cat) => acc + (cat.parts?.length || 0), 0))
const totalPrice = computed(() => categories.value.reduce((sum, cat) => sum + parseFloat(cat.selectedPart?.pret || 0), 0))
const progressPercentage = computed(() => (selectedPartsCount.value / categories.value.length) * 100)
const displayPartName = (part) => part.nume || part.model || 'Componentă'
const displayPartPrice = (part) => part.pret || '0.00'

// ── Mount + încarcă din sesiuni/storage ──
onMounted(async () => {
  await fetchParts()

  const saved = sessionStorage.getItem('loadBuild')
  if (saved) {
    const parts = JSON.parse(saved)
    for (const slot of categories.value) {
      const key = catToKeyMap[slot.id]
      if (key && parts[key]) slot.selectedPart = parts[key]
    }
    sessionStorage.removeItem('loadBuild')
  }

  const pendingAiBuild = localStorage.getItem('pending_ai_build')
  if (pendingAiBuild) {
    try {
      const buildRecomandat = JSON.parse(pendingAiBuild)
      
      if (buildRecomandat.cpu) {
         const cpuCat = categories.value.find(c => c.id === 'cpus')
         const cpuPart = cpuCat.allParts.find(p => p.id === buildRecomandat.cpu.id)
         if (cpuPart) selectPart('cpus', cpuPart)
      }
      
      if (buildRecomandat.gpu) {
         const gpuCat = categories.value.find(c => c.id === 'gpus')
         const gpuPart = gpuCat.allParts.find(p => p.id === buildRecomandat.gpu.id)
         if (gpuPart) selectPart('gpus', gpuPart)
      }
      
      if (buildRecomandat.motherboard) {
         const moboCat = categories.value.find(c => c.id === 'motherboards')
         const moboPart = moboCat.allParts.find(p => p.id === buildRecomandat.motherboard.id)
         if (moboPart) selectPart('motherboards', moboPart)
      }
      
      if (buildRecomandat.ram) {
         const ramCat = categories.value.find(c => c.id === 'rams')
         const ramPart = ramCat.allParts.find(p => p.id === buildRecomandat.ram.id)
         if (ramPart) selectPart('rams', ramPart)
      }

      localStorage.removeItem('pending_ai_build')
      agentError.value = null
      agentResult.value = null

    } catch (error) {
      console.error('Eroare la parsarea build-ului AI:', error)
      localStorage.removeItem('pending_ai_build')
    }
  }

  const currentBuildStr = localStorage.getItem('current_build')
  if (currentBuildStr && !pendingAiBuild && !saved) {
    try {
      const currentBuild = JSON.parse(currentBuildStr)
      for (const slot of categories.value) {
        const key = catToKeyMap[slot.id]
        if (key && currentBuild[key]) {
           const part = slot.allParts.find(p => p.id === currentBuild[key].id)
           if (part) {
               selectPart(slot.id, part) 
           }
        }
      }
    } catch (e) {
      console.error("Eroare la încărcarea current_build:", e)
    }
  }
})
</script>

<style scoped>
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

.category-info { 
  flex: 1;
  display: flex; 
  flex-direction: column; 
  margin-left: 15px;
}

.price-section { 
  margin-left: auto;
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

.no-part {
  font-size: 0.8rem;
  color: #475569;
}

.filter-hint {
  color: #f59e0b;
  font-size: 0.78rem;
}

.incompatibil-warning {
  display: block;
  font-size: 0.75rem;
  color: #f43f5e;
  margin-top: 3px;
}

.filter-tag {
  font-size: 0.7rem;
  color: #475569;
  background: rgba(255,255,255,0.04);
  border: 1px solid #2a2d3e;
  border-radius: 20px;
  padding: 2px 10px;
  margin-right: 12px;
  white-space: nowrap;
}

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

.btn-block { width: 100%; }

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

.btn-analyze {
  width: 100%;
  padding: 10px;
  background: #6366f1;
  border: none;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  margin-bottom: 12px;
  transition: 0.2s;
}
.btn-analyze:hover:not(:disabled) { background: #4f46e5; }
.btn-analyze:disabled { opacity: 0.6; cursor: not-allowed; }

.agent-error {
  background: rgba(239,68,68,0.1);
  border: 1px solid #ef4444;
  color: #fca5a5;
  padding: 10px;
  border-radius: 6px;
  font-size: 0.85rem;
}

.agent-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 10px;
}
.badge-ok      { background: rgba(16,185,129,0.2); color: #10b981; }
.badge-warning { background: rgba(245,158,11,0.2);  color: #f59e0b; }
.badge-error   { background: rgba(239,68,68,0.2);   color: #ef4444; }

.agent-section { margin-top: 10px; font-size: 0.85rem; color: #a9b1d6; }
.agent-section ul { margin: 4px 0 0 16px; }
.agent-section p { margin-top: 4px; line-height: 1.5; }
.sugestie-item { padding: 2px 0 2px 8px; color: #7aa2f7; font-size: 0.8rem; }

.parts-selector-box::-webkit-scrollbar { width: 6px; }
.parts-selector-box::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
.btn-remove {
  background: transparent;
  border: 1px solid #ef4444;
  color: #ef4444;
  padding: 8px 18px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: 0.2s;
}

.btn-remove:hover {
  background: #ef4444;
  color: white;
}
</style>