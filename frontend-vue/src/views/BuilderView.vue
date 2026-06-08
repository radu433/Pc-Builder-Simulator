<template>
  <div class="synth-builder-container">
    
    <!-- SIDEBAR -->
    <aside class="synth-sidebar glass-panel">
      <div class="sidebar-header">
        <span class="gradient-text">DASHBOARD</span>
      </div>
      
      <div class="category-list">
        <div v-for="(cat, idx) in categories" :key="cat.id" 
             class="category-item" 
             :class="{ active: openCategoryId === cat.id }"
             @click="openCategory(cat.id)">
             <div class="cat-left">
               <span class="cat-icon">{{ cat.icon }}</span>
               <span class="cat-name">{{ idx + 1 }}. {{ cat.name }}</span>
             </div>
             <span class="status-dot" :class="{ selected: cat.selectedPart }"></span>
        </div>
      </div>

      <div class="sidebar-footer">
         <button class="btn-neon-full" @click="openCategory(null)">📋 View Summary</button>
         <div style="height: 10px;"></div>
         <button class="btn-solid-green" @click="salveazaPC" :disabled="selectedPartsCount === 0">
           🚀 Save Build
         </button>
         <div style="height: 10px;"></div>
         <button class="btn-solid-purple" @click="analizeazaBuild" :disabled="selectedPartsCount === 0 || agentLoading">
           {{ agentLoading ? '⏳ Analyzing...' : '✨ AI Analysis' }}
         </button>
      </div>
    </aside>
    
    <!-- MAIN AREA -->
    <main class="synth-main">
       <div class="main-header">
           <h2>{{ activeCategory ? activeCategory.name.toUpperCase() + ' SELECTION' : 'BUILD SUMMARY' }}</h2>
           <div class="total-price">
               <span class="compatible-badge" v-if="selectedPartsCount > 0 && !hasIncompatibilities">● Compatible</span> 
               <span class="incompatible-badge" v-if="hasIncompatibilities">● Check Issues</span> 
               Build Total: <span class="neon-price">{{ totalPrice.toFixed(2) }} RON</span>
           </div>
       </div>

       <div v-if="loading" class="loading-state glass-panel">
          <div class="spinner"></div>
          <p>Loading components...</p>
       </div>

       <div class="parts-grid-panel" v-else-if="activeCategory">
          <!-- SEARCH & FILTERS -->
          <div class="builder-filters glass-panel">
            <div class="builder-filters-header">
              <div class="search-input-wrapper">
                <span class="icon">🔍</span>
                <input type="text" v-model="searchQuery" placeholder="Caută componenta..." @input="onFilterChange" />
              </div>
              <div class="price-inputs">
                <input type="number" v-model="minPrice" placeholder="Preț Min" @input="onFilterChange" />
                <span>-</span>
                <input type="number" v-model="maxPrice" placeholder="Preț Max" @input="onFilterChange" />
              </div>
              <label class="checkbox-label">
                <input type="checkbox" v-model="inStockOnly" @change="onFilterChange" /> Doar în stoc
              </label>
              <button class="btn-neon-remove reset-btn" @click="resetFilters(activeCategory.id)">🔄 Reset</button>
            </div>
            
            <div class="dynamic-filters-row" v-if="activeCategoryFilters.length">
              <div v-for="filter in activeCategoryFilters" :key="filter.key" class="filter-group">
                <label class="filter-label-main">{{ filter.label }}</label>
                
                <select v-if="filter.type === 'select'" v-model="dynamicFilters[filter.key]" @change="onFilterChange" class="filter-select">
                  <option value="">Orice</option>
                  <option v-for="opt in filter.options" :key="opt" :value="opt">{{ opt }}</option>
                </select>

                <div v-else-if="filter.type === 'checkbox-group'" class="checkbox-group-wrapper">
                  <label v-for="opt in filter.options" :key="filter.key + '-' + opt" class="checkbox-label small-label">
                    <input type="checkbox" :value="opt" v-model="dynamicFilters[filter.key]" @change="onFilterChange" />
                    {{ opt }}
                  </label>
                </div>

                <input v-else :type="filter.type" v-model="dynamicFilters[filter.key]" :placeholder="filter.placeholder" @input="onFilterChange" class="filter-input" />
              </div>
            </div>
          </div>

          <div class="parts-grid" v-if="activeCategory.parts.length > 0">
             <div v-for="part in activeCategory.parts" :key="part.id" class="synth-product-card glass-panel" :class="{ 'is-selected': activeCategory.selectedPart?.id === part.id }">
                 <div class="card-glow"></div>
                 <div class="card-content">
                    <router-link :to="`/products/${activeCategory.id}/${part.id}`" class="card-link" style="text-decoration: none; color: inherit;">
                      <div class="card-top">
                        <div class="card-brand">{{ part.brand || part.producator || 'N/A' }}</div>
                        <a v-if="part.url_produs" :href="part.url_produs" target="_blank" class="external-link-icon" title="Cumpără de pe magazin" @click.stop>🛒</a>
                      </div>
                      
                      <div class="card-image-box">
                          <img :src="part.imagine_url || 'https://placehold.co/200x200/111827/00f0ff?text=No+Image'" :alt="part.nume">
                      </div>
                      
                      <h3 class="card-title">{{ displayPartName(part) }}</h3>
                      <p class="card-desc">{{ (part.nume || "").substring(0, 50) }}...</p>
                    </router-link>
                    
                    <div class="card-specs">
                       <div class="spec-col" v-if="part.frecventa"><span>Speed</span><br>{{ part.frecventa }}</div>
                       <div class="spec-col" v-if="part.capacitate || part.memorie"><span>Memory</span><br>{{ part.capacitate || part.memorie }}</div>
                       <div class="spec-col" v-if="part.socket"><span>Socket</span><br>{{ part.socket }}</div>
                       <div class="spec-col" v-if="part.putere"><span>Power</span><br>{{ part.putere }}W</div>
                       <div class="spec-col" v-if="part.format"><span>Form</span><br>{{ part.format }}</div>
                    </div>

                    <div class="card-footer">
                       <div class="card-price">{{ displayPartPrice(part) }} RON</div>
                       <button class="btn-neon" v-if="activeCategory.selectedPart?.id !== part.id" @click="selectPart(activeCategory.id, part)">SELECT</button>
                       <button class="btn-neon-remove" v-else @click="removePart(activeCategory.id)">REMOVE</button>
                    </div>
                 </div>
             </div>
          </div>
          <div v-else class="empty-parts glass-panel">
              <p>Nicio componentă disponibilă sau incompatibilitate cu selecția curentă.</p>
              <button class="btn-neon" v-if="activeCategory.filterLocked" @click="resetFilters(activeCategory.id)">Reset Filters</button>
          </div>

          <!-- PAGINATION -->
          <div class="pagination-controls glass-panel" v-if="totalPages > 1">
            <button class="page-btn" :disabled="currentPage <= 1" @click="goToPage(1)">«</button>
            <button class="page-btn" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">‹</button>
            <button v-for="p in visiblePages" :key="p" class="page-btn" :class="{ active: p === currentPage, ellipsis: p === '...' }" :disabled="p === '...'" @click="p !== '...' && goToPage(p)">
              {{ p }}
            </button>
            <button class="page-btn" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">›</button>
            <button class="page-btn" :disabled="currentPage >= totalPages" @click="goToPage(totalPages)">»</button>
            <span class="page-info">Pagina {{ currentPage }} din {{ totalPages }} ({{ totalCount }} produse)</span>
          </div>
       </div>

       <!-- SUMMARY PANEL -->
       <div class="summary-view-panel" v-else>
           <div class="glass-panel">
             <h3 class="gradient-text">Your Selected Parts</h3>
             <div class="selected-parts-list">
                 <div class="selected-row" v-for="cat in categories" :key="cat.id" @click="openCategory(cat.id)">
                     <div class="sr-left">
                       <span class="sr-icon">{{ cat.icon }}</span>
                       <span class="sr-cat">{{ cat.name }}</span>
                     </div>
                     <div class="sr-right">
                       <span class="sr-name" :class="{'text-muted': !cat.selectedPart}">{{ cat.selectedPart ? displayPartName(cat.selectedPart) : 'None selected' }}</span>
                       <span class="sr-price" v-if="cat.selectedPart">{{ displayPartPrice(cat.selectedPart) }} RON</span>
                       <button class="btn-icon-remove" v-if="cat.selectedPart" @click.stop="removePart(cat.id)">✕</button>
                     </div>
                 </div>
             </div>
           </div>

           <!-- AI Results -->
           <div v-if="agentResult || agentError" class="ai-glass-panel glass-panel mt-4">
              <h3 class="gradient-text">✨ AI Analysis Results</h3>
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
              </div>
           </div>
       </div>

    </main>
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
const openCategoryId = ref('cpus') // Default la primul tab

