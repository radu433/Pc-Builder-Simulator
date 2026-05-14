<template>
  <div class="container products-page">
    <div class="page-header">
      <h1 class="category-title">{{ categoryName }}</h1>
      
      <div class="search-sort-bar">
        <div class="search-input-wrapper">
          <span class="icon">🔍</span>
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Caută componenta..." 
            @input="onFilterChange"
          />
        </div>
        
        <select v-model="sortBy" @change="onFilterChange" class="sort-select">
          <option value="">Sortează după...</option>
          <option value="pret">Preț crescător ↑</option>
          <option value="-pret">Preț descrescător ↓</option>
          <option value="nume">Nume A-Z</option>
        </select>
      </div>
    </div>

    <div class="layout-grid">
      <aside class="filters-panel">
        <h3>🎛️ Filtre Generale</h3>
        
        <div class="filter-group">
          <label class="filter-label-main">Preț (RON)</label>
          <div class="price-inputs">
            <input type="number" v-model="minPrice" placeholder="Min" @change="onFilterChange" />
            <span>-</span>
            <input type="number" v-model="maxPrice" placeholder="Max" @change="onFilterChange" />
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label-main">Disponibilitate</label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="inStockOnly" @change="onFilterChange" />
            Doar în stoc
          </label>
        </div>

        <h3 v-if="activeCategoryFilters.length" class="dynamic-filters-title">⚙️ Specificații</h3>
        
        <div v-for="filter in activeCategoryFilters" :key="filter.key" class="filter-group">
          <label class="filter-label-main">{{ filter.label }}</label>
          
          <select 
            v-if="filter.type === 'select'" 
            v-model="dynamicFilters[filter.key]" 
            @change="onFilterChange" 
            class="filter-select"
          >
            <option value="">Orice</option>
            <option v-for="opt in filter.options" :key="opt" :value="opt">{{ opt }}</option>
          </select>

          <div v-else-if="filter.type === 'checkbox-group'" class="checkbox-group-wrapper">
            <label v-for="opt in filter.options" :key="opt" class="checkbox-label small-label">
              <input 
                type="checkbox" 
                :value="opt" 
                v-model="dynamicFilters[filter.key]" 
                @change="onFilterChange" 
              />
              {{ opt }}
            </label>
          </div>

          <input 
            v-else 
            :type="filter.type" 
            v-model="dynamicFilters[filter.key]" 
            :placeholder="filter.placeholder" 
            @change="onFilterChange" 
            class="filter-input" 
          />
        </div>

        <div class="results-count" v-if="totalProducts > 0">
          {{ totalProducts }} produse găsite
        </div>

        <button class="reset-btn" @click="resetFilters">🔄 Resetare filtre</button>
      </aside>

      <main>
        <div v-if="loading" class="loading">⏳ Se încarcă produsele...</div>
        <div v-else-if="products.length === 0" class="no-results">
          😕 Nu s-au găsit produse cu aceste filtre.
        </div>
        
        <div v-else class="products-grid">
          <div 
            v-for="product in products" 
            :key="product.id"
            class="product-card"
          >
            <router-link :to="`/products/${route.params.category}/${product.id}`" class="card-link">
              <div class="card-img-wrapper">
                <img :src="product.imagine_url || 'https://placehold.co/200x200/1a1b26/3b82f6?text=No+Image'" :alt="product.nume" />
                <span v-if="product.stoc" class="badge-stock in-stock">În stoc</span>
                <span v-else class="badge-stock out-stock">Stoc epuizat</span>
              </div>
              <div class="card-info">
                <span class="brand">{{ product.brand }}</span>
                <h4 class="name">{{ product.nume }}</h4>
                <div class="price">{{ Number(product.pret).toLocaleString('ro-RO') }} RON</div>
              </div>
            </router-link>

            <div class="card-actions">
              <button 
                class="add-build-btn"
                :disabled="!product.stoc"
                @click="addToBuild(product)"
              >
                {{ currentAddedId === product.id ? '✅ Adăugat' : '➕ Adaugă în Build' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="totalPages > 1" class="pagination">
          <button class="page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">← Prev</button>
          <template v-for="page in visiblePages" :key="page">
            <span v-if="page === '...'" class="page-dots">...</span>
            <button v-else class="page-btn" :class="{ active: page === currentPage }" @click="goToPage(page)">{{ page }}</button>
          </template>
          <button class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">Next →</button>
        </div>
      </main>
    </div>

    <div v-if="toast" class="toast-notif">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../plugins/axios'

const route = useRoute()
const products = ref([])
const loading = ref(false)
const totalProducts = ref(0)
const currentPage = ref(1)
const PAGE_SIZE = 50

const searchQuery = ref('')
const minPrice = ref('')
const maxPrice = ref('')
const inStockOnly = ref(false)
const sortBy = ref('')

const currentAddedId = ref(null)
const toast = ref('')

// -- FILTRE DINAMICE --
const dynamicFilters = ref({})

// Configurația filtrelor specifice pentru fiecare categorie.
const categoryFiltersMap = {
  cpus: [
    { key: 'producator', label: 'Producător', type: 'select', options: ['AMD', 'Intel'] },
    { key: 'socket', label: 'Socket', type: 'checkbox-group', options: ['AM4', 'AM5', 'LGA 1700', 'LGA 1200', 'LGA 1151', 'LGA 1851'] },
  ],
  motherboards: [
    { key: 'socket', label: 'Socket', type: 'checkbox-group', options: ['AM4', 'AM5', 'LGA 1700', 'LGA 1200', 'LGA 1151', 'LGA 1851'] },
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
    { key: 'socket', label: 'Socket', type: 'checkbox-group', options: ['AM4', 'AM5', 'LGA 1700', 'LGA 1200', 'LGA 1151', 'LGA 1851'] },
    { key: 'tip_racire', label: 'Tip Răcire', type: 'select', options: ['Air', 'AIO 120mm', 'AIO 240mm', 'AIO 280mm', 'AIO 360mm'] }
  ]
}

const activeCategoryFilters = computed(() => {
  return categoryFiltersMap[route.params.category] || []
})

// Funcție care inițializează corect filtrele (ca string sau array gol pentru checkbox-uri)
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

const catToKeyMap = {
  'cpus': 'cpu', 'gpus': 'gpu', 'motherboards': 'motherboard',
  'rams': 'ram', 'storages': 'storage', 'psus': 'psu',
  'cases': 'case', 'coolers': 'cooler'
}

const checkCurrentBuild = () => {
  const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
  const key = catToKeyMap[route.params.category] || route.params.category
  currentAddedId.value = currentBuild[key]?.id || null
}

const categoryName = computed(() => {
  const map = {
    cpus: 'Procesoare (CPU)', gpus: 'Plăci Video (GPU)', rams: 'Memorie RAM',
    storages: 'Stocare', motherboards: 'Plăci de Bază', psus: 'Surse (PSU)',
    cases: 'Carcase', coolers: 'Răcire (Cooler)',
  }
  return map[route.params.category] || route.params.category?.toUpperCase()
})

const totalPages = computed(() => Math.ceil(totalProducts.value / PAGE_SIZE))

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value
  if (total <= 7) { for (let i = 1; i <= total; i++) pages.push(i) } 
  else {
    pages.push(1)
    if (current > 3) pages.push('...')
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i)
    if (current < total - 2) pages.push('...')
    pages.push(total)
  }
  return pages
})

