<template>
  <div class="container builds-container">
    <h2 class="page-title">📂 Build-urile tale salvate</h2>

    <div v-if="loading" class="loading">Se încarcă lista...</div>

    <div v-else-if="builds.length === 0" class="empty-state">
      <div class="empty-icon">📁</div>
      <h3>Niciun build salvat</h3>
      <p>Nu ai salvat nicio configurație până acum. Creează una nouă și va apărea aici.</p>
      <router-link to="/" class="btn-create-build">Creează primul tău Build</router-link>
    </div>

    <div v-else class="builds-grid">
      <div v-for="build in builds" :key="build.id" class="build-card">
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
          <button @click="openModal(build)" class="btn-view">👁 Vezi Detalii</button>
          <button @click="deleteBuild(build.id)" class="btn-delete">🗑️</button>
        </div>
      </div>
    </div>

    <!-- ===== MODAL ===== -->
    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal">

          <div class="modal-header">
            <div>
              <h2>{{ selectedBuild?.nume || 'Configurație PC' }}</h2>
              <span class="modal-date">{{ formatDate(selectedBuild?.data_salvarii) }}</span>
            </div>
            <button class="modal-close" @click="closeModal">✕</button>
          </div>

          <div v-if="modalLoading" class="modal-loading">Se încarcă detaliile...</div>

          <div v-else class="modal-body">

            <!-- Piese -->
            <div class="modal-section">
              <h4>🔧 Componente</h4>
              <div class="parts-grid">
                <div
                  v-for="slot in partSlots"
                  :key="slot.key"
                  class="part-row"
                  :class="{ 'part-missing': !modalParts[slot.key] }"
                >
                  <span class="part-icon">{{ slot.icon }}</span>
                  <div class="part-info">
                    <span class="part-label">{{ slot.label }}</span>
                    <span class="part-name">
                      {{ modalParts[slot.key]?.nume || modalParts[slot.key]?.model || 'Neselectat' }}
                      <a v-if="modalParts[slot.key]?.url_produs" :href="modalParts[slot.key].url_produs" target="_blank" class="external-link" title="Cumpără de pe magazin">🛒</a>
                    </span>
                  </div>
                  <span class="part-price" v-if="modalParts[slot.key]">
                    {{ modalParts[slot.key]?.pret }} RON
                  </span>
                </div>
              </div>
            </div>

            <!-- Grafic + sumar -->
            <div class="modal-side">

              <!-- Pie chart SVG -->
              <div class="modal-section chart-section">
                <h4>📊 Distribuție Buget</h4>
                <div class="chart-wrapper">
                  <svg viewBox="0 0 200 200" class="pie-svg">
                    <g v-for="(slice, i) in pieSlices" :key="i">
                      <path
                        :d="slice.path"
                        :fill="slice.color"
                        :opacity="slice.value > 0 ? 1 : 0"
                        class="pie-slice"
                      />
                    </g>
                    <circle cx="100" cy="100" r="55" fill="#1a1b26"/>
                    <text x="100" y="95" text-anchor="middle" class="pie-center-label">Total</text>
                    <text x="100" y="115" text-anchor="middle" class="pie-center-value">{{ totalPrice }} RON</text>
                  </svg>
                  <div class="pie-legend">
                    <div v-for="(slice, i) in pieSlices.filter(s => s.value > 0)" :key="i" class="legend-item">
                      <span class="legend-dot" :style="{ background: slice.color }"></span>
                      <span class="legend-label">{{ slice.label }}</span>
                      <span class="legend-pct">{{ slice.pct }}%</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Sumar performanță -->
              <div class="modal-section">
                <h4>⚡ Sumar</h4>
                <div class="summary-stats">
                  <div class="stat-row">
                    <span>Consum estimat</span>
                    <strong>{{ estimatedWatts }} W</strong>
                  </div>
                  <div class="stat-row">
                    <span>Preț total</span>
                    <strong class="green">{{ totalPrice }} RON</strong>
                  </div>
                  <div class="stat-row">
                    <span>Componente selectate</span>
                    <strong>{{ selectedCount }} / 8</strong>
                  </div>
                </div>
              </div>

              <div class="modal-section" v-if="bottleneckData || loadingBottleneck">
                 <h4>⚡ Analiză Bottleneck</h4>
                 <div v-if="loadingBottleneck">⏳ Se calculează...</div>
                 <div v-else>
                    <p v-if="bottleneckData.are_bottleneck" style="color: #f59e0b">
                       ⚠️ <strong>{{ bottleneckData.componenta_limitatoare }}</strong> limitează performanța cu <strong>{{ bottleneckData.procentaj_bottleneck }}%</strong>.
                    </p>
                    <p v-else style="color: #10b981">
                       ✅ Build echilibrat (Bottleneck: {{ bottleneckData.procentaj_bottleneck }}%)
                    </p>
                 </div>
              </div>

              <div class="modal-section" v-if="fpsData || loadingFps">
                 <h4>🎮 Gaming FPS</h4>
                 <div v-if="loadingFps">⏳ Se generează...</div>
                 <div v-else class="fps-table-wrapper">
                    <p style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 5px;">{{ fpsData.analiza_text?.substring(0,80) }}...</p>
                    <table class="fps-table" style="width: 100%; text-align: center; font-size: 0.85rem; border-collapse: collapse;">
                       <thead>
                          <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                             <th style="padding: 5px;">Joc</th>
                             <th>1080p</th>
                             <th>1440p</th>
                             <th>4K</th>
                          </tr>
                       </thead>
                       <tbody>
                          <tr v-for="joc in (fpsData.fps_data?.jocuri || fpsData.jocuri || []).slice(0, 4)" :key="joc.nume">
                             <td style="padding: 5px; text-align: left;">{{ joc.nume }}</td>
                             <td>{{ joc.fps_1080p || '-' }}</td>
                             <td>{{ joc.fps_1440p || '-' }}</td>
                             <td>{{ joc.fps_4k || '-' }}</td>
                          </tr>
                       </tbody>
                    </table>
                 </div>
              </div>
              
              <div class="modal-section" v-if="generatedImageUrl || loadingImage">
                 <h4>📸 Randare 3D Build</h4>
                 <div v-if="loadingImage">⏳ Agentul AI generează imaginea...</div>
                 <div v-else>
                    <img :src="generatedImageUrl" alt="PC Render" style="width: 100%; border-radius: 8px; margin-top: 10px;" />
                 </div>
              </div>

            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-bottleneck" v-if="modalParts.cpu && modalParts.gpu" @click="checkBottleneck" :disabled="loadingBottleneck">
              ⚡ Bottleneck
            </button>
            <button class="btn-fps" v-if="modalParts.cpu && modalParts.gpu && !fpsData" @click="checkFps" :disabled="loadingFps">
              🎮 Rulează Benchmark
            </button>
            <button class="btn-image" v-if="modalParts.cpu && modalParts.gpu && modalParts.case && !generatedImageUrl" @click="generateImage" :disabled="loadingImage">
              📸 Generează Imagine
            </button>
            <button class="btn-load-builder" @click="loadIntoBuilder">
              🚀 Încarcă în Builder
            </button>
            <button class="btn-cancel" @click="closeModal">Închide</button>
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

