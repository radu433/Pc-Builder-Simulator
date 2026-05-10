<template>
  <div class="chat-container container">
    <div class="chat-wrapper">
      
      <div class="chat-header">
        <div class="ai-avatar">🤖</div>
        <div class="ai-info">
          <h2>AI PC Architect</h2>
          <span class="status">● Online</span>
        </div>
      </div>

      <div class="chat-messages" ref="chatBox">
        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message-row', msg.role === 'user' ? 'user-row' : 'ai-row']"
        >
          <div :class="['message-bubble', msg.role === 'user' ? 'user-bubble' : 'ai-bubble']">
            
            <p class="msg-text">{{ msg.text }}</p>

            <div v-if="msg.isBuild" class="build-card">
              <h3 class="build-title">Sistem Recomandat</h3>
              <ul class="build-parts-list">
                <li v-if="msg.buildData.cpu"><strong>CPU:</strong> {{ msg.buildData.cpu.nume }}</li>
                <li v-if="msg.buildData.gpu"><strong>GPU:</strong> {{ msg.buildData.gpu.nume }}</li>
                <li v-if="msg.buildData.motherboard"><strong>Placă de bază:</strong> {{ msg.buildData.motherboard.nume }}</li>
                <li v-if="msg.buildData.ram"><strong>RAM:</strong> {{ msg.buildData.ram.nume }}</li>
              </ul>
              <div class="build-footer">
                <span class="build-price">Total Estimat: {{ msg.buildData.totalPrice }} RON</span>
                <button @click="incarcaInBuilder(msg.buildData)" class="btn-load-build">
                  ⚡ Încarcă în Builder
                </button>
              </div>
            </div>

          </div>
        </div>

        <div v-if="isTyping" class="message-row ai-row">
          <div class="message-bubble ai-bubble typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <input 
          v-model="userInput" 
          @keyup.enter="sendMessage"
          type="text" 
          placeholder="Ex: Vreau un PC de 5000 RON pentru CS2 și programare..." 
          :disabled="isTyping"
        />
        <button @click="sendMessage" :disabled="isTyping || !userInput.trim()" class="send-btn">
          Trimite
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const userInput = ref('')
const messages = ref([])
const isTyping = ref(false)
const chatBox = ref(null)

