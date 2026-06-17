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
      <div v-if="modalOpen" class="modal-backdrop-new" @click.self="closeModal">
        <div class="modal-container-new">
          
          <div class="modal-header-new">
            <div class="header-left">
              <span class="label-tiny">PC BUILD DETAILS</span>
              <h2 class="title-build">{{ selectedBuild?.nume || 'Configurație PC' }}</h2>
              <div class="metadata-row">
                <span class="cost-green">Total cost: {{ totalPrice }} RON</span>
                <span class="separator">|</span>
                <span class="date-grey">{{ formatDate(selectedBuild?.data_salvarii) }}</span>
              </div>
            </div>
            <div class="header-right">
              <button class="btn-close-new" @click="closeModal">×</button>
            </div>
          </div>

          <div v-if="modalLoading" class="modal-loading text-center mt-5 mb-5 text-muted">⏳ Se încarcă detaliile...</div>
          
          <div v-else class="modal-body-new">
             
             <!-- Top Row: Stats (Grid 2x2) -->
             <div class="stats-grid-new">
                 <div class="stat-card-new stat-components" style="--delay: 0s">
                   <div class="stat-top-new"><span class="icon">📦</span><span class="label">COMPONENTS</span></div>
                   <div class="stat-val-new">{{ selectedCount }}</div>
                 </div>
                 <div class="stat-card-new stat-power" style="--delay: 0.08s">
                   <div class="stat-top-new"><span class="icon">⚡</span><span class="label">TOTAL POWER</span></div>
                   <div class="stat-val-new">{{ estimatedWatts }} <span class="unit">W</span></div>
                 </div>
                 <div class="stat-card-new stat-price" style="--delay: 0.16s">
                   <div class="stat-top-new"><span class="icon">💰</span><span class="label">TOTAL PRICE</span></div>
                   <div class="stat-val-new">{{ totalPrice }} <span class="unit">RON</span></div>
                 </div>
                 <div class="stat-card-new stat-perf" style="--delay: 0.24s">
                   <div class="stat-top-new"><span class="icon">🚀</span><span class="label">PERFORMANCE</span></div>
                   <div class="stat-val-new tier-s">Tier S</div>
                 </div>
             </div>

             <!-- Middle Section -->
             <div class="middle-grid-new">
                
                <!-- STÂNGA: Bottleneck -->
                <div class="box-new bottleneck-box-new">
                   <h4 class="box-title-new">BOTTLENECK ANALYSIS</h4>
                   <div v-if="loadingBottleneck" class="text-muted text-center py-4">⏳ Se calculează bottleneck-ul...</div>
                   <div v-else-if="!showBottleneck" class="placeholder-text">Rulează o analiză pentru a vedea datele.</div>
                   <div v-else-if="showBottleneck && bottleneckData">
                     <div class="bn-status-row">
                       <span class="bn-status-label">Overall Status:</span>
                       <span class="bn-status-val" :class="{'text-green': !bottleneckData.exista_bottleneck, 'text-warning': bottleneckData.exista_bottleneck}">
                         {{ bottleneckData.mesaj || 'Analiză finalizată' }}
                       </span>
                     </div>
                     
                     <div class="bn-bars-new mt-3">
                       <div class="bn-bar-row-new">
                         <div class="bn-label-row-new">
                           <span>Bottleneck / CPU Load</span>
                           <span :class="{'text-warning': bottleneckData.exista_bottleneck, 'text-green': !bottleneckData.exista_bottleneck}">
                             {{ bottleneckData.procentaj_bottleneck || '0%' }}
                           </span>
                         </div>
                         <div class="progress-bar-container-new">
                            <div class="progress-bar-fill pb-cpu" :style="{width: bottleneckData.procentaj_bottleneck || '0%'}"></div>
                         </div>
                       </div>
                     </div>
                     <p class="bn-desc-italic mt-3">
                       Bazat pe analiza CPU-GPU pentru a oferi cea mai bună balanță de performanță la 1440p High.
                     </p>
                   </div>
                </div>

                <!-- DREAPTA: Donut Chart -->
                <div class="box-new right-col-box-new">
                   <h4 class="box-title-new">BUDGET DISTRIBUTION</h4>
                   <div class="donut-layout-new">
                      <div class="donut-chart-container">
                        <svg viewBox="0 0 42 42" class="donut-chart-new">
                          <circle r="15.9155" cx="21" cy="21" class="donut-bg-new" />
                          <circle r="15.9155" cx="21" cy="21" class="donut-segment gpu-seg" :stroke-dasharray="donutStats.gpu.arr" :stroke-dashoffset="donutStats.gpu.off" />
                          <circle r="15.9155" cx="21" cy="21" class="donut-segment cpu-seg" :stroke-dasharray="donutStats.cpu.arr" :stroke-dashoffset="donutStats.cpu.off" />
                          <circle r="15.9155" cx="21" cy="21" class="donut-segment mobo-seg" :stroke-dasharray="donutStats.mobo.arr" :stroke-dashoffset="donutStats.mobo.off" />
                          <circle r="15.9155" cx="21" cy="21" class="donut-segment other-seg" :stroke-dasharray="donutStats.other.arr" :stroke-dashoffset="donutStats.other.off" />
                        </svg>
                        <div class="donut-center-text">
                          <div class="total-ron-val">{{ totalPrice }}</div>
                          <div class="total-ron-lbl">RON Total</div>
                        </div>
                      </div>
                      
                      <div class="donut-legend-new">
                        <div class="leg-item"><span class="dot d-gpu"></span> <span class="lbl">GPU</span> <span class="val">{{ donutStats.gpu.pct }}%</span></div>
                        <div class="leg-item"><span class="dot d-cpu"></span> <span class="lbl">CPU</span> <span class="val">{{ donutStats.cpu.pct }}%</span></div>
                        <div class="leg-item"><span class="dot d-mobo"></span> <span class="lbl">Mobo</span> <span class="val">{{ donutStats.mobo.pct }}%</span></div>
                        <div class="leg-item"><span class="dot d-other"></span> <span class="lbl">Other</span> <span class="val">{{ donutStats.other.pct }}%</span></div>
                      </div>
                   </div>

                   <!-- FPS TABLE -->
                   <div v-if="loadingFps" class="text-muted mt-4 text-center">⏳ Se estimează FPS-ul...</div>
                   <div class="fps-section-new mt-4" v-else-if="showFps && fpsData">
                      <table class="fps-table-new">
                        <thead>
                          <tr><th class="text-left">GAME TITLE</th><th class="text-right">FPS</th></tr>
                        </thead>
                        <tbody>
                          <tr v-for="game in fpsData" :key="game.joc">
                            <td class="text-left">{{ game.joc }}</td>
                            <td class="text-right val">{{ game.fps }}</td>
                          </tr>
                        </tbody>
                      </table>
                   </div>
                </div>

             </div>

          </div>
          
          <div class="modal-footer-new">
             <button class="btn-new btn-bn" @click="checkBottleneck">
                <span class="icon">📊</span> VIEW BOTTLENECK REPORT
             </button>
             <button class="btn-new btn-fps" @click="checkFps">
                <span class="icon">⚡</span> CHECK FPS PERFORMANCE
             </button>
             <button class="btn-new btn-load" @click="loadIntoBuilder">
                <span class="icon">⬇</span> LOAD INTO BUILDER
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
      cpu_id: selectedBuild.value.cpu,
      gpu_id: selectedBuild.value.gpu,
      ram_id: selectedBuild.value.ram
    })
    
    if (response.data.error) {
      showToast(response.data.error, 'error')
      fpsData.value = []
      return
    }

    if (response.data.jocuri) {
      fpsData.value = response.data.jocuri.map(j => ({
        joc: j.nume,
        fps: `${j.fps_1080p?.ultra || '-'} FPS`
      }))
    } else {
      fpsData.value = response.data.fps_estimari || response.data
    }
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