const builds = ref([])
const loading = ref(true)
const router = useRouter()

// Modal state
const modalOpen = ref(false)
const modalLoading = ref(false)
const selectedBuild = ref(null)
const modalParts = ref({})

const bottleneckData = ref(null)
const loadingBottleneck = ref(false)
const fpsData = ref(null)
const loadingFps = ref(false)
const generatedImageUrl = ref(null)
const loadingImage = ref(false)

const partSlots = [
  { key: 'cpu',         label: 'Procesor',      icon: '🧠', endpoint: 'cpus' },
  { key: 'gpu',         label: 'Placă Video',   icon: '🎮', endpoint: 'gpus' },
  { key: 'motherboard', label: 'Placă de Bază', icon: '🛹', endpoint: 'motherboards' },
  { key: 'ram',         label: 'Memorie RAM',   icon: '⚡', endpoint: 'rams' },
  { key: 'storage',     label: 'Stocare',       icon: '💾', endpoint: 'storages' },
  { key: 'psu',         label: 'Sursă',         icon: '🔌', endpoint: 'psus' },
  { key: 'case',        label: 'Carcasă',       icon: '📦', endpoint: 'cases' },
  { key: 'cooler',      label: 'Cooler',        icon: '❄️', endpoint: 'coolers' },
]

const PIE_COLORS = ['#3b82f6','#10b981','#f59e0b','#f43f5e','#8b5cf6','#06b6d4','#84cc16','#ec4899']

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
    // Fetch fiecare piesă după ID
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
    
    if (modalParts.value.cpu && modalParts.value.gpu) {
       checkFpsCache(modalParts.value.cpu.id, modalParts.value.gpu.id);
    }
  } catch (error) {
    console.error('Eroare detaliere build:', error)
  } finally {
    modalLoading.value = false
  }
}

const checkBottleneck = async () => {
  const cpuId = modalParts.value.cpu?.id;
  const gpuId = modalParts.value.gpu?.id;
  if (!cpuId || !gpuId) return;
  
  loadingBottleneck.value = true;
  try {
    const res = await api.get(`/builder/bottleneck/?cpu_id=${cpuId}&gpu_id=${gpuId}`);
    bottleneckData.value = res.data;
  } catch (err) {
    console.error(err);
  } finally {
    loadingBottleneck.value = false;
  }
}

