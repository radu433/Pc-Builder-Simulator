<template>
  <div class="container detail-page">
    <div v-if="loading" class="loading">Se încarcă detaliile...</div>
    
    <div v-else-if="product" class="product-layout">
      <div class="image-section">
        <div class="main-image">
          <img :src="product.imagine_url || 'https://via.placeholder.com/400'" :alt="product.nume" />
        </div>
      </div>

      <div class="info-section">
        <div class="brand-badge">{{ product.brand }}</div>
        <h1 class="product-name">{{ product.nume }}</h1>
        
        <div class="status-row">
          <span v-if="product.stoc" class="status in-stock">✅ În stoc</span>
          <span v-else class="status out-stock">❌ Stoc epuizat</span>
          <span class="part-number">PN: {{ product.part_number || 'N/A' }}</span>
        </div>

        <div class="price-box">
          <div class="price">{{ product.pret }} RON</div>
          <div class="action-buttons">
            <button class="add-btn" :disabled="!product.stoc" @click="addToBuild">
              <span class="icon">➕</span> {{ isAdded ? '✅ Adăugat' : 'Adaugă în Build' }}
            </button>
            <a v-if="product.url_produs" :href="product.url_produs" target="_blank" class="buy-btn">
              🛒 Cumpără ({{ product.magazin || 'Magazin' }})
            </a>
          </div>
        </div>

        <div v-if="product.magazin" class="store-link">
          Disponibil la: <a :href="product.url_produs" target="_blank">{{ product.magazin }} ↗</a>
        </div>

        <div class="specs-card">
          <h3>Specificații Tehnice</h3>
          <div class="specs-grid">
            <div class="spec-row" v-if="product.socket">
              <span class="spec-label">Socket:</span>
              <span class="spec-value">{{ product.socket }}</span>
            </div>
            <div class="spec-row" v-if="product.nuclee">
              <span class="spec-label">Nuclee/Thread-uri:</span>
              <span class="spec-value">{{ product.nuclee }} / {{ product.threaduri }}</span>
            </div>
            <div class="spec-row" v-if="product.frecventa_ghz">
              <span class="spec-label">Frecvență:</span>
              <span class="spec-value">{{ product.frecventa_ghz }} GHz</span>
            </div>
            <div class="spec-row" v-if="product.consum_tdp">
              <span class="spec-label">Consum (TDP):</span>
              <span class="spec-value">{{ product.consum_tdp }} W</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast-notif">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../plugins/axios'

const route = useRoute()
const product = ref(null)
const loading = ref(true)
const toast = ref('')
const isAdded = ref(false)

const catToKeyMap = {
  'cpus': 'cpu', 'gpus': 'gpu', 'motherboards': 'motherboard',
  'rams': 'ram', 'storages': 'storage', 'psus': 'psu',
  'cases': 'case', 'coolers': 'cooler'
}

const checkCurrentBuild = () => {
  if (!product.value) return;
  const key = catToKeyMap[route.params.category] || route.params.category
  const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
  
  if (currentBuild[key] && currentBuild[key].id != null && currentBuild[key].id === product.value.id) {
    isAdded.value = true
  } else {
    isAdded.value = false
  }
}

const fetchProductDetail = async () => {
  try {
    const category = route.params.category
    const id = route.params.id
    const response = await api.get(`${category}/${id}/`)
    product.value = response.data
    checkCurrentBuild()
  } catch (error) { console.error(error) } 
  finally { loading.value = false }
}

const addToBuild = () => {
  if (!product.value) return
  const category = route.params.category
  const key = catToKeyMap[category] || category
 const currentBuild = JSON.parse(localStorage.getItem('current_build') || '{}')
if (product.value && product.value.id != null) {
  currentBuild[key] = product.value
} else {
  delete currentBuild[key]
}
localStorage.setItem('current_build', JSON.stringify(currentBuild))
  isAdded.value = true
  toast.value = `✅ ${product.value.nume} adăugat în build!`
  setTimeout(() => { toast.value = '' }, 3000)
}

