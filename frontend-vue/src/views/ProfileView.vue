<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../plugins/axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const loadingProfile = ref(true)
const saving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')
const jocNou = ref('')

const profile = ref({ username: localStorage.getItem('username') || 'Cont' })
const userInitial = computed(() => profile.value.username?.charAt(0).toUpperCase() || 'U')

// Verifică numele cheilor (buget_max, cpu_preferat, etc.) să coincidă cu baza de date Django
const form = ref({
  buget_max: 0,
  cpu_preferat: 'Oricare',
  gpu_preferat: 'Oricare',
  rezolutie_dorita: '1080p',
  locatie: 'Romania',
  jocuri_pref: [], // Folosim numele scurt din ultima ta variantă de cod
})

const cpuOptions = [
  { value: 'Oricare', label: 'Oricare' },
  { value: 'AMD', label: 'AMD' },
  { value: 'Intel', label: 'Intel' },
]

const gpuOptions = [
  { value: 'Oricare', label: 'Oricare' },
  { value: 'NVIDIA', label: 'NVIDIA' },
  { value: 'AMD', label: 'AMD' },
  { value: 'Intel', label: 'Intel Arc' },
]

const rezolutieOptions = [
  { value: '1080p', label: '1080p' },
  { value: '1440p', label: '1440p' },
  { value: '4K', label: '4K' },
]

const fetchProfile = async () => {
  const token = localStorage.getItem('access_token')
  if (!token) { router.push('/login'); return }

  try {
    // Cerem datele folosind instanța API configurată
    const res = await api.get('accounts/profile/')
    profile.value = res.data
    
    // Populăm formularul cu datele primite de la server
    form.value = {
      buget_max: res.data.buget_max || 0,
      cpu_preferat: res.data.cpu_preferat || 'Oricare',
      gpu_preferat: res.data.gpu_preferat || 'Oricare',
      rezolutie_dorita: res.data.rezolutie_dorita || '1080p',
      locatie: res.data.locatie || 'Romania',
      jocuri_pref: res.data.jocuri_pref || [],
    }
  } catch (err) {
    console.error('Eroare la fetch profil:', err)
    if (err.response?.status === 401) router.push('/login')
  } finally {
    loadingProfile.value = false
  }
}

const salveazaProfil = async () => {
  saving.value = true
  saveSuccess.value = false
  saveError.value = ''
  
  try {
    // Trimitem întreg obiectul form către Django
    await api.put('accounts/profile/', form.value)
    saveSuccess.value = true
    
    // Resetăm mesajul de succes după 3 secunde
    setTimeout(() => saveSuccess.value = false, 3000)
  } catch (err) {
    saveError.value = 'Eroare la salvare. Verificați datele.'
    console.error('Eroare salvare:', err)
  } finally {
    saving.value = false
  }
}

const adaugaJoc = () => {
  const joc = jocNou.value.trim()
  if (joc && !form.value.jocuri_pref.includes(joc)) {
    form.value.jocuri_pref.push(joc)
  }
  jocNou.value = ''
}

const stergeJoc = (index) => {
  form.value.jocuri_pref.splice(index, 1)
}

onMounted(fetchProfile)
</script>

