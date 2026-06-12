<template>
  <div class="container builds-container">
    <h2 class="page-title">📂 Build-urile tale salvate</h2>

    <div v-if="loading" class="loading">Se încarcă lista...</div>

    <div v-else-if="builds.length === 0" class="empty-state">
      <div class="empty-icon">📁</div>
      <h3>Niciun build salvat</h3>
      <p>Nu ai salvat nicio configurație până acum. Creează una nouă și va apărea aici.</p>
      <router-link to="/" class="btn-primary" style="text-decoration: none; display: inline-flex; margin-top: 15px;">Creează primul tău Build</router-link>
    </div>

    <div v-else class="builds-grid">
      <div v-for="build in builds" :key="build.id" class="build-card glass-panel">
        <div class="build-header">
          <h3>{{ build.nume || 'Configurație PC' }}</h3>
          <span class="build-date">{{ formatDate(build.data_salvarii) }}</span>
        </div>

        <div class="build-details">
          <div class="detail-item"><strong>CPU:</strong> {{ build.cpu_nume || (build.cpu ? `#${build.cpu}` : 'Neselectat') }}</div>
          <div class="detail-item"><strong>GPU:</strong> {{ build.gpu_nume || (build.gpu ? `#${build.gpu}` : 'Neselectat') }}</div>
          <div class="total-row">
            <span>Preț Total:</span>
            <span class="price">{{ build.pret_total ?? '—' }} RON</span>
          </div>
        </div>

        <div class="build-actions">
          <button @click="openModal(build)" class="btn-outline" style="flex: 1; text-align: center;">👁 Vezi Detalii</button>
          <button @click="deleteBuild(build.id)" class="btn-delete" title="Șterge">🗑️</button>
        </div>
      </div>
    </div>

    <!-- ===== MODAL ===== -->
    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="cyber-modal">
          
          <div class="modal-header-cyber">
             <span class="modal-subtitle">PC BUILD DETAILS</span>
             <h2 class="modal-title-cyber">{{ selectedBuild?.nume || 'Configurație PC' }}</h2>
             <p class="modal-cost-date">Total cost: {{ totalPrice }} RON | {{ formatDate(selectedBuild?.data_salvarii) }}</p>
             <button class="close-btn-cyber" @click="closeModal">×</button>
          </div>

          <div v-if="modalLoading" class="modal-loading text-center mt-5 mb-5 text-muted">⏳ Se încarcă detaliile...</div>
          
          <div v-else class="modal-body-cyber">
             
             <!-- Top Row: Stats (Grid 2x2) -->
             <div class="cyber-stats-grid mb-4">
                 <div class="stat-card">
                   <div class="stat-top"><span class="icon">📦</span><span class="label">COMPONENTS</span></div>
                   <div class="stat-val">{{ selectedCount }}</div>
                 </div>
                 <div class="stat-card">
                   <div class="stat-top"><span class="icon">⚡</span><span class="label">TOTAL POWER</span></div>
                   <div class="stat-val">{{ estimatedWatts }} <span class="unit">W</span></div>
                 </div>
                 <div class="stat-card">
                   <div class="stat-top"><span class="icon">💰</span><span class="label">TOTAL PRICE</span></div>
                   <div class="stat-val"><span class="unit">RON</span> {{ totalPrice }}</div>
                 </div>
                 <div class="stat-card">
                   <div class="stat-top"><span class="icon">🚀</span><span class="label">PERFORMANCE</span></div>
                   <div class="stat-val">Tier S</div>
                 </div>
             </div>

             <!-- Bottom Row: 2 Columns -->
             <div class="cyber-bottom-grid">
                
                <!-- STÂNGA: Bottleneck -->
                <div class="cyber-box bottleneck-box">
                   <h4 class="box-title">Bottleneck Analysis</h4>
                   <div v-if="loadingBottleneck" class="text-muted">⏳ Se calculează bottleneck-ul...</div>
                   <div v-else-if="showBottleneck && bottleneckData">
                     <div class="bn-status" :class="{'text-green': !bottleneckData.exista_bottleneck, 'text-warning': bottleneckData.exista_bottleneck}">
                       Overall Status: {{ bottleneckData.mesaj || 'Analiză finalizată' }}
                     </div>
                     
                     <div class="bn-bars mt-3">
                       <div class="bn-bar-row">
                         <div class="bn-label-row"><span>Bottleneck %</span><span>{{ bottleneckData.procentaj_bottleneck || '0%' }}</span></div>
                         <div class="progress-bar-container"><div class="progress-bar violet-bar" :style="{width: bottleneckData.procentaj_bottleneck || '0%'}"></div></div>
                       </div>
                     </div>
                     <p class="bn-desc-italic mt-3 text-muted" style="font-style: italic; font-size: 0.85rem;">
                       Bazat pe analiza CPU-GPU pentru a oferi cea mai bună balanță de performanță.
                     </p>
                     <div class="bn-ref mt-2">Reference: 1440p High settings</div>
                   </div>
                </div>

                <!-- DREAPTA: Donut Chart + FPS -->
                <div class="cyber-box right-col-box">
                   
                   <div class="budget-dist">
                     <h4 class="box-title">Budget Distribution</h4>
                     <div class="donut-wrapper">
                        <svg viewBox="0 0 32 32" class="donut-chart">
                          <circle r="15.9155" cx="16" cy="16" class="donut-bg" />
                          <circle r="15.9155" cx="16" cy="16" class="donut-segment gpu" :stroke-dasharray="donutStats.gpu.arr" :stroke-dashoffset="donutStats.gpu.off" />
                          <circle r="15.9155" cx="16" cy="16" class="donut-segment cpu" :stroke-dasharray="donutStats.cpu.arr" :stroke-dashoffset="donutStats.cpu.off" />
                          <circle r="15.9155" cx="16" cy="16" class="donut-segment mobo" :stroke-dasharray="donutStats.mobo.arr" :stroke-dashoffset="donutStats.mobo.off" />
                          <circle r="15.9155" cx="16" cy="16" class="donut-segment other" :stroke-dasharray="donutStats.other.arr" :stroke-dashoffset="donutStats.other.off" />
                        </svg>
                        <div class="donut-legend">
                          <div class="legend-item"><span class="dot bg-blue"></span> GPU ({{ donutStats.gpu.pct }}%)</div>
                          <div class="legend-item"><span class="dot bg-purple"></span> CPU ({{ donutStats.cpu.pct }}%)</div>
                          <div class="legend-item"><span class="dot bg-green"></span> Mobo ({{ donutStats.mobo.pct }}%)</div>
                          <div class="legend-item"><span class="dot bg-orange"></span> Other ({{ donutStats.other.pct }}%)</div>
                        </div>
                     </div>
                   </div>

                   <div v-if="loadingFps" class="text-muted mt-4">⏳ Se estimează FPS-ul...</div>
                   <div class="fps-section mt-4" v-else-if="showFps && fpsData">
                      <table class="fps-small-table">
                        <thead>
                          <tr><th class="text-left">Game | 1440p, High Settings</th><th class="text-right">FPS</th></tr>
                        </thead>
                        <tbody>
                          <tr v-for="game in fpsData" :key="game.joc">
                            <td class="text-left">{{ game.joc }}</td>
                            <td class="text-right text-white font-mono">{{ game.fps }}</td>
                          </tr>
                        </tbody>
                      </table>
                   </div>
                </div>

             </div>

          </div>
          
          <div class="modal-footer-cyber">
             <button class="cyber-btn btn-orange" @click="checkBottleneck">
                <span class="icon">📊</span> VIEW BOTTLENECK REPORT
             </button>
             <button class="cyber-btn btn-purple" @click="checkFps">
                <span class="icon">⚡</span> CHECK FPS PERFORMANCE
             </button>
             <button class="cyber-btn btn-green" @click="loadIntoBuilder">
                <span class="icon">⬇️</span> LOAD INTO BUILDER
             </button>
          </div>

        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import api from '../plugins/axios'
