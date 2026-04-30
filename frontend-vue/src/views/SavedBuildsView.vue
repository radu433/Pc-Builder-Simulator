<template>
  <div class="container builds-container">
    <h2 class="page-title">📂 Build-urile tale salvate</h2>

    <div v-if="loading" class="loading">Se încarcă lista...</div>
    
    <div v-else-if="builds.length === 0" class="empty-state">
      <div class="empty-icon">📁</div>
      <h3>Niciun build salvat</h3>
      <p>Nu ai salvat nicio configurație până acum. Creează una nouă și va apărea aici.</p>
      <!-- Am schimbat to="/pc-builder" in to="/" -->
      <router-link to="/" class="btn-create-build">Creează primul tău Build</router-link>
    </div>

    <div v-else class="builds-grid">
      <div v-for="build in builds" :key="build.id" class="build-card">
        <div class="build-header">
          <h3>{{ build.nume || 'Configurație PC' }}</h3>
          <span class="build-date">{{ formatDate(build.data_creare) }}</span>
        </div>

        <div class="build-details">
          <div class="detail-item"><strong>CPU:</strong> {{ build.cpu_nume || 'Nesecat' }}</div>
          <div class="detail-item"><strong>GPU:</strong> {{ build.gpu_nume || 'Neselectat' }}</div>
          <div class="total-row">
            <span>Preț Total:</span>
            <span class="price">{{ build.pret_total }} RON</span>
          </div>
        </div>

        <div class="build-actions">
          <button @click="editBuild(build)" class="btn-edit">✏️ Modifică</button>
          <button @click="deleteBuild(build.id)" class="btn-delete">🗑️ Șterge</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../plugins/axios'
import { useRouter } from 'vue-router'

const builds = ref([])
const loading = ref(true)
const router = useRouter()

const fetchSavedBuilds = async () => {
  try {
    const token = localStorage.getItem('access_token'); 

    if (!token) {
      console.error("Nu s-a găsit niciun token.");
      router.push('/login');
      return;
    }

    // REPARARE: Folosim 'api' în loc de 'axios' nespecificat[cite: 2]
    // Instanța 'api' are deja URL-ul de bază configurat
    const response = await api.get('saved-builds/', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    builds.value = response.data;
  } catch (error) {
    console.error("Eroare la preluarea build-urilor:", error);
  } finally {
    loading.value = false;
  }
};

const deleteBuild = async (id) => {
  if (confirm("Sigur vrei să ștergi această configurație?")) {
    try {
      await api.delete(`saved-builds/${id}/`)
      builds.value = builds.value.filter(b => b.id !== id)
      alert("Build șters cu succes!")
    } catch (err) {
      alert("Eroare la ștergere.")
    }
  }
}

const editBuild = (build) => {
  // Trimitem utilizatorul inapoi in builder cu datele build-ului
  // Poti folosi un store (Pinia) sau query params
  router.push({ name: 'pc-builder', query: { edit: build.id } })
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('ro-RO')
}

onMounted(fetchSavedBuilds)
</script>

<style scoped>
.builds-container { padding: 40px 20px; color: white; }
.builds-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.build-card { background: #1a1b26; border: 1px solid #2a2d3e; border-radius: 12px; padding: 20px; transition: 0.3s; }
.build-card:hover { transform: translateY(-5px); border-color: #3b82f6; }
.build-header { border-bottom: 1px solid #232533; margin-bottom: 15px; padding-bottom: 10px; }
.price { color: #10b981; font-weight: bold; font-size: 1.2rem; }
.build-actions { display: flex; gap: 10px; margin-top: 20px; }
.btn-edit { background: #3b82f6; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; flex: 1; }
.btn-delete { background: #f43f5e; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: #1a1b26;
  border: 2px dashed #2a2d3e; /* Chenar punctat */
  border-radius: 12px;
  margin-top: 30px;
  text-align: center;
}

.empty-icon {
  font-size: 3.5rem;
  margin-bottom: 15px;
}

.empty-state h3 {
  color: white;
  margin-bottom: 10px;
  font-size: 1.5rem;
}

.empty-state p {
  color: #94a3b8;
  margin-bottom: 25px;
  max-width: 400px;
  line-height: 1.5;
}

.btn-create-build {
  background: #3b82f6; /* Albastrul temei */
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none; /* Scoate sublinierea link-ului */
  font-weight: 600;
  transition: all 0.2s ease;
  display: inline-block;
}

.btn-create-build:hover {
  background: #2563eb; /* Un albastru un pic mai închis la hover */
  transform: translateY(-2px); /* Se ridică puțin când pui mouse-ul */
}
</style>