onMounted(fetchProductDetail)
</script>

<style scoped>
/* =========== CYBERPUNK MOCKUP 1:1 UI =========== */
.detail-page { padding: 40px 15px; display: flex; justify-content: center; font-family: 'Inter', sans-serif; }
.product-layout { 
  display: grid; grid-template-columns: 1fr 1fr; gap: 40px; 
  background: #111520;
  border: 1px solid rgba(34, 211, 238, 0.3);
  border-radius: 16px;
  padding: 40px;
  max-width: 1000px;
  width: 100%;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
}

.main-image { 
  background: #1a1e2b; border-radius: 12px; padding: 40px; display: flex; justify-content: center; align-items: center; 
  border: 1px solid rgba(255,255,255,0.05); height: 100%; 
}
.main-image img { max-width: 100%; max-height: 400px; object-fit: contain; filter: drop-shadow(0 20px 30px rgba(0,0,0,0.6)); transition: transform 0.3s; }
.main-image img:hover { transform: scale(1.05); }

.brand-badge { display: inline-block; background: #1a1e2b; color: #94a3b8; padding: 6px 14px; border-radius: 6px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; font-size: 0.85rem; margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.1); }
.product-name { color: white; font-size: 2.2rem; font-weight: 800; line-height: 1.2; margin-bottom: 20px; }

.status-row { display: flex; gap: 20px; margin-bottom: 30px; font-size: 0.95rem; background: #1a1e2b; padding: 10px 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); width: fit-content; }
.status { font-weight: 700; }
.in-stock { color: #10b981; }
.out-stock { color: #ef4444; }
.part-number { color: #94a3b8; }

.price-box { background: #1a1e2b; border: 1px solid rgba(255,255,255,0.1); padding: 30px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
.price-box .price { color: #22d3ee; font-size: 2.2rem; font-weight: 900; }

.action-buttons { display: flex; flex-direction: column; gap: 12px; }
.add-btn { background: #10b981; color: white; border: none; padding: 15px 30px; border-radius: 8px; font-size: 1.1rem; font-weight: 800; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: 0.3s; text-transform: uppercase; }
.add-btn:hover:not(:disabled) { background: #059669; transform: translateY(-2px); }
.add-btn:disabled { background: #1a1e2b; cursor: not-allowed; color: #64748b; border: 1px solid rgba(255,255,255,0.1); }

.buy-btn { background: #1a1e2b; border: 1px solid rgba(255,255,255,0.1); color: #d8b4fe; text-decoration: none; padding: 12px 15px; border-radius: 8px; font-size: 0.95rem; font-weight: 700; text-align: center; display: block; transition: 0.3s; }
.buy-btn:hover { border-color: #d8b4fe; color: white; }

.store-link { color: #94a3b8; margin-bottom: 30px; font-size: 0.95rem; text-align: right; }
.store-link a { color: #d946ef; text-decoration: none; font-weight: 700; transition: 0.2s; }
.store-link a:hover { color: #c026d3; }

.specs-card { background: #1a1e2b; border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 25px; }
.specs-card h3 { color: #d946ef; margin-bottom: 20px; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 800; }
.specs-grid { display: flex; flex-direction: column; gap: 12px; }
.spec-row { display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 12px; }
.spec-label { color: #94a3b8; font-size: 0.95rem; }
.spec-value { color: white; font-weight: 600; font-size: 0.95rem; }

.toast-notif { position: fixed; bottom: 30px; right: 30px; background: #10b981; color: white; padding: 16px 24px; border-radius: 8px; font-weight: 700; box-shadow: 0 10px 30px rgba(0,0,0,0.5); z-index: 9999; animation: slideIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); border: 1px solid rgba(255,255,255,0.2); }
@keyframes slideIn { from { transform: translateX(100%) scale(0.9); opacity: 0; } to { transform: translateX(0) scale(1); opacity: 1; } }

@media (max-width: 768px) { .product-layout { grid-template-columns: 1fr; } }
</style>