import { useRouter } from 'vue-router'
import { showToast } from '@/toast'

const builds = ref([])
const loading = ref(true)
const router = useRouter()

// Modal state
const modalOpen = ref(false)
const modalLoading = ref(false)
const selectedBuild = ref(null)
const modalParts = ref({})

const showBottleneck = ref(false)
const bottleneckData = ref(null)
const loadingBottleneck = ref(false)

const showFps = ref(false)
const fpsData = ref(null)
const loadingFps = ref(false)

const partSlots = [
  { key: 'cpu',         label: 'Procesor', endpoint: 'cpus' },
  { key: 'gpu',         label: 'Placă Video', endpoint: 'gpus' },
  { key: 'motherboard', label: 'Placă de Bază', endpoint: 'motherboards' },
  { key: 'ram',         label: 'Memorie RAM', endpoint: 'rams' },
  { key: 'storage',     label: 'Stocare', endpoint: 'storages' },
  { key: 'psu',         label: 'Sursă', endpoint: 'psus' },
  { key: 'case',        label: 'Carcasă', endpoint: 'cases' },
  { key: 'cooler',      label: 'Cooler',  endpoint: 'coolers' },
]

// ── Fetch builds ──────────────────────────────────────────
const fetchSavedBuilds = async () => {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) { router.push('/login'); return }
    const response = await api.get('saved-builds/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    builds.value = response.data.results || response.data
  } catch (error) {
    console.error('Eroare la preluarea build-urilor:', error)
  } finally {
    loading.value = false
  }
}