/* ==========================================================================
   MODAL REDESIGN
   ========================================================================== */
.modal-backdrop-new {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.modal-container-new {
  width: min(860px, 94vw);
  max-height: 90vh;
  overflow-y: auto;
  background: #0e0c1a;
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: 20px;
  box-shadow: 
    0 0 0 1px rgba(255,255,255,0.05),
    0 24px 80px rgba(0,0,0,0.6),
    0 0 60px rgba(124,58,237,0.12);
  padding: 32px;
  position: relative;
  animation: slideUp 0.3s ease;
}
.modal-container-new::-webkit-scrollbar { width: 4px; }
.modal-container-new::-webkit-scrollbar-thumb { background: rgba(124,58,237,0.4); border-radius: 4px; }
.modal-container-new::-webkit-scrollbar-track { background: transparent; }

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* HEADER */
.modal-header-new {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 24px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.label-tiny { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em; color: #8b9db5; text-transform: uppercase; margin-bottom: 2px; }
.title-build { font-size: clamp(1.6rem, 3vw, 2.2rem); font-weight: 800; color: #f0f4ff; line-height: 1.1; margin: 0; }
.metadata-row { display: flex; gap: 16px; margin-top: 6px; align-items: center; }
.cost-green { font-size: 0.85rem; color: #00e5a0; font-weight: 600; }
.separator { color: rgba(255,255,255,0.2); }
.date-grey { font-size: 0.85rem; color: #8b9db5; }

.header-right .btn-close-new {
  width: 36px; height: 36px; border-radius: 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  color: #8b9db5; font-size: 1.2rem;
  cursor: pointer; transition: all 0.15s ease;
  display: flex; align-items: center; justify-content: center;
}
.header-right .btn-close-new:hover { background: rgba(255,255,255,0.1); color: #fff; }

/* 2x2 STATS */
.stats-grid-new { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
@media (max-width: 768px) { .stats-grid-new { grid-template-columns: repeat(2, 1fr); } }

.stat-card-new {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px;
  padding: 16px;
  position: relative; overflow: hidden;
  transition: all 0.2s ease;
  animation: fadeUp 0.4s ease both;
  animation-delay: var(--delay);
}
.stat-card-new:hover { border-color: rgba(255,255,255,0.12); background: rgba(255,255,255,0.05); }
.stat-card-new::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px; }

.stat-components::before { background: #818cf8; }
.stat-power::before { background: #f59e0b; }
.stat-price::before { background: #00e5a0; }
.stat-perf::before { background: #7c3aed; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.stat-top-new { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.stat-top-new .icon { font-size: 1rem; }
.stat-top-new .label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #8b9db5; }
.stat-val-new { font-size: 1.6rem; font-weight: 800; color: #f0f4ff; line-height: 1; }
.stat-val-new .unit { font-size: 0.85rem; font-weight: 500; color: #8b9db5; margin-left: 4px; vertical-align: middle; }
.tier-s { color: #00e5a0; }

/* MIDDLE GRID */
.middle-grid-new { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
@media (max-width: 768px) { .middle-grid-new { grid-template-columns: 1fr; } }

.box-new {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 20px;
}
.box-title-new { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #8b9db5; margin: 0 0 16px 0; }
.placeholder-text { text-align: center; color: #8b9db5; font-size: 0.85rem; padding: 20px 0; }

/* BOTTLENECK */
.bn-status-row { display: flex; gap: 8px; margin-bottom: 16px; align-items: center;}
.bn-status-label { font-size: 0.82rem; color: #8b9db5; }
.bn-status-val { font-weight: 700; font-size: 0.85rem; }
.text-green { color: #00e5a0; }
.text-warning { color: #f59e0b; }

.bn-bars-new { display: flex; flex-direction: column; gap: 14px; }
.bn-label-row-new { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: #e2e8f0; margin-bottom: 6px; }
.progress-bar-container-new { height: 6px; border-radius: 3px; background: rgba(255,255,255,0.06); overflow: hidden; position: relative;}
.progress-bar-fill { height: 100%; width: 0; border-radius: 3px; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); animation: fillAnim 0.8s forwards;}
.pb-cpu { background: linear-gradient(90deg, #818cf8, #6366f1); }
@keyframes fillAnim { from { width: 0; } }

.bn-desc-italic { margin-top: 12px; font-size: 0.78rem; color: #8b9db5; line-height: 1.5; font-style: italic; background: rgba(255,255,255,0.02); border-radius: 8px; padding: 10px; }

/* DONUT */
.donut-layout-new { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.donut-chart-container { position: relative; width: 180px; height: 180px; }
.donut-chart-new { width: 100%; height: 100%; transform: rotate(-90deg); }
.donut-bg-new { fill: transparent; stroke: rgba(255,255,255,0.03); stroke-width: 6; }
.donut-segment { fill: transparent; stroke-width: 6; transition: stroke-dasharray 1s ease; animation: rotateAnim 0.8s ease-out; transform-origin: center;}
@keyframes rotateAnim { from { stroke-dasharray: 0 100; } }
.gpu-seg { stroke: #3b82f6; }
.cpu-seg { stroke: #7c3aed; }
.mobo-seg { stroke: #00e5a0; }
.other-seg { stroke: #f59e0b; }

.donut-center-text { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.total-ron-val { font-size: 1.1rem; font-weight: 800; color: #fff; }
.total-ron-lbl { font-size: 0.65rem; color: #8b9db5; text-transform: uppercase; letter-spacing: 0.05em; }

.donut-legend-new { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; width: 100%; max-width: 300px; }
.leg-item { display: flex; align-items: center; gap: 8px; }
.leg-item .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.d-gpu { background: #3b82f6; }
.d-cpu { background: #7c3aed; }
.d-mobo { background: #00e5a0; }
.d-other { background: #f59e0b; }
.leg-item .lbl { font-size: 0.78rem; color: #8b9db5; }
.leg-item .val { font-size: 0.78rem; font-weight: 700; color: #f0f4ff; margin-left: auto; }

/* FPS TABLE */
.fps-table-new { width: 100%; border-collapse: collapse; }
.fps-table-new th { font-size: 0.72rem; color: #8b9db5; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 8px; }
.fps-table-new td { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.02); font-size: 0.8rem; }
.fps-table-new .text-left { text-align: left; color: #e2e8f0; }
.fps-table-new .text-right { text-align: right; }
.fps-table-new .val { font-family: monospace; font-size: 0.95rem; font-weight: 700; color: #fff; }

/* FOOTER BUTTONS */
.modal-footer-new { display: flex; gap: 12px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.06); }
@media (max-width: 640px) { .modal-footer-new { flex-direction: column; } }
.btn-new {
  flex: 1; height: 44px; border-radius: 10px; border: none; cursor: pointer;
  font-size: 0.82rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all 0.2s ease;
}
.btn-bn { background: linear-gradient(135deg, #ea580c, #f97316); color: #fff; }
.btn-bn:hover { filter: brightness(1.1); box-shadow: 0 0 20px rgba(249,115,22,0.4); }
.btn-fps { background: linear-gradient(135deg, #6d28d9, #7c3aed); color: #fff; }
.btn-fps:hover { filter: brightness(1.1); box-shadow: 0 0 20px rgba(124,58,237,0.4); }
.btn-load { background: linear-gradient(135deg, #059669, #00e5a0); color: #000; font-weight: 800; }
.btn-load:hover { filter: brightness(1.08); box-shadow: 0 0 20px rgba(0,229,160,0.35); }
</style>