<template>
  <div class="container profile-container">
    <div class="profile-layout">
      <div class="profile-sidebar">
        <div class="avatar-section">
          <div class="avatar-big">{{ userInitial }}</div>
          <div class="avatar-name">{{ profile.username }}</div>
          <div class="avatar-role">Utilizator</div>
        </div>
        <div class="sidebar-links">
          <router-link to="/completed-builds" class="sidebar-link">📂 Build-urile mele</router-link>
          <span class="sidebar-link active">⚙️ Preferințele mele</span>
        </div>
      </div>

      <div class="profile-main">
        <div class="profile-header">
          <h2>⚙️ Preferințele mele</h2>
          <p>Acestea vor fi folosite de agentul AI pentru a genera build-uri personalizate.</p>
        </div>

        <div v-if="loadingProfile" class="loading">Se încarcă profilul...</div>

        <div v-else class="profile-form">
          <div class="form-section">
            <h4>💰 Buget</h4>
            <div class="form-row">
              <label>Buget maxim (RON)</label>
              <input type="number" v-model="form.buget_max" min="0" />
            </div>
          </div>

          <div class="form-section">
            <h4>🖥️ Preferințe Hardware</h4>
            <div class="form-row">
              <label>Procesor (CPU)</label>
              <div class="select-group">
                <button v-for="opt in cpuOptions" :key="opt.value" class="select-btn"
                  :class="{ active: form.cpu_preferat === opt.value }" @click="form.cpu_preferat = opt.value">
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <div class="form-row">
              <label>Placă video (GPU)</label>
              <div class="select-group">
                <button v-for="opt in gpuOptions" :key="opt.value" class="select-btn"
                  :class="{ active: form.gpu_preferat === opt.value }" @click="form.gpu_preferat = opt.value">
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <div class="form-row">
              <label>Rezoluție dorită</label>
              <div class="select-group">
                <button v-for="opt in rezolutieOptions" :key="opt.value" class="select-btn"
                  :class="{ active: form.rezolutie_dorita === opt.value }" @click="form.rezolutie_dorita = opt.value">
                  {{ opt.label }}
                </button>
              </div>
            </div>
          </div>

          <div class="form-section">
            <h4>📍 Locație</h4>
            <div class="form-row">
              <input type="text" v-model="form.locatie" placeholder="ex: Romania" />
            </div>
          </div>

          <div class="form-section">
            <h4>🎮 Jocuri preferate</h4>
            <div class="jocuri-input-row">
              <input type="text" v-model="jocNou" placeholder="Adaugă un joc..." @keydown.enter.prevent="adaugaJoc" />
              <button class="btn-add-joc" @click="adaugaJoc">+ Adaugă</button>
            </div>
            <div class="jocuri-tags">
              <span v-for="(joc, i) in form.jocuri_pref" :key="i" class="joc-tag">
                {{ joc }} <button @click="stergeJoc(i)">✕</button>
              </span>
            </div>
          </div>

          <div class="form-actions">
            <button class="btn-save" :disabled="saving" @click="salveazaProfil">
              {{ saving ? '⏳ Se salvează...' : '💾 Salvează Preferințele' }}
            </button>
            <span v-if="saveSuccess" class="save-success">✅ Salvat!</span>
            <span v-if="saveError" class="save-error">{{ saveError }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Folosește stilurile pe care le-am stabilit anterior pentru .select-btn.active și .select-group */
.profile-container { padding: 40px 20px; color: white; }
.profile-layout { display: grid; grid-template-columns: 220px 1fr; gap: 30px; max-width: 900px; margin: 0 auto; }
.profile-sidebar, .profile-main { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 12px; padding: 25px; height: fit-content; }
.avatar-big { width: 60px; height: 60px; border-radius: 50%; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin: 0 auto 10px; }
.sidebar-link { display: block; padding: 10px; color: #a9b1d6; text-decoration: none; border-radius: 7px; margin-bottom: 5px; }
.sidebar-link.active { background: #232533; color: #3b82f6; }
.form-section { margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #2a2d3e; }
.form-row label { display: block; margin-bottom: 8px; font-size: 0.9rem; color: #94a3b8; }
.select-group { display: flex; gap: 10px; flex-wrap: wrap; }
.select-btn { padding: 8px 18px; border-radius: 20px; border: 1px solid #2a2d3e; background: transparent; color: #a9b1d6; cursor: pointer; transition: 0.2s; }
.select-btn.active { background: rgba(59, 130, 246, 0.2); border-color: #3b82f6; color: #3b82f6; font-weight: 600; }
.btn-save { background: #10b981; color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-weight: 700; }
.btn-save:disabled { opacity: 0.5; }
input { width: 100%; background: #0f111a; border: 1px solid #2a2d3e; padding: 10px; border-radius: 7px; color: white; }
.jocuri-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.joc-tag { background: #232533; border: 1px solid #2a2d3e; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem; }
.joc-tag button { background: none; border: none; color: #64748b; margin-left: 5px; cursor: pointer; }
</style>