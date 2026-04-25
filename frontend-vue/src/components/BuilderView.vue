<template>
  <div class="container builder-layout">
    
    <div class="main-panel">
      <h2>Sistemul tău</h2>
      
      <table class="builder-table">
        <thead>
          <tr>
            <th>Componentă</th>
            <th>Selecție</th>
            <th>Preț</th>
            <th>Acțiune</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="category in categories" :key="category.id">
            <td class="category-name">{{ category.name }}</td>
            
            <td class="selection">
              <span v-if="category.selectedPart">{{ category.selectedPart.name }}</span>
              <span v-else class="empty-state">Nu ai ales o componentă</span>
            </td>
            
            <td class="price">
              <span v-if="category.selectedPart">{{ category.selectedPart.price }} RON</span>
            </td>
            
            <td class="actions">
              <button 
                v-if="!category.selectedPart" 
                class="btn btn-outline"
                @click="openPartSelector(category.id)"
              >
                + Alege
              </button>
              <button 
                v-else 
                class="btn remove-btn"
                @click="removePart(category.id)"
              >
                Șterge
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="summary-panel">
      <h3>Sumar</h3>
      <div class="summary-row">
        <span>Consum Estimat:</span>
        <strong>{{ totalWattage }} W</strong>
      </div>
      <hr class="divider" />
      <div class="summary-row total">
        <span>Total:</span>
        <strong>{{ totalPrice }} RON</strong>
      </div>
      <button class="btn checkout-btn">Salvează Build-ul</button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// Structura de date (Aici vei conecta mai târziu datele din Backend)
const categories = ref([
  { id: 'cpu', name: 'Procesor (CPU)', selectedPart: null },
  { id: 'cooler', name: 'Cooler CPU', selectedPart: null },
  { id: 'motherboard', name: 'Placă de bază', selectedPart: null },
  { id: 'ram', name: 'Memorie RAM', selectedPart: null },
  { id: 'storage', name: 'Stocare (SSD/HDD)', selectedPart: null },
  { id: 'gpu', name: 'Placă Video (GPU)', selectedPart: null },
  { id: 'case', name: 'Carcasă', selectedPart: null },
  { id: 'psu', name: 'Sursă (PSU)', selectedPart: null }
])

// Simulăm ce se întâmplă când dai click pe "Alege"
const openPartSelector = (categoryId) => {
  alert(`Aici se va deschide pagina sau lista ca să alegi o piesă pentru: ${categoryId}. \nTrebuie să aducem lista de la backend!`)
  
  // Exemplu mock: adăugăm o piesă automat doar ca să vezi cum arată interfața
  const catIndex = categories.value.findIndex(c => c.id === categoryId)
  if(catIndex !== -1) {
    categories.value[catIndex].selectedPart = { 
      name: `Componentă Test ${categoryId}`, 
      price: 450, 
      wattage: 65 
    }
  }
}

// Funcția de ștergere a piesei
const removePart = (categoryId) => {
  const catIndex = categories.value.findIndex(c => c.id === categoryId)
  if(catIndex !== -1) {
    categories.value[catIndex].selectedPart = null
  }
}

// Calculăm automat prețul și consumul pe baza pieselor selectate
const totalPrice = computed(() => {
  return categories.value.reduce((sum, cat) => {
    return sum + (cat.selectedPart ? cat.selectedPart.price : 0)
  }, 0)
})

const totalWattage = computed(() => {
  return categories.value.reduce((sum, cat) => {
    return sum + (cat.selectedPart ? cat.selectedPart.wattage : 0)
  }, 0)
})
</script>

<style scoped>
.builder-layout {
  display: grid;
  grid-template-columns: 3fr 1fr;
  gap: 20px;
  margin-top: 30px;
}

.main-panel, .summary-panel {
  background-color: var(--panel-bg);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.builder-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

.builder-table th {
  text-align: left;
  padding-bottom: 15px;
  border-bottom: 2px solid var(--border-color);
  color: var(--text-muted);
}

.builder-table td {
  padding: 15px 0;
  border-bottom: 1px solid var(--border-color);
}

.category-name { font-weight: bold; width: 25%; }
.selection { width: 40%; }
.empty-state { color: var(--text-muted); font-style: italic; }
.price { width: 15%; font-weight: bold; }
.actions { width: 20%; text-align: right; }

.remove-btn {
  background-color: transparent;
  color: #ff4d4d;
  border: 1px solid #ff4d4d;
}
.remove-btn:hover { background-color: #ff4d4d; color: white; }

.summary-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 1.1rem;
}

.divider {
  border: 0;
  height: 1px;
  background: var(--border-color);
  margin: 15px 0;
}

.total {
  font-size: 1.3rem;
  color: var(--accent-color);
}

.checkout-btn {
  width: 100%;
  margin-top: 20px;
  padding: 12px;
  font-size: 1.1rem;
}

/* Pentru ecrane mici (telefoane) */
@media (max-width: 768px) {
  .builder-layout { grid-template-columns: 1fr; }
}
</style>