const categories = ref([
  { id: 'cpus',         name: 'Procesor',      icon: '🧠', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'motherboards', name: 'Placă de Bază', icon: '🛹', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'gpus',         name: 'Placă Video',   icon: '🎮', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'rams',         name: 'Memorie RAM',   icon: '⚡', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'storages',     name: 'Stocare',       icon: '💾', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'psus',         name: 'Sursă',         icon: '🔌', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'cases',        name: 'Carcasă',       icon: '📦', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
  { id: 'coolers',      name: 'Cooler CPU',    icon: '❄️', parts: [], allParts: [], selectedPart: null, activeFilter: null, filterLocked: false },
])

const catToKeyMap = {
  'cpus': 'cpu', 'gpus': 'gpu', 'motherboards': 'motherboard',
  'rams': 'ram', 'storages': 'storage', 'psus': 'psu',
  'cases': 'case', 'coolers': 'cooler'
}

const activeCategory = computed(() => {
  if (!openCategoryId.value) return null;
  return categories.value.find(c => c.id === openCategoryId.value)
})

const hasIncompatibilities = computed(() => categories.value.some(c => c.incompatibil))

// --- FILTERS STATE ---
const searchQuery = ref('')
const minPrice = ref('')
const maxPrice = ref('')
const inStockOnly = ref(false)
const dynamicFilters = ref({})

// --- PAGINATION STATE ---
const currentPage = ref(1)
const totalCount = ref(0)
const pageSize = 50

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages = []
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
    return pages
  }
  
  pages.push(1)
  if (current > 3) pages.push('...')
  
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  
  for (let i = start; i <= end; i++) pages.push(i)
  
  if (current < total - 2) pages.push('...')
  pages.push(total)
  
  return pages
})