const checkFpsCache = async (cpuId, gpuId) => {
  try {
    const res = await api.get(`/builder/benchmark/?cpu_id=${cpuId}&gpu_id=${gpuId}`);
    if (res.data.cached) {
       fpsData.value = res.data;
    }
  } catch (err) {
    console.error(err);
  }
}

const checkFps = async () => {
  const cpu = modalParts.value.cpu;
  const gpu = modalParts.value.gpu;
  if (!cpu || !gpu) return;
  
  loadingFps.value = true;
  try {
    const res = await api.post('/builder/benchmark/', {
      cpu: cpu,
      gpu: gpu,
      ram: modalParts.value.ram || {},
      rezolutie: '1080p'
    });
    fpsData.value = res.data;
  } catch (err) {
    console.error(err);
  } finally {
    loadingFps.value = false;
  }
}

const generateImage = async () => {
  const cpu = modalParts.value.cpu;
  const gpu = modalParts.value.gpu;
  const case_part = modalParts.value.case;
  if (!cpu || !gpu || !case_part) return;
  
  loadingImage.value = true;
  try {
    const res = await api.post('/builder/generate-image/', {
      cpu_name: cpu.nume,
      gpu_name: gpu.nume,
      case_name: case_part.nume
    });
    if (res.data.image_url) {
       generatedImageUrl.value = res.data.image_url;
    }
  } catch (err) {
    console.error(err);
    alert('A apărut o eroare la generarea imaginii.');
  } finally {
    loadingImage.value = false;
  }
}

const closeModal = () => {
  modalOpen.value = false
  selectedBuild.value = null
  modalParts.value = {}
  bottleneckData.value = null
  fpsData.value = null
  generatedImageUrl.value = null
}

// ── Încarcă în Builder ────────────────────────────────────
const loadIntoBuilder = () => {
  sessionStorage.setItem('loadBuild', JSON.stringify(modalParts.value))
  router.push('/')
}

// ── Pie chart ─────────────────────────────────────────────
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
  return cpu + gpu + 50 || '—'
})

const pieSlices = computed(() => {
  const total = parseFloat(totalPrice.value)
  if (!total) return []

  let startAngle = 0
  return partSlots.map((slot, i) => {
    const pret = parseFloat(modalParts.value[slot.key]?.pret || 0)
    const pct = total > 0 ? (pret / total) : 0
    const angle = pct * 2 * Math.PI

    const x1 = 100 + 90 * Math.sin(startAngle)
    const y1 = 100 - 90 * Math.cos(startAngle)
    const x2 = 100 + 90 * Math.sin(startAngle + angle)
    const y2 = 100 - 90 * Math.cos(startAngle + angle)
    const large = angle > Math.PI ? 1 : 0

    const path = pret > 0
      ? `M100,100 L${x1},${y1} A90,90 0 ${large},1 ${x2},${y2} Z`
      : ''

    startAngle += angle

    return {
      path,
      color: PIE_COLORS[i % PIE_COLORS.length],
      value: pret,
      label: slot.label,
      pct: (pct * 100).toFixed(1),
    }
  })
})

// ── Helpers ───────────────────────────────────────────────
const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return isNaN(d) ? '—' : d.toLocaleDateString('ro-RO')
}

onMounted(fetchSavedBuilds)
</script>

<style scoped>
.builds-container { padding: 40px 20px; color: white; }

.page-title { margin-bottom: 30px; font-size: 1.6rem; }

