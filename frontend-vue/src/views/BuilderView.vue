<template>
  <div class="maximalist-app-container">
    <!-- Overlay pentru textura de zgomot (Dithering) -->
    <div class="noise-texture"></div>

    <!-- SIDEBAR -->
    <aside class="sidebar glass-panel">
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
        </div>
        <span class="font-syne gradient-text-brand">RIGMASTER</span>
      </div>
      
      <div class="sidebar-scroll-area">
        <div class="category-list">
          <div v-for="(cat, idx) in categories" :key="cat.id" 
               class="category-item" 
               :class="{ active: activeCategoryId === cat.id, 'has-part': cat.selectedPart }"
               @click="openCategory(cat.id)">
               <div class="cat-left">
                 <span class="cat-icon">{{ cat.icon }}</span>
                 <span class="cat-name font-inter">{{ cat.name }}</span>
               </div>
               <span class="status-indicator"></span>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
         <button class="btn-ghost-outline font-inter" @click="openCategory(null)">
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line></svg>
           View Summary
         </button>
         
         <button class="btn-primary-green font-mono" @click="openSaveModal" :disabled="selectedPartsCount === 0">
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
           SAVE BUILD
         </button>
         
         <button class="btn-primary-violet font-mono" @click="analizeazaBuild" :disabled="selectedPartsCount === 0 || agentLoading">
           <svg v-if="!agentLoading" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
           <svg v-else class="spin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
           {{ agentLoading ? 'ANALYZING...' : 'AI ANALYSIS' }}
         </button>

         <div class="ai-sub-actions">
           <button class="btn-ai-sub font-mono" @click="triggerBottleneck">BOTTLENECK CHECK</button>
           <button class="btn-ai-sub font-mono" @click="triggerFps">ESTIMATE FPS</button>
           <button class="btn-ai-sub font-mono" @click="triggerCasePreview">CASE PREVIEW</button>
         </div>
      </div>
    </aside>
    
    <!-- MAIN CONTENT -->
    <main class="main-content">
       <!-- HERO HEADER -->
       <div class="hero-header glass-panel">
           <div class="hero-bg-animated"></div>
           <div class="hero-content">
             <div>
               <h1 class="font-syne hero-title">{{ activeCategory ? activeCategory.name.toUpperCase() + ' SELECTION' : 'SYSTEM SUMMARY' }}</h1>
               <div class="badges-row font-inter">
                 <span class="badge-status" :class="hasIncompatibilities ? 'error' : 'success'">
                   <span class="dot"></span> {{ hasIncompatibilities ? 'Compatibility Issues' : '100% Compatible' }}
                 </span>
                 <span class="badge-status info">
                   <span class="dot"></span> {{ selectedPartsCount }} Components Selected
                 </span>
               </div>
             </div>
             
             <div class="price-display">
               <div class="price-label font-inter">ESTIMATED TOTAL</div>
               <div class="price-value font-mono gradient-text-green">{{ totalPrice.toFixed(2) }} <span class="currency">RON</span></div>
               <div class="tdp-value font-mono">PWR DRAIN: {{ totalTdp }}W</div>
             </div>
           </div>
       </div>

       <!-- LOADING STATE -->
       <div v-if="loading" class="loading-state glass-panel">
          <div class="spinner-hologram"></div>
          <p class="font-mono gradient-text-cyan">INITIALIZING DATABASE...</p>
       </div>

       <!-- BROWSING GRID (Când o categorie este selectată) -->
       <div v-else-if="activeCategoryId" class="components-grid">
          <div 
            v-for="part in activeCategoryParts" 
            :key="part.id"
            class="synth-product-card glass-panel interactive-card"
          >
            <div class="card-link" style="cursor: pointer;" @click="selectPart(part)">
              <div class="card-glow"></div>
              <div class="card-content">
                <div class="card-top">
                  <div class="card-brand">{{ part.brand || part.producator || 'N/A' }}</div>
                </div>
                
                <div class="card-image-box">
                  <img :src="part.imagine_url || 'https://placehold.co/200x200/111827/00f0ff?text=No+Image'" :alt="part.nume || part.name" />
                </div>
                
                <h3 class="card-title">{{ part.nume || part.name }}</h3>
                <div class="card-specs">
                  <div class="spec-col">
                    <span class="neon-price">{{ Number(part.pret || part.price).toLocaleString('ro-RO') }} RON</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="card-footer">
              <button 
                class="btn-neon"
                @click="selectPart(part)"
                style="width: 100%"
              >
                ➕ Adaugă în Build
              </button>
            </div>
          </div>
       </div>

       <!-- SUMMARY VIEW -->
       <div v-else class="summary-layout">
           <!-- COLOANA STÂNGA -->
           <div class="col-left">
             
             <!-- PC Visual Preview -->
             <div class="pc-preview-card glass-panel interactive-card">
               <div class="pc-hologram" v-if="!generatedImageUrl && !imageGenerationErrorText">
                  <div class="holo-core"></div>
                  <div class="holo-rings"></div>
               </div>
               <div class="pc-preview-error font-inter text-center" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #8b9db5; padding: 20px;" v-else-if="imageGenerationErrorText">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mb-4 text-red-500" style="opacity: 0.8"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                  <p>{{ imageGenerationErrorText }}</p>
               </div>
               <div v-else class="generated-image-container">
                  <img :src="generatedImageUrl" class="generated-preview-img" alt="PC Build" />
                  <button class="btn-enlarge font-mono" @click="showImageModal = true">ENLARGE</button>
               </div>
               <div class="pc-preview-label font-mono">CASE PREVIEW {{ generatedImageUrl ? '[GENERATED]' : (imageGenerationErrorText ? '[UNAVAILABLE]' : '[SIMULATED]') }}</div>
             </div>

             <!-- Bottleneck Analysis -->
             <div class="bottleneck-panel glass-panel">
               <h3 class="panel-title font-syne" :style="{ marginBottom: showBottleneck ? '1.5rem' : '0', borderBottom: showBottleneck ? '' : 'none', paddingBottom: showBottleneck ? '1rem' : '0', transition: 'all 0.4s' }">BOTTLENECK ANALYSIS</h3>
               
               <Transition name="expand">
                 <div v-if="showBottleneck">
                   <div v-if="loadingBottleneck" class="loading-state-small">
                     <div class="spinner-hologram small-spinner"></div>
                     <p class="font-mono gradient-text-cyan">ANALYZING BOTTLENECK...</p>
                   </div>

                   <div class="bottleneck-list">
                     <div class="progress-item" v-for="stat in bottleneckStats" :key="stat.label">
                       <div class="progress-header font-inter">
                         <span>{{ stat.label }}</span>
                         <span class="font-mono" :class="stat.color">{{ stat.value }}%</span>
                       </div>
                       <div class="progress-track">
                         <div class="progress-fill" :style="{ width: stat.value + '%', background: stat.bg }"></div>
                       </div>
                     </div>
                   </div>
                 </div>
               </Transition>
             </div>

             <!-- Gaming FPS Table -->
             <div class="fps-panel glass-panel">
               <h3 class="panel-title font-syne" :style="{ marginBottom: showFps ? '1.5rem' : '0', borderBottom: showFps ? '' : 'none', paddingBottom: showFps ? '1rem' : '0', transition: 'all 0.4s' }">FPS ESTIMATES <span class="badge-ultra">ULTRA SETTINGS</span></h3>
               
               <Transition name="expand">
                 <div v-if="showFps">
                   <div v-if="loadingFps" class="loading-state-small">
                     <div class="spinner-hologram small-spinner"></div>
                     <p class="font-mono gradient-text-violet">SIMULATING FPS...</p>
                   </div>

                   <div v-else class="table-responsive">
                     <table class="fps-table font-mono">
                       <thead>
                         <tr>
                           <th>GAME TITLE</th>
                           <th>1080P</th>
                           <th>1440P</th>
                           <th>4K</th>
                         </tr>
                       </thead>
                       <tbody>
                         <tr v-for="game in fpsEstimates" :key="game.name">
                           <td class="font-inter game-title">{{ game.name }}</td>
                           <td class="fps-high">{{ game.fhd }}</td>
                           <td class="fps-med">{{ game.qhd }}</td>
                           <td class="fps-low">{{ game.uhd }}</td>
                         </tr>
                       </tbody>
                     </table>
                   </div>
                 </div>
               </Transition>
             </div>
           </div>

           <!-- COLOANA DREAPTA -->
           <div class="col-right">
             
             <!-- Build List -->
              <div class="build-list-panel glass-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 0.8rem;">
                  <h3 class="panel-title font-syne" style="margin-bottom: 0; padding-bottom: 0; border: none;">SELECTED COMPONENTS</h3>
                  <button v-if="selectedPartsCount > 0" class="btn-clear-all font-mono" @click="clearAllParts" title="Clear All Components">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    CLEAR
                  </button>
                </div>
               <div class="build-items-container">
                 
                 <!-- Empty state -->
                 <div v-if="selectedPartsCount === 0" class="empty-state font-inter">
                   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                   <p>No components selected. Start building your rig from the dashboard.</p>
                 </div>

                 <!-- Items -->
                 <div v-for="cat in categories.filter(c => c.selectedPart)" :key="cat.id" class="build-item">
                   <div class="item-icon">{{ cat.icon }}</div>
                    <div class="build-item-info">
                      <h4 class="font-inter">{{ cat.selectedPart.nume || cat.selectedPart.name }}</h4>
                      <p class="font-mono text-sm opacity-70">{{ cat.selectedPart.pret || cat.selectedPart.price }} RON</p>
                    </div>
                   <div class="item-actions">
                     <span class="item-price font-mono">{{ cat.selectedPart.price }} RON</span>
                     <button class="btn-swap" @click="openAlternativesModal(cat)" title="Find Alternatives">
                       <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><polyline points="23 20 23 14 17 14"></polyline><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path></svg>
                     </button>
                     <button class="btn-remove" @click="removePart(cat.id)" title="Remove">✕</button>
                   </div>
                 </div>

               </div>
             </div>

           </div>
       </div>
    </main>

    <!-- ========================================== -->
    <!-- MODAL 1: SALVEAZĂ BUILD (Teleported)       -->
    <!-- ========================================== -->
    <Teleport to="body">
      <div v-if="showSaveModal" class="modal-overlay" @click.self="showSaveModal = false">
        <div class="maximalist-modal glass-panel">
          <div class="modal-header">
            <h2 class="font-syne gradient-text-violet">SAVE CONFIGURATION</h2>
            <button class="btn-close" @click="showSaveModal = false">✕</button>
          </div>
          
          <div class="modal-body font-inter">
            <div class="input-group">
              <label for="build-name" class="font-mono">BUILD DESIGNATION</label>
              <input 
                id="build-name" 
                type="text" 
                v-model="newBuildName" 
                class="synth-input font-inter" 
                placeholder="e.g. CyberBeast MK.II" 
              />
            </div>

            <div class="save-options-row glass-panel-inner">
              <div class="toggle-container">
                <label class="synth-switch">
                  <input type="checkbox" v-model="isPublic" />
                  <span class="slider round"></span>
                </label>
                <span class="toggle-label font-mono">PUBLIC BUILD</span>
              </div>

              <div class="user-profile-badge">
                <div class="avatar-circle font-syne">R</div>
                <span class="username font-mono">radut202...</span>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-ghost font-mono" @click="showSaveModal = false">ABORT</button>
            <button class="btn-primary-cyan font-mono" @click="confirmSave">SAVE</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ========================================== -->
    <!-- MODAL 2: ALTERNATIVE (Teleported)          -->
    <!-- ========================================== -->
    <Teleport to="body">
      <div v-if="showAlternativesModal" class="modal-overlay" @click.self="showAlternativesModal = false">
        <div class="maximalist-modal modal-large glass-panel">
          <div class="modal-header">
            <h2 class="font-syne gradient-text-cyan">AI ALTERNATIVES FOR {{ modalTargetCategory?.name.toUpperCase() }}</h2>
            <button class="btn-close" @click="showAlternativesModal = false">✕</button>
          </div>
          
          <div class="modal-body">
            <div class="alternatives-grid">
              
              <div v-for="alt in alternatives" :key="alt.id" class="alt-card glass-panel-inner interactive-card">
                <div class="alt-header-container mb-2">
                  <div class="text-xs text-purple-400 font-bold tracking-wider mb-2 font-syne">{{ alt.tip_alternativa }}</div>
                  <div class="alt-header">
                    <span class="alt-icon">{{ modalTargetCategory?.icon }}</span>
                    <h4 class="font-inter">{{ alt.name }}</h4>
                  </div>
                </div>
                <div class="alt-price font-mono gradient-text-cyan">{{ alt.price }} RON</div>
                <p class="alt-reason font-inter">{{ alt.reason }}</p>
                <button class="btn-primary-cyan font-mono" @click="swapComponent(alt)">
                  ÎNLOCUIEȘTE
                </button>
              </div>

            </div>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- MODAL 3: AI ANALYSIS (Teleported) -->
    <Teleport to="body">
      <div v-if="showAnalysisModal" class="modal-overlay" @click.self="showAnalysisModal = false">
        <div class="maximalist-modal glass-panel">
          <div class="modal-header">
            <h2 class="font-syne gradient-text-cyan">AI COMPATIBILITY ANALYSIS</h2>
            <button class="btn-close" @click="showAnalysisModal = false">✕</button>
          </div>
          <div class="modal-body font-inter">
            <div v-if="analysisResult.length === 0" class="flex flex-col items-center text-center">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#00e5ff" stroke-width="2" class="mb-4">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              <h3 class="text-xl text-white mb-2">Build 100% Compatibil!</h3>
              <p class="text-gray-400">Toate componentele selectate se potrivesc perfect. Nicio problemă detectată.</p>
            </div>
            
            <div v-else>
              <h3 class="text-xl text-red-400 mb-4 font-syne">⚠️ Probleme Detectate ({{ analysisResult.length }})</h3>
              <ul class="space-y-3">
                <li v-for="(prob, idx) in analysisResult" :key="idx" class="glass-panel-inner p-3 border border-red-500/30 text-gray-200 flex items-start gap-3">
                  <span class="text-red-500">❌</span>
                  {{ prob }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modal imagine generată -->
    <Teleport to="body">
      <div v-if="showImageModal" class="modal-overlay" @click.self="showImageModal = false">
        <div class="image-modal glass-panel">
          <button class="btn-close" @click="showImageModal = false">✕</button>
          <img :src="generatedImageUrl" class="full-size-img" alt="PC Build Full" />
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/plugins/axios'
import { showToast } from '@/toast'

// --- STILURI IMPORTATE (Google Fonts) ---
// Notă: Folosim o injecție a fonturilor direct din componentă pentru a garanta aspectul.
const fontStyle = document.createElement('style');
fontStyle.innerHTML = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&family=Syne:wght@600;700;800&display=swap');
`;
document.head.appendChild(fontStyle);

// --- STATE MANAGEMENT ---
const activeCategoryId = ref(null)
const loading = ref(false)
const agentLoading = ref(false)

// Panels State
const showBottleneck = ref(false)
const loadingBottleneck = ref(false)
const showFps = ref(false)
const loadingFps = ref(false)

// Modals State
const showSaveModal = ref(false)
const showAlternativesModal = ref(false)
const showAnalysisModal = ref(false)
const analysisResult = ref([])
const newBuildName = ref('')
const isPublic = ref(true)
const modalTargetCategory = ref(null)

// --- DATA STATE ---
const categories = ref([
  { id: 'cpu', endpoint: 'cpus', name: 'Procesor',selectedPart: null },
  { id: 'gpu', endpoint: 'gpus', name: 'Placă Video',selectedPart: null },
  { id: 'motherboard', endpoint: 'motherboards', name: 'Placă de Bază',selectedPart: null },
  { id: 'ram', endpoint: 'rams', name: 'Memorie RAM',selectedPart: null },
  { id: 'storage', endpoint: 'storages', name: 'Stocare',selectedPart: null },
  { id: 'psu', endpoint: 'psus', name: 'Sursă',selectedPart: null },
  { id: 'case', endpoint: 'cases', name: 'Carcasă',selectedPart: null },
  { id: 'cooler', endpoint: 'coolers', name: 'Cooler', selectedPart: null },
])

const activeCategoryParts = ref([])
const bottleneckStats = ref([])
const fpsEstimates = ref([])
const alternatives = ref([])

const generatedImageUrl = ref(null)
const imageGenerationErrorText = ref(null)
const showImageModal = ref(false)

const isLoggedIn = ref(false)
const imageGenerationsCount = ref(0)

const saveCurrentBuildToStorage = () => {
  const build = {}
  categories.value.forEach(cat => {
    if (cat.selectedPart) {
      build[cat.id] = cat.selectedPart
    }
  })
  localStorage.setItem('current_build', JSON.stringify(build))
}

onMounted(() => {
  const token = localStorage.getItem('access_token');
  isLoggedIn.value = !!token;
  const storedCount = localStorage.getItem('image_generations_count');
  if (storedCount) {
    imageGenerationsCount.value = parseInt(storedCount);
  }
  
  // 1. Verificăm dacă venim din SavedBuildsView cu un "loadBuild"
  const loadBuildStr = sessionStorage.getItem('loadBuild');
  if (loadBuildStr) {
    try {
      const parts = JSON.parse(loadBuildStr);
      categories.value.forEach(cat => {
        if (parts[cat.id]) {
          cat.selectedPart = parts[cat.id];
        }
      });
      saveCurrentBuildToStorage(); // suprascriem current_build-ul cu cel încărcat
    } catch (e) {
      console.error("Eroare la încărcarea build-ului salvat:", e);
    }
    sessionStorage.removeItem('loadBuild');
  } else {
    // 2. Altfel, încărcăm ultimul build la care se lucra
    const currentBuildStr = localStorage.getItem('current_build');
    if (currentBuildStr) {
      try {
        const parts = JSON.parse(currentBuildStr);
        categories.value.forEach(cat => {
          if (parts[cat.id]) {
            cat.selectedPart = parts[cat.id];
          }
        });
      } catch (e) {
        console.error("Eroare la citirea current_build:", e);
      }
    }
  }
})

// --- COMPUTED ---
const activeCategory = computed(() => categories.value.find(c => c.id === activeCategoryId.value))
const selectedPartsCount = computed(() => categories.value.filter(c => c.selectedPart).length)
const totalPrice = computed(() => categories.value.reduce((acc, cat) => acc + parseFloat(cat.selectedPart?.pret || cat.selectedPart?.price || 0), 0))
const totalTdp = computed(() => selectedPartsCount.value * 75) // Mock calcul
const hasIncompatibilities = computed(() => false) // Mock state

// --- METHODS ---
const openCategory = async (id) => {
  activeCategoryId.value = id
  if (id) {
    loading.value = true
    try {
      const cat = categories.value.find(c => c.id === id)
      if (cat && cat.endpoint) {
        const response = await api.get(`/${cat.endpoint}/`)
        activeCategoryParts.value = response.data.results !== undefined ? response.data.results : response.data
      }
    } catch (err) {
      showToast('Eroare la încărcarea componentelor', 'error')
      activeCategoryParts.value = []
    } finally {
      loading.value = false
    }
  }
}

const selectPart = (part) => {
  const cat = categories.value.find(c => c.id === activeCategoryId.value)
  if(cat) {
    cat.selectedPart = part
    saveCurrentBuildToStorage()
  }
  activeCategoryId.value = null // Întoarcere la summary
}

const removePart = (id) => {
  const cat = categories.value.find(c => c.id === id)
  if(cat) {
    cat.selectedPart = null
    saveCurrentBuildToStorage()
  }
}

const clearAllParts = () => {
  categories.value.forEach(cat => {
    cat.selectedPart = null
  })
  saveCurrentBuildToStorage()
}

const openSaveModal = () => showSaveModal.value = true
const confirmSave = async () => {
  if (!isLoggedIn.value) {
    showToast('Trebuie să fii conectat pentru a salva!', 'error')
    return
  }

  const payload = {
    nume: newBuildName.value || undefined,
  }

  categories.value.forEach(cat => {
    if (cat.selectedPart) {
      payload[cat.id] = cat.selectedPart.id
    }
  })

  try {
    const response = await api.post('/saved-builds/', payload)
    showToast('Build salvat cu succes!', 'success')
    showSaveModal.value = false
  } catch (error) {
    showToast('Eroare la salvarea build-ului', 'error')
    console.error(error)
  }
}

const analizeazaBuild = async () => {
  const buildPayload = {}
  categories.value.forEach(cat => {
    if (cat.selectedPart) {
      buildPayload[cat.id] = cat.selectedPart
    }
  })

  if (Object.keys(buildPayload).length === 0) {
    showToast('Nu ai selectat nicio componentă pentru analiză.', 'error')
    return
  }

  agentLoading.value = true
  
  try {
    const response = await api.post('/builder/compatibility/', {
      build: buildPayload
    })
    
    analysisResult.value = response.data.probleme || []
    showAnalysisModal.value = true
  } catch (err) {
    showToast('Eroare la analiza build-ului', 'error')
  } finally {
    agentLoading.value = false
  }
}

const openAlternativesModal = async (cat) => {
  if (!cat.selectedPart) {
    showToast('Te rog să selectezi o componentă mai întâi.', 'error')
    return
  }
  
  modalTargetCategory.value = cat
  showAlternativesModal.value = true
  alternatives.value = [] // clear loading state
  
  try {
    const response = await api.post('/builder/alternatives/', {
      component_type: cat.id,
      component_id: cat.selectedPart.id,
      limit: 3
    })
    
    if (response.data.alternative) {
      alternatives.value = response.data.alternative.map(alt => ({
        id: alt.id,
        name: alt.nume,
        price: alt.pret,
        reason: `Performanță: +${alt.diferenta_performanta_procent}% | Economie: ${alt.economie_ron} RON (${alt.magazin})`,
        ...alt
      }))
    } else {
      showToast(response.data.error || 'Nicio alternativă găsită.', 'error')
    }
  } catch (err) {
    showToast('Eroare la obținerea alternativelor.', 'error')
  }
}

const swapComponent = (alt) => {
  if(modalTargetCategory.value) {
    modalTargetCategory.value.selectedPart = {
      id: alt.id,
      nume: alt.name || alt.nume,
      pret: alt.price || alt.pret,
      magazin: alt.magazin,
      url_produs: alt.url_produs || alt.url,
      // mapping extra
    }
  }
  showAlternativesModal.value = false
}

const triggerBottleneck = async () => {
  const cpu = categories.value.find(c => c.id === 'cpu')?.selectedPart
  const gpu = categories.value.find(c => c.id === 'gpu')?.selectedPart
  if (!cpu || !gpu) {
    showToast('Te rog să selectezi un CPU și un GPU pentru analiză!', 'error')
    return
  }
  
  showBottleneck.value = true;
  loadingBottleneck.value = true;
  
  try {
    const response = await api.post('/builder/bottleneck/', {
      cpu_id: cpu.id,
      gpu_id: gpu.id
    })
    const data = response.data
    bottleneckStats.value = [
      { label: 'SCOR CPU', value: Math.min(100, Math.round((data.scor_cpu / Math.max(data.scor_cpu, data.scor_gpu)) * 100)), color: 'text-cyan', bg: 'linear-gradient(90deg, #00e5ff, #3b82f6)' },
      { label: 'SCOR GPU', value: Math.min(100, Math.round((data.scor_gpu / Math.max(data.scor_cpu, data.scor_gpu)) * 100)), color: 'text-violet', bg: 'linear-gradient(90deg, #7c3aed, #ec4899)' },
      { label: 'BOTTLENECK', value: data.procentaj_bottleneck, color: 'text-red', bg: 'linear-gradient(90deg, #ef4444, #f97316)' },
    ]
  } catch (error) {
    showToast('Eroare la calculul bottleneck-ului', 'error')
  } finally {
    loadingBottleneck.value = false;
  }
}

const triggerFps = async () => {
  const cpu = categories.value.find(c => c.id === 'cpu')?.selectedPart
  const gpu = categories.value.find(c => c.id === 'gpu')?.selectedPart
  const ram = categories.value.find(c => c.id === 'ram')?.selectedPart
  
  if (!cpu || !gpu || !ram) {
    showToast('Te rog să selectezi CPU, GPU și RAM pentru benchmark!', 'error')
    return
  }
  
  showFps.value = true;
  loadingFps.value = true;
  
  try {
    const response = await api.post('/builder/benchmark/', {
      cpu: cpu,
      gpu: gpu,
      ram: ram,
      rezolutie: '1080p'
    })
    
    if (response.data.error) {
      showToast(response.data.error, 'error');
      console.error(response.data.traceback);
      return;
    }
    
    if (response.data.jocuri) {
      fpsEstimates.value = response.data.jocuri.slice(0, 5).map(j => ({
        name: j.nume,
        fhd: j.fps_1080p?.ultra || '-',
        qhd: j.fps_1440p?.ultra || '-',
        uhd: j.fps_4k?.ultra || '-'
      }))
    }
  } catch (error) {
    showToast('Eroare la simularea FPS-urilor', 'error')
  } finally {
    loadingFps.value = false;
  }
}

const triggerCasePreview = async () => {
  if (!isLoggedIn.value) {
    showToast('Trebuie să fii conectat pentru a genera imagini!', 'error')
    return
  }
  
  const casePart = categories.value.find(c => c.id === 'case')?.selectedPart
  const gpu = categories.value.find(c => c.id === 'gpu')?.selectedPart
  const cpu = categories.value.find(c => c.id === 'cpu')?.selectedPart
  
  if (!casePart || !gpu || !cpu) {
    showToast('Te rog să selectezi Carcasa, GPU și CPU pentru imagine!', 'error')
    return
  }
  
  try {
    imageGenerationErrorText.value = null; // Reset error before fetching
    showToast('Se generează imaginea... Așteaptă câteva secunde.', 'success')
    const response = await api.post('/builder/generate-image/', {
      case_name: casePart.nume || casePart.name,
      gpu_name: gpu.nume || gpu.name,
      cpu_name: cpu.nume || cpu.name
    })
    
    if (response.data.image_url) {
      generatedImageUrl.value = response.data.image_url
      imageGenerationsCount.value++
      localStorage.setItem('image_generations_count', imageGenerationsCount.value)
    } else {
      showToast(response.data.error || 'Eroare la generare', 'error')
      if (response.data.error) {
        imageGenerationErrorText.value = response.data.error
      } else {
        imageGenerationErrorText.value = "Preview indisponibil momentan."
      }
    }
  } catch (err) {
    showToast('Eroare la generarea imaginii', 'error')
    imageGenerationErrorText.value = "Preview indisponibil momentan (Eroare server)."
  }
}
</script>

<style scoped>
/* ==========================================================================
   DESIGN SYSTEM & CSS VARIABLES
   ========================================================================== */
.maximalist-app-container {
  /* Core Colors */
  --bg-base: #0C0D12;
  --bg-surface: rgba(255, 255, 255, 0.03);
  --border-glass: rgba(255, 255, 255, 0.08);
  
  /* Accents */
  --neon-cyan: #00e5ff;
  --neon-violet: #7c3aed;
  --neon-green: #00e5a0;
  --neon-pink: #ec4899;
  
  /* Text */
  --text-primary: #f0f4ff;
  --text-secondary: #8b9db5;

  background-color: var(--bg-base);
  color: var(--text-primary);
  min-height: 100vh;
  display: flex;
  overflow: hidden; /* Fără scroll pe body */
  position: relative;
}

/* Typography Classes */
.font-inter { font-family: 'Inter', sans-serif; }
.font-mono { font-family: 'JetBrains Mono', monospace; }
.font-syne { font-family: 'Syne', sans-serif; }

/* Dithering / Noise Effect */
.noise-texture {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");
}

/* Glassmorphism Panel Core */
.glass-panel {
  background: var(--bg-surface);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-glass);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  position: relative;
  z-index: 1;
}

.glass-panel-inner {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

/* Interactive Cards Hover */
.interactive-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}
.interactive-card:hover {
  border-color: rgba(0, 229, 255, 0.4);
  transform: translateY(-4px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 229, 255, 0.15);
}

/* Gradients Text */
.gradient-text-brand { background: linear-gradient(90deg, #f0f4ff, #8b9db5); -webkit-background-clip: text; color: transparent; font-weight: 800; font-size: 1.2rem; letter-spacing: 0.5px;}
.gradient-text-cyan { background: linear-gradient(90deg, #00e5ff, #3b82f6); -webkit-background-clip: text; color: transparent; }
.gradient-text-violet { background: linear-gradient(90deg, #ec4899, #7c3aed); -webkit-background-clip: text; color: transparent; }
.gradient-text-green { background: linear-gradient(90deg, #00e5a0, #10b981); -webkit-background-clip: text; color: transparent; }

/* Text colors */
.text-cyan { color: var(--neon-cyan); }
.text-violet { color: var(--neon-violet); }
.text-green { color: var(--neon-green); }

/* ==========================================================================
   LAYOUT: SIDEBAR
   ========================================================================== */
.sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-glass);
  background: rgba(12, 13, 18, 0.85);
  z-index: 10;
}

.sidebar-brand {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  border-bottom: 1px solid var(--border-glass);
}
.brand-icon svg { width: 28px; height: 28px; stroke: var(--neon-cyan); }

.sidebar-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 1rem;
}
.sidebar-scroll-area::-webkit-scrollbar { width: 4px; }
.sidebar-scroll-area::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }

.category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 0.5rem;
  border: 1px solid transparent;
}
.category-item:hover { background: rgba(255,255,255,0.05); }
.category-item.active {
  background: rgba(0, 229, 255, 0.1);
  border-color: rgba(0, 229, 255, 0.3);
}
.cat-left { display: flex; align-items: center; gap: 1rem; }
.cat-icon { font-size: 1.2rem; }
.cat-name { font-weight: 500; font-size: 0.95rem; color: var(--text-secondary); transition: color 0.2s;}
.category-item.active .cat-name, .category-item.has-part .cat-name { color: var(--text-primary); }

.status-indicator { width: 8px; height: 8px; border-radius: 50%; background: #334155; transition: 0.3s;}
.category-item.has-part .status-indicator { background: var(--neon-green); box-shadow: 0 0 10px var(--neon-green); }

.sidebar-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-glass);
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  background: rgba(0,0,0,0.2);
}

/* ==========================================================================
   BUTTONS
   ========================================================================== */
.btn-ghost-outline {
  background: transparent; border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 0.8rem; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  transition: 0.2s; font-weight: 600; font-size: 0.9rem;
}
.btn-ghost-outline:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.2); }

.btn-primary-green {
  background: var(--neon-green); color: #000; border: none; padding: 0.8rem; border-radius: 8px;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  font-weight: 700; transition: 0.2s; box-shadow: 0 0 15px rgba(0, 229, 160, 0.2);
}
.btn-primary-green:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 0 25px rgba(0, 229, 160, 0.4); }
.btn-primary-green:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

.btn-primary-violet {
  background: var(--neon-violet); color: #fff; border: none; padding: 0.8rem; border-radius: 8px;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  font-weight: 700; transition: 0.2s; box-shadow: 0 0 15px rgba(124, 58, 237, 0.2);
}
.btn-primary-violet:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 0 25px rgba(124, 58, 237, 0.4); }
.btn-primary-violet:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

.btn-primary-cyan {
  background: rgba(0, 229, 255, 0.1); border: 1px solid var(--neon-cyan); color: var(--neon-cyan);
  padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 700; transition: 0.2s;
}
.btn-primary-cyan:hover { background: var(--neon-cyan); color: #000; box-shadow: 0 0 15px rgba(0,229,255,0.4);}

.ai-sub-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.btn-ai-sub {
  background: rgba(124, 58, 237, 0.05);
  border: 1px solid rgba(124, 58, 237, 0.2);
  color: #c4b5fd;
  padding: 0.6rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  transition: 0.2s;
  letter-spacing: 0.5px;
}
.btn-ai-sub:hover {
  background: rgba(124, 58, 237, 0.2);
  color: #fff;
  border-color: rgba(124, 58, 237, 0.5);
}

.spin-icon { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

/* ==========================================================================
   LAYOUT: MAIN CONTENT & HERO
   ========================================================================== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 1.5rem;
  position: relative;
  z-index: 5;
}
.main-content::-webkit-scrollbar { width: 8px; }
.main-content::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }

.hero-header {
  border-radius: 16px;
  padding: 2.5rem;
  margin-bottom: 1.5rem;
  position: relative;
  overflow: hidden;
  display: flex;
  border-color: rgba(0, 229, 255, 0.15);
}

.hero-bg-animated {
  position: absolute; inset: 0; z-index: 0;
  background: linear-gradient(120deg, rgba(12,13,18,1) 0%, rgba(0, 229, 255, 0.05) 50%, rgba(124, 58, 237, 0.05) 100%);
  background-size: 200% 200%;
  animation: gradientMove 10s ease infinite;
}
@keyframes gradientMove { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

.hero-content {
  position: relative; z-index: 1; width: 100%;
  display: flex; justify-content: space-between; align-items: flex-end;
}

.hero-title { font-size: 2.5rem; margin: 0 0 1rem 0; letter-spacing: -1px; text-shadow: 0 2px 10px rgba(0,0,0,0.5); }

.badges-row { display: flex; gap: 1rem; }
.badge-status { padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1);}
.badge-status .dot { width: 8px; height: 8px; border-radius: 50%; }
.badge-status.success .dot { background: var(--neon-green); box-shadow: 0 0 8px var(--neon-green); }
.badge-status.error .dot { background: var(--neon-pink); box-shadow: 0 0 8px var(--neon-pink); }
.badge-status.info .dot { background: var(--neon-cyan); box-shadow: 0 0 8px var(--neon-cyan); }

.price-display { text-align: right; }
.price-label { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.3rem; letter-spacing: 1px; }
.price-value { font-size: 3rem; font-weight: 700; line-height: 1; margin-bottom: 0.5rem; text-shadow: 0 0 20px rgba(0,229,160,0.2); }
.price-value .currency { font-size: 1.5rem; }
.tdp-value { font-size: 0.9rem; color: #f97316; font-weight: 600; }

/* ==========================================================================
   LOADING & GRID
   ========================================================================== */
.loading-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 400px; border-radius: 16px;
}
.spinner-hologram { width: 60px; height: 60px; border: 3px solid rgba(0, 229, 255, 0.1); border-top-color: var(--neon-cyan); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 1.5rem; box-shadow: 0 0 20px rgba(0,229,255,0.2); }

.loading-state-small {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 2rem 0; min-height: 150px;
}
.small-spinner { width: 40px; height: 40px; border-width: 2px; margin-bottom: 1rem; }

/* Transitions */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  max-height: 600px;
  opacity: 1;
}
.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0 !important;
  margin-top: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  border-width: 0 !important;
}

.generated-image-container { position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.generated-preview-img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; }
.btn-enlarge { position: absolute; bottom: 10px; right: 10px; background: rgba(0, 229, 255, 0.2); border: 1px solid var(--neon-cyan); color: #fff; padding: 4px 8px; font-size: 0.8rem; cursor: pointer; border-radius: 4px; z-index: 10;}
.image-modal { position: relative; max-width: 90vw; max-height: 90vh; padding: 2rem; display: flex; justify-content: center; align-items: center; }
.full-size-img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 12px; }

.components-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 25px; margin-bottom: 30px;
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
  position: relative;
  width: 100%;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  background: rgba(255,255,255,0.02);
  border-radius: 12px;
}
.card-image-box img {
  max-width: 80%;
  max-height: 80%;
  object-fit: contain;
  filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));
}

.card-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 5px;
  line-height: 1.3;
  color: #e2e8f0;
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

.neon-price {
  color: #00f0ff;
  font-weight: 800;
  font-size: 1.3rem;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

.btn-neon {
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.8), rgba(0, 240, 255, 0.8));
  border: none;
  padding: 12px 20px;
  border-radius: 20px;
  color: white;
  font-weight: 700;
  cursor: pointer;
  transition: 0.3s;
}
.btn-neon:hover:not(:disabled) {
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.6);
  transform: scale(1.05);
}
.btn-neon:disabled { opacity: 0.5; cursor: not-allowed; }

.card-link { text-decoration: none; flex: 1; }

/* ==========================================================================
   SUMMARY LAYOUT (Coloane stânga/dreapta)
   ========================================================================== */
.summary-layout {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 1.5rem;
}
@media (max-width: 1200px) { .summary-layout { grid-template-columns: 1fr; } }

.panel-title { font-size: 1.2rem; margin: 0 0 1.5rem 0; letter-spacing: 1px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 1rem; }

/* PC Preview Hologram */
.pc-preview-card { border-radius: 16px; padding: 2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; margin-bottom: 1.5rem; overflow: hidden; position: relative;}
.pc-hologram { position: relative; width: 120px; height: 180px; perspective: 1000px; transform-style: preserve-3d; animation: float 6s ease-in-out infinite; }
.holo-core { width: 100%; height: 100%; background: linear-gradient(180deg, rgba(0, 229, 255, 0.1), rgba(124, 58, 237, 0.3)); border: 1px solid rgba(0, 229, 255, 0.5); box-shadow: 0 0 40px rgba(0, 229, 255, 0.2) inset, 0 0 20px rgba(124, 58, 237, 0.4); border-radius: 10px; }
.holo-rings { position: absolute; top: 50%; left: 50%; width: 160%; height: 60%; border: 1px dashed rgba(0, 229, 255, 0.3); border-radius: 50%; transform: translate(-50%, -50%) rotateX(75deg); animation: rotateRings 10s linear infinite; }
.pc-preview-label { position: absolute; bottom: 1.5rem; color: rgba(0, 229, 255, 0.6); font-size: 0.8rem; letter-spacing: 2px; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
@keyframes rotateRings { 100% { transform: translate(-50%, -50%) rotateX(75deg) rotateZ(360deg); } }

/* Bottleneck Analysis */
.bottleneck-panel { border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; }
.progress-item { margin-bottom: 1.2rem; }
.progress-item:last-child { margin-bottom: 0; }
.progress-header { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 600;}
.progress-track { width: 100%; height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);}
.progress-fill { height: 100%; border-radius: 4px; box-shadow: 0 0 10px currentColor; }

/* Build List */
.build-list-panel { border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; }
.build-items-container { display: flex; flex-direction: column; gap: 1rem; }
.empty-state { text-align: center; color: var(--text-secondary); padding: 2rem; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
.empty-state svg { width: 48px; height: 48px; opacity: 0.5; }
.build-item { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 1rem; display: flex; align-items: center; gap: 1rem; transition: 0.2s;}
.build-item:hover { border-color: rgba(255,255,255,0.15); background: rgba(255,255,255,0.02);}
.item-icon { font-size: 1.5rem; background: rgba(255,255,255,0.05); width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; border-radius: 8px; }
.item-info { flex: 1; display: flex; flex-direction: column; }
.item-cat { font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.2rem; }
.item-name { font-weight: 600; font-size: 0.95rem; }
.item-actions { display: flex; align-items: center; gap: 1rem; }
.item-price { font-weight: 700; color: var(--neon-green); }
.btn-swap { background: rgba(0, 229, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.3); color: var(--neon-cyan); width: 32px; height: 32px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s;}
.btn-swap svg { width: 16px; height: 16px; }
.btn-swap:hover { background: var(--neon-cyan); color: #000; box-shadow: 0 0 10px rgba(0,229,255,0.4);}

.btn-clear-all {
  background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444;
  padding: 0.3rem 0.6rem; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 4px;
  font-size: 0.8rem; font-weight: bold; transition: 0.2s;
}
.btn-clear-all:hover { background: #ef4444; color: #fff; box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);}
.btn-remove { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 1.2rem; transition: 0.2s;}
.btn-remove:hover { color: var(--neon-pink); }

/* FPS Panel */
.fps-panel { border-radius: 16px; padding: 2rem; }
.badge-ultra { background: var(--neon-violet); color: white; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.7rem; letter-spacing: 1px; }
.table-responsive { overflow-x: auto; }
.fps-table { width: 100%; border-collapse: collapse; text-align: left; }
.fps-table th { padding: 1rem 0; color: var(--text-secondary); font-size: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.1); }
.fps-table td { padding: 1rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.game-title { font-weight: 600; }
.fps-high { color: var(--neon-green); font-weight: 700;}
.fps-med { color: var(--neon-cyan); font-weight: 700;}
.fps-low { color: #f97316; font-weight: 700;}

/* ==========================================================================
   MODALS
   ========================================================================== */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.maximalist-modal { width: 100%; max-width: 500px; border-radius: 16px; border: 1px solid rgba(124, 58, 237, 0.3); box-shadow: 0 20px 50px rgba(0,0,0,0.8), 0 0 40px rgba(124, 58, 237, 0.1); display: flex; flex-direction: column; }
.modal-large { max-width: 700px; border-color: rgba(0, 229, 255, 0.3); box-shadow: 0 20px 50px rgba(0,0,0,0.8), 0 0 40px rgba(0, 229, 255, 0.1); }

.modal-header { padding: 1.5rem 2rem; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
.modal-header h2 { margin: 0; font-size: 1.25rem; letter-spacing: 1px; }
.btn-close { background: transparent; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer; transition: 0.2s; }
.btn-close:hover { color: white; transform: rotate(90deg); }

.modal-body { padding: 2rem; overflow-y: auto; max-height: 60vh; }

.input-group { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 2rem; }
.input-group label { color: var(--text-secondary); font-size: 0.85rem; letter-spacing: 1px; }
.synth-input { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1rem; color: white; font-size: 1rem; outline: none; transition: 0.2s; }
.synth-input:focus { border-color: var(--neon-violet); box-shadow: 0 0 15px rgba(124, 58, 237, 0.2); }

.save-options-row { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.5rem; }
.toggle-container { display: flex; align-items: center; gap: 1rem; }
.toggle-label { color: white; font-size: 0.9rem; letter-spacing: 1px; }

/* Switch CSS */
.synth-switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.synth-switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(255,255,255,0.1); transition: .4s; border-radius: 34px; }
.slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
.synth-switch input:checked + .slider { background-color: var(--neon-green); box-shadow: 0 0 10px var(--neon-green); }
.synth-switch input:checked + .slider:before { transform: translateX(20px); }

.user-profile-badge { display: flex; align-items: center; gap: 0.8rem; color: var(--text-secondary); font-size: 0.85rem; }
.avatar-circle { width: 28px; height: 28px; background: linear-gradient(135deg, var(--neon-cyan), var(--neon-violet)); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.8rem; }

.modal-footer { padding: 1.5rem 2rem; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: flex-end; gap: 1rem; background: rgba(0,0,0,0.2); border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;}
.btn-ghost { background: transparent; border: none; color: var(--text-secondary); font-weight: 600; padding: 0.8rem 1.5rem; cursor: pointer; border-radius: 8px; transition: 0.2s; }
.btn-ghost:hover { background: rgba(255,255,255,0.05); color: white; }

/* Alternatives Grid */
.alternatives-grid { display: flex; flex-direction: column; gap: 1rem; }
.alt-card { padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.alt-header { display: flex; align-items: center; gap: 0.8rem; }
.alt-icon { font-size: 1.5rem; }
.alt-header h4 { margin: 0; font-size: 1.1rem; }
.alt-price { font-size: 1.5rem; font-weight: 700; margin: 0; }
.alt-reason { color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0; }
</style>