const goToPage = (page) => {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
  applyFilters()
  // Scroll to top of parts grid
  const grid = document.querySelector('.parts-grid-panel')
  if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const onFilterChange = () => {
  currentPage.value = 1
  applyFilters()
}

const allSocketOptions = [
  'AM4', 'AM5', '1851', 'LGA 1851', 'FM2', 'FM2+', 'FM2, FM2+',
  'AM3+', 'AM3', 'TR4', 'TRX40', 'sTR5', 'sWRX80', 'sWRX8',
  '1700', '1150', '1200', '1151', '1155', '2066', '2011-V3'
]

const categoryFiltersMap = {
  cpus: [
    { key: 'producator', label: 'Producător', type: 'select', options: ['AMD', 'Intel'] },
    { key: 'socket', label: 'Socket', type: 'checkbox-group', options: allSocketOptions },
  ],
  motherboards: [
    { key: 'socket', label: 'Socket', type: 'checkbox-group', options: allSocketOptions },
    { key: 'tip_ram', label: 'Tip Memorie Suportată', type: 'select', options: ['DDR4', 'DDR5'] },
    { key: 'format', label: 'Format', type: 'select', options: ['ATX', 'mATX', 'Mini-ITX'] }
  ],
  gpus: [
    { key: 'producator_chipset', label: 'Producător Chipset', type: 'select', options: ['NVIDIA', 'AMD', 'Intel'] },
    { key: 'memorie', label: 'Capacitate VRAM', type: 'number', placeholder: 'ex: 8, 12, 16' }
  ],
  rams: [
    { key: 'tip', label: 'Tip Memorie', type: 'select', options: ['DDR4', 'DDR5'] },
    { key: 'capacitate', label: 'Capacitate (GB)', type: 'number', placeholder: 'ex: 16, 32' }
  ],
  storages: [
    { key: 'tip', label: 'Tip Stocare', type: 'select', options: ['SSD', 'HDD', 'NVME'] },
    { key: 'capacitate', label: 'Capacitate (GB)', type: 'number', placeholder: 'ex: 500, 1000' }
  ],
  psus: [
    { key: 'putere', label: 'Putere (W)', type: 'number', placeholder: 'ex: 750, 850' },
    { key: 'certificare', label: 'Certificare 80+', type: 'select', options: ['White', 'Bronze', 'Gold', 'Platinum', 'Titanium'] }
  ],
  cases: [
    { key: 'tip_carcasa', label: 'Tip Carcasă', type: 'select', options: ['MID', 'FULL', 'MINI', 'SFF', 'AQ'] }
  ],
  coolers: [
    { key: 'socket', label: 'Socket', type: 'checkbox-group', options: allSocketOptions },
    { key: 'tip_racire', label: 'Tip Răcire', type: 'select', options: ['Air', 'AIO 120mm', 'AIO 240mm', 'AIO 280mm', 'AIO 360mm'] }
  ]
}

const activeCategoryFilters = computed(() => {
  if (!activeCategory.value) return []
  return categoryFiltersMap[activeCategory.value.id] || []
})

const initDynamicFilters = () => {
  const filters = {}
  activeCategoryFilters.value.forEach(f => {
    if (f.type === 'checkbox-group') {
      filters[f.key] = []
    } else {
      filters[f.key] = ''
    }
  })
  dynamicFilters.value = filters
}

import { watch } from 'vue'

watch(openCategoryId, () => {
  searchQuery.value = ''
  minPrice.value = ''
  maxPrice.value = ''
  inStockOnly.value = false
  currentPage.value = 1
  initDynamicFilters()
  applyFilters()
})

const applyFilters = async () => {
  const cat = activeCategory.value
  if (!cat) return

  loading.value = true

  const params = {}

  // 1. Compatibility Lock
  if (cat.filterLocked && cat.activeFilter) {
    if (cat.id === 'motherboards' && cat.activeFilter.startsWith('Socket ')) {
       params.socket = cat.activeFilter.replace('Socket ', '')
    } else if (cat.id === 'rams') {
       params.tip = cat.activeFilter
    }
  }

  // 2. Global Filters
  if (searchQuery.value) params.search = searchQuery.value
  if (minPrice.value) params.min_pret = minPrice.value
  if (maxPrice.value) params.max_pret = maxPrice.value
  if (inStockOnly.value) params.in_stock = 'true'

  // 3. Dynamic Filters
  for (const [key, value] of Object.entries(dynamicFilters.value)) {
    if (Array.isArray(value)) {
      if (value.length > 0) {
        params[key] = value.join('|')
      }
    } else if (value !== '' && value !== null && value !== undefined) {
       params[key] = value
    }
  }

  // 4. Pagination
  params.page = currentPage.value
  params.page_size = pageSize

  try {
    const response = await axios.get(`/api/${cat.id}/`, { params })
    if (response.data.results !== undefined) {
      cat.parts = response.data.results
      totalCount.value = response.data.count || 0
    } else {
      cat.parts = response.data
      totalCount.value = response.data.length || 0
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
// --- END FILTERS STATE ---

const openCategory = (id) => {
  openCategoryId.value = id
}

const fetchParts = async () => {
  loading.value = true
  try {
    for (const category of categories.value) {
      const response = await axios.get(`/api/${category.id}/`)
      const parts = response.data.results || response.data
      category.allParts = parts        
      category.parts = [...parts]      
    }
  } catch (err) {
    console.error('Eroare:', err)
  } finally {
    loading.value = false
    applyFilters()
  }
}

const resetFilters = (categoryId) => {
  searchQuery.value = ''
  minPrice.value = ''
  maxPrice.value = ''
  inStockOnly.value = false
  currentPage.value = 1
  initDynamicFilters()

  if (categoryId === 'cpus' || categoryId === 'motherboards' || categoryId === 'rams') {
     const cat = categories.value.find(c => c.id === categoryId)
     if (cat) {
       cat.filterLocked = false
       cat.activeFilter = null
     }
  }
  applyFilters()
}

const selectPart = (categoryId, part) => {
  const category = categories.value.find(c => c.id === categoryId)
  if (!category) return
  category.selectedPart = part
  agentResult.value = null
  agentError.value = null

  const key = catToKeyMap[categoryId] || categoryId
  const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
  if (part && part.id != null) {
    currentBuild[key] = part
  } else {
    delete currentBuild[key]
  }
  localStorage.setItem('current_build', JSON.stringify(currentBuild))

  if (categoryId === 'cpus') {
    const socket = part.socket
    const moboCat = categories.value.find(c => c.id === 'motherboards')
    if (socket && moboCat) {
      moboCat.activeFilter = `Socket ${socket}`
      moboCat.filterLocked = true
      moboCat.incompatibil = moboCat.selectedPart && moboCat.selectedPart.socket !== socket
    }
  }

  if (categoryId === 'motherboards') {
    const tipRam = part.tip_ram
    const ramCat = categories.value.find(c => c.id === 'rams')
    if (tipRam && ramCat) {
      ramCat.activeFilter = tipRam
      ramCat.filterLocked = true
      ramCat.incompatibil = ramCat.selectedPart && ramCat.selectedPart.tip !== tipRam && ramCat.selectedPart.tip_memorie !== tipRam
    }
  }

  applyFilters()
}

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
    if (moboCat) {
      moboCat.activeFilter = null
      moboCat.filterLocked = false
      moboCat.incompatibil = false
    }
  }

  if (categoryId === 'motherboards') {
    const ramCat = categories.value.find(c => c.id === 'rams')
    if (ramCat) {
      ramCat.activeFilter = null
      ramCat.filterLocked = false
      ramCat.incompatibil = false
    }
  }

  applyFilters()
}

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
    alert(error.response?.status === 401 ? 'Loghează-te pentru a salva!' : 'Eroare server.')
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
    const response = await axios.post('/analizeaza-build', payload)
    agentResult.value = response.data
    openCategoryId.value = null // Sari la sumar sa vada analiza
  } catch (err) {
    agentError.value = 'Nu s-a putut contacta agentul.'
  } finally {
    agentLoading.value = false
  }
}