/* Grid carduri */
.builds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.build-card {
  background: #1a1b26;
  border: 1px solid #2a2d3e;
  border-radius: 12px;
  padding: 20px;
  transition: 0.3s;
}
.build-card:hover { transform: translateY(-4px); border-color: #3b82f6; }

.build-header {
  border-bottom: 1px solid #232533;
  margin-bottom: 15px;
  padding-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.build-header h3 { margin: 0; font-size: 1rem; }
.build-date { font-size: 0.75rem; color: #64748b; }

.detail-item { font-size: 0.85rem; color: #a9b1d6; margin-bottom: 6px; }
.total-row { display: flex; justify-content: space-between; margin-top: 12px; font-size: 0.9rem; }
.price { color: #10b981; font-weight: bold; font-size: 1.1rem; }

.build-actions { display: flex; gap: 8px; margin-top: 16px; }
.btn-view {
  flex: 1;
  background: #3b82f6;
  color: white;
  border: none;
  padding: 9px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: 0.2s;
}
.btn-view:hover { background: #2563eb; }
.btn-delete {
  background: #f43f5e;
  color: white;
  border: none;
  padding: 9px 13px;
  border-radius: 6px;
  cursor: pointer;
  transition: 0.2s;
}
.btn-delete:hover { background: #e11d48; }

/* Empty state */
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  padding: 60px 20px; background: #1a1b26;
  border: 2px dashed #2a2d3e; border-radius: 12px;
  margin-top: 30px; text-align: center;
}
.empty-icon { font-size: 3.5rem; margin-bottom: 15px; }
.empty-state h3 { color: white; margin-bottom: 10px; }
.empty-state p { color: #94a3b8; margin-bottom: 25px; max-width: 400px; line-height: 1.5; }
.btn-create-build {
  background: #3b82f6; color: white; padding: 12px 24px;
  border-radius: 8px; text-decoration: none; font-weight: 600;
  transition: 0.2s; display: inline-block;
}
.btn-create-build:hover { background: #2563eb; transform: translateY(-2px); }

/* ===== MODAL ===== */
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal {
  background: #1a1b26;
  border: 1px solid #2a2d3e;
  border-radius: 16px;
  width: 100%;
  max-width: 860px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 28px 16px;
  border-bottom: 1px solid #2a2d3e;
}
.modal-header h2 { margin: 0; font-size: 1.3rem; color: white; }
.modal-date { font-size: 0.8rem; color: #64748b; margin-top: 4px; display: block; }
.modal-close {
  background: none; border: none; color: #64748b;
  font-size: 1.2rem; cursor: pointer; padding: 4px 8px;
  border-radius: 6px; transition: 0.2s;
}
.modal-close:hover { background: #2a2d3e; color: white; }

.modal-loading {
  padding: 40px;
  text-align: center;
  color: #64748b;
}

.modal-body {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 24px;
  padding: 24px 28px;
}

.modal-section h4 {
  color: #a9b1d6;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 14px;
}

/* Piese */
.parts-grid { display: flex; flex-direction: column; gap: 8px; }
.part-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #0f1117;
  border-radius: 8px;
  border: 1px solid #2a2d3e;
}
.part-row.part-missing { opacity: 0.4; }
.part-icon { font-size: 1.1rem; width: 24px; text-align: center; }
.part-info { flex: 1; display: flex; flex-direction: column; }
.part-label { font-size: 0.7rem; color: #64748b; }
.part-name { font-size: 0.85rem; color: #c0caf5; font-weight: 500; display: flex; align-items: center; flex-wrap: wrap; }
.external-link { text-decoration: none; margin-left: 6px; font-size: 1rem; transition: transform 0.2s; display: inline-block; line-height: 1; }
.external-link:hover { transform: scale(1.2); }
.part-price { font-size: 0.85rem; color: #10b981; font-weight: 600; white-space: nowrap; }

/* Side panel */
.modal-side { display: flex; flex-direction: column; gap: 20px; }

/* Pie chart */
.chart-section {}
.chart-wrapper { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.pie-svg { width: 160px; height: 160px; }
.pie-slice { transition: opacity 0.3s; }
.pie-center-label { fill: #64748b; font-size: 11px; }
.pie-center-value { fill: #10b981; font-size: 10px; font-weight: bold; }

.pie-legend { width: 100%; display: flex; flex-direction: column; gap: 5px; }
.legend-item {
  display: flex; align-items: center; gap: 7px;
  font-size: 0.75rem; color: #a9b1d6;
}
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.legend-label { flex: 1; }
.legend-pct { color: #64748b; }

/* Sumar stats */
.summary-stats { display: flex; flex-direction: column; gap: 10px; }
.stat-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px;
  background: #0f1117;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #a9b1d6;
}
.stat-row strong { color: white; }
.stat-row strong.green { color: #10b981; }

/* Footer */
.modal-footer {
  display: flex;
  gap: 10px;
  padding: 16px 28px 24px;
  border-top: 1px solid #2a2d3e;
}

.btn-bottleneck {
  background: #f59e0b;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: 0.2s;
}
.btn-bottleneck:hover:not(:disabled) { background: #d97706; }

.btn-fps {
  background: #8b5cf6;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: 0.2s;
}
.btn-fps:hover:not(:disabled) { background: #7c3aed; }

.btn-image {
  background: #06b6d4;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: 0.2s;
}
.btn-image:hover:not(:disabled) { background: #0891b2; }

.btn-bottleneck:disabled, .btn-fps:disabled, .btn-image:disabled { opacity: 0.6; cursor: not-allowed; }

.fps-table-wrapper { background: rgba(0,0,0,0.2); padding: 5px; border-radius: 6px; margin-top: 10px;}

.btn-load-builder {
  flex: 1;
  background: #10b981;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.95rem;
  transition: 0.2s;
}
.btn-load-builder:hover { background: #059669; transform: translateY(-1px); }
.btn-cancel {
  background: #2a2d3e;
  color: #a9b1d6;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.2s;
}
.btn-cancel:hover { background: #334155; }

@media (max-width: 640px) {
  .modal-body { grid-template-columns: 1fr; }
}
</style>
