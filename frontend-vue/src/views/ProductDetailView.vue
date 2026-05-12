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
          <button class="add-btn" :disabled="!product.stoc" @click="addToBuild">
            <span class="icon">➕</span> {{ isAdded ? '✅ Adăugat' : 'Adaugă în Build' }}
          </button>
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
  
  if (currentBuild[key] && currentBuild[key].id === product.value.id) {
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
  currentBuild[key] = product.value
  localStorage.setItem('current_build', JSON.stringify(currentBuild))

  isAdded.value = true
  toast.value = `✅ ${product.value.nume} adăugat în build!`
  setTimeout(() => { toast.value = '' }, 3000)
}

onMounted(fetchProductDetail)
</script>

<style scoped>
.detail-page { padding: 40px 15px; }
.product-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 50px; }
.main-image { background: white; border-radius: 12px; padding: 40px; display: flex; justify-content: center; align-items: center; border: 1px solid #2a2d3e; height: 100%; }
.main-image img { max-width: 100%; max-height: 400px; object-fit: contain; }
.brand-badge { display: inline-block; background: #232533; color: #3b82f6; padding: 6px 12px; border-radius: 6px; font-weight: 700; letter-spacing: 1px; font-size: 0.85rem; margin-bottom: 15px; }
.product-name { color: white; font-size: 2.5rem; line-height: 1.2; margin-bottom: 20px; }
.status-row { display: flex; gap: 20px; margin-bottom: 30px; font-size: 0.9rem; }
.status { font-weight: 600; }
.in-stock { color: #10b981; }
.out-stock { color: #f43f5e; }
.part-number { color: #64748b; }
.price-box { background: #1a1b26; border: 1px solid #2a2d3e; padding: 30px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.price-box .price { color: white; font-size: 2rem; font-weight: 800; }
.add-btn { background: #3b82f6; color: white; border: none; padding: 15px 30px; border-radius: 8px; font-size: 1.1rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: background 0.2s; }
.add-btn:hover:not(:disabled) { background: #2563eb; }
.add-btn:disabled { background: #3f4455; cursor: not-allowed; color: #94a3b8; }
.store-link { color: #94a3b8; margin-bottom: 30px; font-size: 0.95rem; }
.store-link a { color: #3b82f6; text-decoration: none; font-weight: 600; }
.specs-card { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 12px; padding: 30px; }
.specs-card h3 { color: white; margin-bottom: 20px; font-size: 1.3rem; }
.specs-grid { display: flex; flex-direction: column; gap: 15px; }
.spec-row { display: flex; justify-content: space-between; border-bottom: 1px solid #2a2d3e; padding-bottom: 10px; }
.spec-label { color: #94a3b8; }
.spec-value { color: white; font-weight: 500; }
.toast-notif { position: fixed; bottom: 30px; right: 30px; background: #1a1b26; border: 1px solid #10b981; color: white; padding: 14px 22px; border-radius: 8px; font-weight: 600; box-shadow: 0 10px 25px rgba(0,0,0,0.4); z-index: 9999; animation: slideIn 0.3s ease-out; }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
</style>