const selectedPartsCount = computed(() => categories.value.filter(cat => cat.selectedPart).length)
const totalPrice = computed(() => categories.value.reduce((sum, cat) => sum + parseFloat(cat.selectedPart?.pret || 0), 0))
const displayPartName = (part) => part.nume || part.model || 'Componentă'
const displayPartPrice = (part) => part.pret || '0.00'

onMounted(async () => {
  // Curăță current_build corupt
  try {
    const raw = localStorage.getItem('current_build')
    if (raw) {
      const parsed = JSON.parse(raw)
      let changed = false
      for (const k of Object.keys(parsed)) {
        if (parsed[k] === null || parsed[k]?.id == null) {
          delete parsed[k]
          changed = true
        }
      }
      if (changed) localStorage.setItem('current_build', JSON.stringify(parsed))
    }
  } catch { localStorage.removeItem('current_build') }

  await fetchParts()

  const saved = sessionStorage.getItem('loadBuild')
  if (saved) {
    const parts = JSON.parse(saved)
    for (const slot of categories.value) {
      const key = catToKeyMap[slot.id]
      if (key && parts[key] && parts[key].id != null) {
        slot.selectedPart = parts[key]
      }
    }
    sessionStorage.removeItem('loadBuild')
  }

  const currentBuildStr = localStorage.getItem('current_build')
  if (currentBuildStr && !saved) {
    try {
      const currentBuild = JSON.parse(currentBuildStr)
      for (const slot of categories.value) {
        const key = catToKeyMap[slot.id]
        if (key && currentBuild[key]) {
          const savedId = currentBuild[key]?.id
          if (savedId != null) {
            const part = slot.allParts?.find(p => p.id === savedId)
            if (part) selectPart(slot.id, part)
          }
        }
      }
    } catch (e) {}
  }

  const pendingAiBuild = localStorage.getItem('pending_ai_build')
  if (pendingAiBuild) {
    try {
      const buildData = JSON.parse(pendingAiBuild)
      const build = buildData.build || buildData
      for (const slot of categories.value) {
        const key = catToKeyMap[slot.id]
        if (key && build[key] && build[key].id != null) {
          const part = slot.allParts?.find(p => p.id === build[key].id)
          if (part) selectPart(slot.id, part)
        }
      }
    } catch (e) {}
    localStorage.removeItem('pending_ai_build')
  }
})