const fetchProducts = async () => {
  loading.value = true
  try {
    const category = route.params.category
    const params = { page: currentPage.value, page_size: PAGE_SIZE }
    
    if (searchQuery.value) params.search = searchQuery.value
    if (minPrice.value) params.min_pret = minPrice.value
    if (maxPrice.value) params.max_pret = maxPrice.value
    if (inStockOnly.value) params.in_stock = 'true'
    if (sortBy.value) params.ordering = sortBy.value

    for (const [key, value] of Object.entries(dynamicFilters.value)) {
      if (Array.isArray(value)) {
        if (value.length > 0) {
          // Trimite array-ul ca un string separat prin virgulă (ex: AM4,AM5)
          params[key] = value.join(',')
        }
      } else if (value !== '' && value !== null && value !== undefined) {
        params[key] = value
      }
    }

    const response = await api.get(`${category}/`, { params })
    if (response.data.results !== undefined) {
      products.value = response.data.results
      totalProducts.value = response.data.count
    } else {
      products.value = response.data
      totalProducts.value = response.data.length
    }
  } catch (error) { console.error('Eroare:', error) } 
  finally { loading.value = false }
}

const onFilterChange = () => { currentPage.value = 1; fetchProducts() }

const goToPage = (page) => { 
  if (page < 1 || page > totalPages.value) return; 
  currentPage.value = page; 
  fetchProducts(); 
  window.scrollTo({ top: 0, behavior: 'smooth' }) 
}

const resetFilters = () => { 
  searchQuery.value = ''; 
  minPrice.value = ''; 
  maxPrice.value = ''; 
  inStockOnly.value = false; 
  sortBy.value = ''; 
  initDynamicFilters(); // Resetăm și restabilim starea inițială
  currentPage.value = 1; 
  fetchProducts() 
}

const addToBuild = (product) => {
  const category = route.params.category
  const key = catToKeyMap[category] || category
  const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
  
  currentBuild[key] = product
  localStorage.setItem('current_build', JSON.stringify(currentBuild))

  currentAddedId.value = product.id
  toast.value = `✅ ${product.nume} adăugat în build!`
  setTimeout(() => { toast.value = '' }, 3000)
}

watch(() => route.params.category, () => { 
  currentPage.value = 1; 
  initDynamicFilters();
  checkCurrentBuild();
  fetchProducts() 
})

onMounted(() => {
  initDynamicFilters();
  checkCurrentBuild();
  fetchProducts();
})
</script>