// ── Delete ────────────────────────────────────────────────
const deleteBuild = async (id) => {
  if (confirm('Sigur vrei să ștergi această configurație?')) {
    try {
      await api.delete(`saved-builds/${id}/`)
      builds.value = builds.value.filter(b => b.id !== id)
    } catch {
      alert('Eroare la ștergere.')
    }
  }
}

// ── Modal ─────────────────────────────────────────────────
const openModal = async (build) => {
  selectedBuild.value = build
  modalParts.value = {}
  modalOpen.value = true
  modalLoading.value = true

  try {
    const fetches = partSlots.map(async (slot) => {
      const id = build[slot.key]
      if (!id) return
      try {
        const res = await api.get(`${slot.endpoint}/${id}/`)
        modalParts.value[slot.key] = res.data
      } catch {
        modalParts.value[slot.key] = { id, nume: `ID #${id}`, pret: null }
      }
    })
    await Promise.all(fetches)
  } catch (error) {
    console.error('Eroare detaliere build:', error)
  } finally {
    modalLoading.value = false
  }
}

const checkBottleneck = async () => {
  if (!selectedBuild.value?.cpu || !selectedBuild.value?.gpu) {
    showToast('Această configurație necesită un CPU și un GPU salvate pentru analiză.', 'error')
    return
  }
  
  showBottleneck.value = true
  loadingBottleneck.value = true
  
  try {
    const response = await api.post('/builder/bottleneck/', {
      cpu_id: selectedBuild.value.cpu,
      gpu_id: selectedBuild.value.gpu
    })
    bottleneckData.value = response.data
  } catch (err) {
    showToast('Eroare la calcularea bottleneck-ului', 'error')
  } finally {
    loadingBottleneck.value = false
  }
}

const checkFps = async () => {
  if (!selectedBuild.value?.gpu) {
    showToast('Această configurație necesită un GPU salvat pentru estimarea FPS.', 'error')
    return
  }
  
  showFps.value = true
  loadingFps.value = true
  
  try {
    const response = await api.post('/builder/benchmark/', {
      gpu_id: selectedBuild.value.gpu
    })
    fpsData.value = response.data.fps_estimari || response.data
  } catch (err) {
    showToast('Eroare la calcularea FPS-ului', 'error')
  } finally {
    loadingFps.value = false
  }
}

const closeModal = () => {
  modalOpen.value = false
  selectedBuild.value = null
  modalParts.value = {}
  showBottleneck.value = false
  bottleneckData.value = null
  showFps.value = false
  fpsData.value = null
}

const loadIntoBuilder = () => {
  sessionStorage.setItem('loadBuild', JSON.stringify(modalParts.value))
  router.push('/')
}

const totalPrice = computed(() => {
  return partSlots.reduce((sum, slot) => {
    return sum + parseFloat(modalParts.value[slot.key]?.pret || 0)
  }, 0).toFixed(2)
})

const selectedCount = computed(() =>
  partSlots.filter(s => modalParts.value[s.key]).length
)

const estimatedWatts = computed(() => {
  const cpu = parseFloat(modalParts.value.cpu?.consum_tdp || 0)
  const gpu = parseFloat(modalParts.value.gpu?.consum_tdp || 0)
  return cpu + gpu + 50 || '450'
})

const donutStats = computed(() => {
  const total = parseFloat(totalPrice.value) || 1
  
  const getPrice = (key) => parseFloat(modalParts.value[key]?.pret || 0)
  
  const gpuP = (getPrice('gpu') / total) * 100
  const cpuP = (getPrice('cpu') / total) * 100
  const moboP = (getPrice('motherboard') / total) * 100
  let otherP = 100 - gpuP - cpuP - moboP
  if (otherP < 0) otherP = 0
  
  return {
    gpu: { pct: gpuP.toFixed(1), arr: `${gpuP} ${100 - gpuP}`, off: 0 },
    cpu: { pct: cpuP.toFixed(1), arr: `${cpuP} ${100 - cpuP}`, off: -gpuP },
    mobo: { pct: moboP.toFixed(1), arr: `${moboP} ${100 - moboP}`, off: -(gpuP + cpuP) },
    other: { pct: otherP.toFixed(1), arr: `${otherP} ${100 - otherP}`, off: -(gpuP + cpuP + moboP) },
  }
})

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return isNaN(d) ? '—' : d.toLocaleDateString('ro-RO')
}

onMounted(fetchSavedBuilds)
</script>

<style scoped>
.builds-container { padding-top: 40px; padding-bottom: 40px; }
.page-title { font-size: 2rem; font-weight: 800; margin-bottom: 30px; color: white; }

.builds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 25px;
}