</script>

<style scoped>
/* =========== MODERN UI =========== */
.synth-builder-container {
  display: flex;
  min-height: calc(100vh - 80px);
  padding: 30px;
  gap: 30px;
  color: #e2e8f0;
}

/* Glassmorphism Utilities */
.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.gradient-text {
  background: linear-gradient(90deg, #00f0ff, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
}

/* SIDEBAR */
.synth-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 20px;
  height: fit-content;
  position: sticky;
  top: 30px;
}

.sidebar-header {
  font-size: 1.2rem;
  letter-spacing: 2px;
  margin-bottom: 30px;
  text-align: center;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 30px;
}

.category-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255,255,255,0.02);
  border: 1px solid transparent;
}

.category-item:hover {
  background: rgba(255,255,255,0.05);
}

.category-item.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.3);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.1);
}

.cat-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cat-icon { font-size: 1.2rem; }
.cat-name { font-weight: 500; font-size: 0.95rem; }

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #334155;
  border: 2px solid #1e293b;
}

.status-dot.selected {
  background: #00f0ff;
  box-shadow: 0 0 8px #00f0ff;
  border-color: rgba(0, 240, 255, 0.3);
}

.btn-solid-green, .btn-solid-purple, .btn-neon-full {
  width: 100%;
  padding: 14px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  color: white;
}
.btn-neon-full { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); }
.btn-neon-full:hover { background: rgba(255,255,255,0.1); }