<style scoped>
.products-page { padding: 30px 15px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; flex-wrap: wrap; gap: 15px; }
.category-title { color: white; font-size: 2rem; font-weight: 800; }
.search-sort-bar { display: flex; gap: 15px; }
.search-input-wrapper { position: relative; display: flex; align-items: center; }
.search-input-wrapper input { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 8px; padding: 10px 15px 10px 35px; color: white; width: 250px; outline: none; font-size: 0.9rem; }
.search-input-wrapper input:focus { border-color: #3b82f6; }
.search-input-wrapper .icon { position: absolute; left: 10px; }
.sort-select { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 8px; padding: 10px 15px; color: white; outline: none; cursor: pointer; }
.layout-grid { display: grid; grid-template-columns: 250px 1fr; gap: 30px; }
.filters-panel { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 12px; padding: 20px; height: fit-content; position: sticky; top: 20px; }
.filters-panel h3 { color: white; margin-bottom: 20px; font-size: 1.1rem; }
.dynamic-filters-title { margin-top: 30px; border-top: 1px solid #2a2d3e; padding-top: 20px; }
.filter-group { margin-bottom: 20px; }
.filter-label-main { display: block; color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px; font-weight: 600; }

.filter-input, .filter-select { width: 100%; background: #0f111a; border: 1px solid #2a2d3e; color: white; padding: 10px; border-radius: 6px; outline: none; font-size: 0.85rem; box-sizing: border-box; }
.filter-input:focus, .filter-select:focus { border-color: #3b82f6; }
.filter-select option { background: #1a1b26; color: white; }

.checkbox-group-wrapper { display: flex; flex-direction: column; gap: 8px; background: #0f111a; padding: 12px; border-radius: 6px; border: 1px solid #2a2d3e; max-height: 180px; overflow-y: auto; }
.checkbox-group-wrapper::-webkit-scrollbar { width: 4px; }
.checkbox-group-wrapper::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 4px; }
.small-label { font-size: 0.85rem; }

.price-inputs { display: flex; align-items: center; gap: 8px; }
.price-inputs input { width: 100%; background: #0f111a; border: 1px solid #2a2d3e; color: white; padding: 8px; border-radius: 6px; outline: none; font-size: 0.85rem; }
.price-inputs span { color: #64748b; }
.checkbox-label { display: flex; align-items: center; gap: 8px; color: white !important; cursor: pointer; font-size: 0.9rem; }
.checkbox-label input { accent-color: #3b82f6; width: 16px; height: 16px; }
.results-count { color: #64748b; font-size: 0.8rem; margin-bottom: 15px; padding: 8px; background: #0f111a; border-radius: 6px; text-align: center; }
.reset-btn { width: 100%; background: transparent; color: #94a3b8; border: 1px solid #2a2d3e; padding: 10px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.reset-btn:hover { background: #3b82f6; color: white; border-color: #3b82f6; }
.products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px; }
.product-card { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 10px; overflow: hidden; transition: transform 0.2s, border-color 0.2s; display: flex; flex-direction: column; }
.product-card:hover { transform: translateY(-4px); border-color: #3b82f6; }
.card-link { text-decoration: none; flex: 1; }
.card-img-wrapper { position: relative; height: 180px; background: white; display: flex; align-items: center; justify-content: center; }
.card-img-wrapper img { max-width: 100%; max-height: 100%; object-fit: contain; padding: 15px; }
.badge-stock { position: absolute; top: 10px; right: 10px; padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white; }
.in-stock { background: #10b981; }
.out-stock { background: #f43f5e; }
.card-info { padding: 15px; }
.brand { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
.name { color: white; font-size: 0.95rem; margin: 5px 0 10px 0; line-height: 1.4; }
.price { color: #3b82f6; font-size: 1.2rem; font-weight: 800; }
.card-actions { padding: 0 15px 15px 15px; }
.add-build-btn { width: 100%; background: #3b82f6; color: white; border: none; padding: 10px; border-radius: 8px; font-size: 0.85rem; font-weight: 700; cursor: pointer; transition: background 0.2s; }
.add-build-btn:hover:not(:disabled) { background: #2563eb; }
.add-build-btn:disabled { background: #3f4455; cursor: not-allowed; color: #94a3b8; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 20px 0; flex-wrap: wrap; }
.page-btn { background: #1a1b26; border: 1px solid #2a2d3e; color: #a9b1d6; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 600; transition: all 0.15s; min-width: 40px; }
.page-btn:hover:not(:disabled) { background: #232533; color: white; border-color: #3b82f6; }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn.active { background: #3b82f6; border-color: #3b82f6; color: white; }
.page-dots { color: #64748b; padding: 0 4px; }
.loading, .no-results { text-align: center; color: #94a3b8; padding: 60px 20px; font-size: 1.1rem; }
.toast-notif { position: fixed; bottom: 30px; right: 30px; background: #1a1b26; border: 1px solid #10b981; color: white; padding: 14px 22px; border-radius: 8px; font-weight: 600; box-shadow: 0 10px 25px rgba(0,0,0,0.4); z-index: 9999; animation: slideIn 0.3s ease-out; }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
</style>