// ── 1. Funcție pentru Scroll ──
const scrollToBottom = async () => {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

// ── 2. Funcție pentru ștergerea conversației (Opțional, un buton de reset) ──
const resetChat = () => {
  localStorage.removeItem('ai_chat_history')
  messages.value = []
  initChat()
}

// ── 3. Inițializare & Încărcare Memorie (Cache) ──
const initChat = () => {
  const istoricSalvat = localStorage.getItem('ai_chat_history')
  
  if (istoricSalvat) {
    // Dacă avem istoric, îl încărcăm
    messages.value = JSON.parse(istoricSalvat)
    scrollToBottom()
  } else {
    // Dacă e prima dată, generăm salutul
    const username = localStorage.getItem('username')
    const textSalut = username 
      ? `Salut, ${username}! 👋 Sunt asistentul tău AI. Ce PC vrei să construim astăzi și ce buget ai la dispoziție?`
      : `Salut! 👋 Sunt asistentul tău AI. Pentru a-ți asambla PC-ul perfect, te rog să-mi spui: ce buget ai și pentru ce îl vei folosi?`
    
    messages.value.push({ role: 'ai', text: textSalut, isBuild: false })
  }
}

onMounted(() => {
  initChat()
})

// ── 4. Salvare Automată în Cache ──
// De fiecare dată când 'messages' se modifică, salvăm automat în localStorage
watch(messages, (newMessages) => {
  localStorage.setItem('ai_chat_history', JSON.stringify(newMessages))
}, { deep: true })


// ── 5. Trimiterea mesajului real către Python ──
const sendMessage = async () => {
  if (!userInput.value.trim() || isTyping.value) return

  const userText = userInput.value
  // Adăugăm mesajul userului pe ecran
  messages.value.push({ role: 'user', text: userText })
  userInput.value = ''
  isTyping.value = true
  scrollToBottom()

  try {
    // AICI FACEM LEGĂTURA CU PYTHON (FastAPI)
    // Trimitem tot istoricul conversației ca AI-ul să aibă context
    const response = await axios.post(import.meta.env.VITE_AI_AGENT_URL + '/chat-architect', {
      mesaj_nou: userText,
      istoric: messages.value.map(m => ({ role: m.role, text: m.text }))
    })

    const raspunsAI = response.data

    // Adăugăm răspunsul de la Python pe ecran
    messages.value.push({
      role: 'ai',
      text: raspunsAI.mesaj_text,
      isBuild: raspunsAI.contine_build,
      buildData: raspunsAI.build_data // Va fi null dacă încă mai pune întrebări
    })

  } catch (error) {
    console.error("Eroare la comunicarea cu AI-ul:", error)
    messages.value.push({
      role: 'ai',
      text: 'Scuze, am întâmpinat o eroare de conexiune cu serverul neuronal. Te rog să încerci din nou.',
      isBuild: false
    })
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

// ── 6. Logica butonului "Încarcă în Builder" ──
const incarcaInBuilder = (buildData) => {
  localStorage.setItem('pending_ai_build', JSON.stringify(buildData))
  router.push({ path: '/' })
}
</script>

<style scoped>
.chat-container {
  display: flex;
  justify-content: center;
  padding: 30px 15px;
}

.chat-wrapper {
  width: 100%;
  max-width: 800px;
  background-color: #1a1b26;
  border: 1px solid #2a2d3e;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  height: 75vh;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 20px;
  background-color: #0f111a;
  border-bottom: 1px solid #2a2d3e;
}

.ai-avatar {
  font-size: 2rem;
  background: rgba(168, 85, 247, 0.2);
  border-radius: 50%;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.ai-info h2 { color: white; font-size: 1.2rem; margin-bottom: 3px; }
.ai-info .status { color: #10b981; font-size: 0.85rem; font-weight: 600; }

.chat-messages {
  flex-grow: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-row { display: flex; width: 100%; }
.user-row { justify-content: flex-end; }
.ai-row { justify-content: flex-start; }

.message-bubble {
  max-width: 75%;
  padding: 12px 18px;
  border-radius: 18px;
  font-size: 0.95rem;
  line-height: 1.5;
}

.user-bubble {
  background-color: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}

.ai-bubble {
  background-color: #232533;
  color: #e2e8f0;
  border-bottom-left-radius: 4px;
  border: 1px solid #2a2d3e;
}

/* Stiluri pentru Cardul de Build Generat */
.build-card {
  margin-top: 15px;
  background-color: #0f111a;
  border: 1px solid #a855f7;
  border-radius: 12px;
  padding: 15px;
  color: white;
}

.build-title { color: #c084fc; font-size: 1.1rem; margin-bottom: 10px; border-bottom: 1px solid #2a2d3e; padding-bottom: 8px;}
.build-parts-list { list-style: none; padding: 0; margin-bottom: 15px; font-size: 0.9rem;}
.build-parts-list li { margin-bottom: 6px; }
.build-parts-list strong { color: #94a3b8; }

.build-footer { display: flex; justify-content: space-between; align-items: center; }
.build-price { font-weight: bold; color: #10b981; }

.btn-load-build {
  background: #a855f7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: 0.2s;
}
.btn-load-build:hover { background: #c084fc; }

.chat-input-area {
  display: flex;
  padding: 20px;
  background-color: #0f111a;
  border-top: 1px solid #2a2d3e;
  gap: 10px;
}

.chat-input-area input {
  flex-grow: 1;
  background-color: #1a1b26;
  border: 1px solid #2a2d3e;
  padding: 15px;
  border-radius: 8px;
  color: white;
  font-size: 1rem;
}
.chat-input-area input:focus { outline: none; border-color: #a855f7; }

.send-btn {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 0 25px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: 0.2s;
}
.send-btn:hover:not(:disabled) { background-color: #2563eb; }
.send-btn:disabled { background-color: #3f4455; color: #94a3b8; cursor: not-allowed; }

/* Animație Typing */
.typing-indicator span {
  display: inline-block; width: 6px; height: 6px; background-color: #94a3b8; border-radius: 50%; margin: 0 2px; animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
</style>