.build-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.build-header {
  margin-bottom: 15px;
}
.build-header h3 { margin: 0 0 5px 0; font-size: 1.2rem; font-weight: 800; color: white; }
.build-date { font-size: 0.8rem; color: var(--text-muted); }

.build-details {
  margin: auto 0 20px 0;
  padding: 15px 0;
  border-top: 1px solid rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.detail-item { font-size: 0.9rem; margin-bottom: 8px; color: var(--text-muted); }
.detail-item strong { color: white; }
.total-row { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; font-weight: 800; font-size: 1.1rem; }
.total-row .price { color: var(--accent-color); }

.build-actions { display: flex; gap: 10px; }
.btn-delete {
  width: 40px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.2s;
}
.btn-delete:hover { background: #ef4444; }

/* MODAL STYLES (IMAGE 3) */
.modal-backdrop {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.8);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}

.cyber-modal {
  width: 95%;
  max-width: 900px;
  background: #111318;
  border-radius: 4px;
  position: relative;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.text-warning { color: #f59e0b; }

.modal-header-cyber {
  padding: 30px 40px 20px;
}

.modal-subtitle {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.modal-title-cyber {
  font-size: 2rem;
  font-weight: 800;
  color: white;
  margin: 5px 0;
}

.modal-cost-date {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin: 0;
}

.close-btn-cyber {
  position: absolute;
  top: 20px; right: 25px;
  background: none; border: none;
  color: #64748b; font-size: 2rem;
  cursor: pointer; transition: 0.2s;
  line-height: 1;
}
.close-btn-cyber:hover { color: white; }

.modal-body-cyber { padding: 0 40px 20px; }

/* Grid 2x2 Stats */
.cyber-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
}
@media (max-width: 600px) { .cyber-stats-grid { grid-template-columns: 1fr 1fr; } }

.stat-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 15px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
}
.stat-top { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.stat-top .icon { font-size: 1.1rem; }
.stat-top .label { font-size: 0.75rem; color: var(--text-muted); font-weight: 600; }
.stat-val { font-size: 1.4rem; font-weight: 800; color: white; }
.stat-val .unit { font-size: 0.9rem; color: var(--text-muted); font-weight: 600; }

/* Bottom Grid */
.cyber-bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
}
@media (max-width: 600px) { .cyber-bottom-grid { grid-template-columns: 1fr; } }

.box-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: white;
  margin: 0 0 15px 0;
}

.bn-status { font-weight: 600; font-size: 0.95rem; }
.text-green { color: var(--accent-color); }

.bn-label-row { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px; color: white;}
.progress-bar-container { background: rgba(255, 255, 255, 0.05); height: 8px; border-radius: 4px; overflow: hidden;}
.progress-bar { height: 100%; }
.violet-bar { background: var(--accent-secondary); }
.cyan-bar { background: var(--accent-color); }
.bn-ref { font-size: 0.8rem; color: var(--text-muted); }

/* Donut Chart */
.budget-dist {
  background: transparent;
}
.donut-wrapper {
  display: flex;
  align-items: center;
  gap: 20px;
}
.donut-chart {
  width: 100px; height: 100px;
  transform: rotate(-90deg);
}
.donut-bg { fill: transparent; stroke: rgba(255,255,255,0.05); stroke-width: 6; }
.donut-segment { fill: transparent; stroke-width: 6; transition: stroke-dasharray 1s ease; }
.gpu { stroke: #3b82f6; }
.cpu { stroke: #a855f7; }
.mobo { stroke: #10b981; }
.other { stroke: #f97316; }

.donut-legend { display: flex; flex-direction: column; gap: 8px; }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: var(--text-muted); font-weight: 600;}
.legend-item .dot { width: 10px; height: 10px; border-radius: 50%; }
.bg-blue { background: #3b82f6; }
.bg-purple { background: #a855f7; }
.bg-green { background: #10b981; }
.bg-orange { background: #f97316; }

/* FPS Table */
.fps-small-table { width: 100%; border-collapse: collapse; }
.fps-small-table th { color: var(--text-muted); font-size: 0.8rem; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.fps-small-table td { font-size: 0.85rem; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.02); }
.font-mono { font-family: monospace; font-size: 1rem !important; }
.text-right { text-align: right; }
.text-white { color: white; }

/* Footer Buttons */
.modal-footer-cyber {
  padding: 0 40px 30px;
  display: flex;
  gap: 15px;
}
@media (max-width: 600px) { .modal-footer-cyber { flex-direction: column; } }

.cyber-btn {
  flex: 1;
  padding: 14px 10px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.85rem;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: white;
  transition: filter 0.2s;
}
.cyber-btn:hover { filter: brightness(1.1); }
.btn-orange { background: #f97316; }
.btn-purple { background: #7c3aed; }
.btn-green { background: #00e5a0; color: #000; }
</style>