.btn-solid-green { background: #10b981; }
.btn-solid-green:hover:not(:disabled) { background: #059669; box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); }
.btn-solid-green:disabled { background: #334155; opacity: 0.5; cursor: not-allowed; }

.btn-solid-purple { background: #a855f7; }
.btn-solid-purple:hover:not(:disabled) { background: #9333ea; box-shadow: 0 0 15px rgba(168, 85, 247, 0.4); }
.btn-solid-purple:disabled { background: #334155; opacity: 0.5; cursor: not-allowed; }

/* MAIN AREA */
.synth-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}

.main-header h2 {
  font-size: 1.5rem;
  letter-spacing: 1px;
  font-weight: 700;
}

.total-price {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 1.1rem;
}

.compatible-badge { color: #10b981; font-size: 0.9rem; font-weight: 600; text-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
.incompatible-badge { color: #ef4444; font-size: 0.9rem; font-weight: 600; text-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }

.neon-price {
  color: #00f0ff;
  font-weight: 800;
  font-size: 1.4rem;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

/* CARDS GRID */
.parts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 25px;
}

.synth-product-card {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px;
  transition: transform 0.3s ease, border-color 0.3s ease;
}

.synth-product-card:hover {
  transform: translateY(-5px);
  border-color: rgba(0, 240, 255, 0.5);
}

.synth-product-card.is-selected {
  border-color: #a855f7;
  box-shadow: 0 0 20px rgba(168, 85, 247, 0.2);
}

.card-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
}
.card-brand {
  background: rgba(255,255,255,0.1);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  color: #94a3b8;
}

.card-image-box {
  width: 100%;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}
.external-link-icon { font-size: 1.2rem; text-decoration: none; background: rgba(26, 27, 38, 0.85); border-radius: 50%; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 10; margin-left: auto; }
.external-link-icon:hover { transform: scale(1.1); background: #00f0ff; border-color: #00f0ff; }
.card-link { display: block; }
.card-image-box img {
  max-width: 80%;
  max-height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));
}

.card-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 5px;
  line-height: 1.3;
}

.card-desc {
  font-size: 0.8rem;
  color: #64748b;
  margin-bottom: 15px;
  min-height: 35px;
}

.card-specs {
  display: flex;
  gap: 15px;
  margin-bottom: 25px;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 15px;
}
.spec-col span {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
}
.spec-col {
  font-size: 0.85rem;
  font-weight: 600;
  color: #e2e8f0;
}

.card-footer {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-price {
  font-size: 1.2rem;
  font-weight: 800;
}

.btn-neon {
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.8), rgba(0, 240, 255, 0.8));
  border: none;
  padding: 8px 20px;
  border-radius: 20px;
  color: white;
  font-weight: 700;
  cursor: pointer;
  transition: 0.3s;
}
.btn-neon:hover {
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.6);
  transform: scale(1.05);
}

.btn-neon-remove {
  background: transparent;
  border: 1px solid #ef4444;
  color: #ef4444;
  padding: 8px 15px;
  border-radius: 20px;
  font-weight: 700;
  cursor: pointer;
  transition: 0.3s;
}
.btn-neon-remove:hover {
  background: rgba(239, 68, 68, 0.2);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}

/* SUMMARY VIEW */
.summary-view-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.selected-parts-list {
  padding: 20px;
}

.selected-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  cursor: pointer;
  transition: 0.2s;
}
.selected-row:hover {
  background: rgba(255,255,255,0.02);
}

.sr-left {
  display: flex;
  align-items: center;
  gap: 15px;
  width: 200px;
}
.sr-icon { font-size: 1.2rem; }
.sr-cat { font-weight: 600; color: #94a3b8; }

.sr-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 20px;
}
.sr-name { font-weight: 600; }
.text-muted { color: #475569; }
.sr-price { font-weight: 800; color: #00f0ff; width: 100px; text-align: right; }

.btn-icon-remove {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 1.1rem;
}
.btn-icon-remove:hover { text-shadow: 0 0 5px #ef4444; }

.loading-state, .empty-parts {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
}

/* AI Results styling kept similar to before but with glassmorphism */
.ai-glass-panel { padding: 25px; }
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

/* LIGHT THEME OVERRIDES FOR BUILDER */
body.light-theme .glass-panel {
  background: rgba(255, 255, 255, 0.8);
  border-color: rgba(0, 0, 0, 0.1);
  color: #0f172a;
}
body.light-theme .synth-builder-container {
  color: #0f172a;
  background: #f1f5f9;
}
body.light-theme .category-item:hover { background: rgba(0,0,0,0.05); }
body.light-theme .category-item.active { background: rgba(0, 240, 255, 0.1); }
body.light-theme .card-desc, body.light-theme .spec-col span, body.light-theme .sr-cat { color: #64748b; }
body.light-theme .card-brand { background: rgba(0,0,0,0.05); color: #475569; }
body.light-theme .spec-col { color: #0f172a; }
body.light-theme .neon-price { color: #0284c7; text-shadow: none; }
body.light-theme .btn-neon { background: linear-gradient(90deg, #9333ea, #0284c7); }
body.light-theme .btn-neon-full { color: #0f172a; background: rgba(0,0,0,0.05); border-color: rgba(0,0,0,0.1); }
body.light-theme .btn-neon-full:hover { background: rgba(0,0,0,0.1); }

/* Builder Filters CSS */
.builder-filters {
  padding: 15px 20px;
  margin-bottom: 20px;
}

.builder-filters-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.search-input-wrapper { position: relative; display: flex; align-items: center; flex: 1; min-width: 200px; }
.search-input-wrapper input { background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px 15px 8px 35px; color: white; width: 100%; outline: none; font-size: 0.9rem; }
.search-input-wrapper input:focus { border-color: #3b82f6; }
.search-input-wrapper .icon { position: absolute; left: 10px; }

.price-inputs { display: flex; align-items: center; gap: 8px; }
.price-inputs input { width: 90px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 8px; border-radius: 6px; outline: none; font-size: 0.85rem; }
.price-inputs span { color: #64748b; }

.checkbox-label { display: flex; align-items: center; gap: 8px; color: #e2e8f0; cursor: pointer; font-size: 0.9rem; }
.checkbox-label input { accent-color: #3b82f6; width: 16px; height: 16px; }

.dynamic-filters-row {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 15px;
}

.filter-group { flex: 1; min-width: 150px; }
.filter-label-main { display: block; color: #94a3b8; font-size: 0.8rem; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }

.filter-input, .filter-select { width: 100%; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 8px; border-radius: 6px; outline: none; font-size: 0.85rem; }
.filter-input:focus, .filter-select:focus { border-color: #3b82f6; }
.filter-select option { background: #1a1b26; color: white; }

.checkbox-group-wrapper { display: flex; flex-direction: column; gap: 6px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); max-height: 180px; overflow-y: auto; }
.checkbox-group-wrapper::-webkit-scrollbar { width: 4px; }
.checkbox-group-wrapper::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 4px; }
.checkbox-group-wrapper .small-label { user-select: none; }

.reset-btn { margin-left: auto; }

/* PAGINATION */
.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 20px;
  margin-top: 25px;
  flex-wrap: wrap;
}

.page-btn {
  min-width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: #e2e8f0;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-btn:hover:not(:disabled):not(.active) {
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.3);
  color: #00f0ff;
}

.page-btn.active {
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.6), rgba(0, 240, 255, 0.6));
  border-color: transparent;
  color: white;
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.3);
  transform: scale(1.05);
}

.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-btn.ellipsis {
  border: none;
  background: none;
  cursor: default;
  color: #64748b;
  min-width: 30px;
}

.page-info {
  color: #64748b;
  font-size: 0.82rem;
  margin-left: 12px;
  white-space: nowrap;
}

body.light-theme .page-btn {
  background: rgba(0, 0, 0, 0.03);
  border-color: rgba(0, 0, 0, 0.1);
  color: #334155;
}
body.light-theme .page-btn:hover:not(:disabled):not(.active) {
  background: rgba(0, 240, 255, 0.08);
  color: #0284c7;
}
body.light-theme .page-btn.active {
  background: linear-gradient(135deg, #9333ea, #0284c7);
  color: white;
}

body.light-theme .builder-filters .search-input-wrapper input,
body.light-theme .builder-filters .price-inputs input,
body.light-theme .builder-filters .filter-input,
body.light-theme .builder-filters .filter-select,
body.light-theme .builder-filters .checkbox-group-wrapper {
  background: rgba(255,255,255,0.5);
  border-color: rgba(0,0,0,0.1);
  color: #0f172a;
}
</style>
