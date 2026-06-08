<template>
  <div class="chat-container container">
    <div class="chat-wrapper">
      
      <div class="chat-header">
        <div class="ai-avatar">🤖</div>
        <div class="ai-info">
          <h2>AI PC Architect</h2>
          <span class="status">● Online</span>
        </div>
        <button class="btn-reset" @click="resetChat" title="Conversație nouă">🗑️</button>
      </div>

      <div class="chat-messages" ref="chatBox">
        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message-row', msg.role === 'user' ? 'user-row' : 'ai-row']"
        >
          <div :class="['message-bubble', msg.role === 'user' ? 'user-bubble' : 'ai-bubble']">
            
            <p class="msg-text" v-html="formatMessage(msg.text)"></p>

            <div v-if="msg.isBuild && msg.buildData" class="build-card">
              <h3 class="build-title">🖥️ Sistem Recomandat</h3>
              
              <!-- Lista componentelor -->
              <ul class="build-parts-list">
                <li v-if="msg.buildData.build && msg.buildData.build.cpu">
                  <strong>CPU:</strong> {{ msg.buildData.build.cpu.nume }} 
                  <span class="part-price">{{ msg.buildData.build.cpu.pret }} RON</span>
                </li>
                <li v-if="msg.buildData.build && msg.buildData.build.gpu">
                  <strong>GPU:</strong> {{ msg.buildData.build.gpu.nume }}
                  <span class="part-price">{{ msg.buildData.build.gpu.pret }} RON</span>
                </li>
                <li v-if="msg.buildData.build && msg.buildData.build.motherboard">
                  <strong>Placă de bază:</strong> {{ msg.buildData.build.motherboard.nume }}
                  <span class="part-price">{{ msg.buildData.build.motherboard.pret }} RON</span>
                </li>
                <li v-if="msg.buildData.build && msg.buildData.build.ram">
                  <strong>RAM:</strong> {{ msg.buildData.build.ram.nume }}
                  <span class="part-price">{{ msg.buildData.build.ram.pret }} RON</span>
                </li>
                <li v-if="msg.buildData.build && msg.buildData.build.storage">
                  <strong>Storage:</strong> {{ msg.buildData.build.storage.nume }}
                  <span class="part-price">{{ msg.buildData.build.storage.pret }} RON</span>
                </li>
                <li v-if="msg.buildData.build && msg.buildData.build.psu">
                  <strong>Sursă:</strong> {{ msg.buildData.build.psu.nume }}
                  <span class="part-price">{{ msg.buildData.build.psu.pret }} RON</span>
                </li>
              </ul>

              <!-- Bottleneck info -->
              <div v-if="msg.buildData.bottleneck" class="build-section">
                <div :class="['bottleneck-badge', msg.buildData.bottleneck.are_bottleneck ? 'bottleneck-warn' : 'bottleneck-ok']">
                  {{ msg.buildData.bottleneck.are_bottleneck 
                    ? `⚠️ Bottleneck ${msg.buildData.bottleneck.componenta_limitatoare} (${msg.buildData.bottleneck.procentaj_bottleneck}%)`
                    : '✅ Echilibru CPU/GPU bun' 
                  }}
                </div>
              </div>

              <!-- Compatibilitate -->
              <div v-if="msg.buildData.compatibilitate" class="build-section">
                <div :class="['compat-badge', msg.buildData.compatibilitate.compatibil ? 'compat-ok' : 'compat-warn']">
                  {{ msg.buildData.compatibilitate.compatibil ? '✅ Toate componentele sunt compatibile' : '⚠️ Probleme de compatibilitate' }}
                </div>
                <ul v-if="msg.buildData.compatibilitate.probleme && msg.buildData.compatibilitate.probleme.length" class="compat-issues">
                  <li v-for="(prob, i) in msg.buildData.compatibilitate.probleme" :key="i">{{ prob }}</li>
                </ul>
              </div>

              <!-- FPS jocuri -->
              <div v-if="msg.buildData.fps_jocuri_cerute && msg.buildData.fps_jocuri_cerute.length" class="build-section">
                <h4 class="section-title">🎮 FPS Estimat</h4>
                <div class="fps-grid">
                  <div v-for="joc in msg.buildData.fps_jocuri_cerute" :key="joc.joc" class="fps-card">
                    <span class="fps-game">{{ joc.joc }}</span>
                    <span :class="['fps-rating', 'rating-' + (joc.rating || 'B').toLowerCase()]">{{ joc.rating }}</span>
                    <span class="fps-preset">{{ joc.preset_optim }}</span>
                  </div>
                </div>
              </div>

              <!-- Rating general -->
              <div v-if="msg.buildData.rating_general" class="build-section">
                <div class="rating-general">
                  Rating: <span :class="'rating-' + msg.buildData.rating_general.toLowerCase()">{{ msg.buildData.rating_general }}</span>
                </div>
              </div>

              <div class="build-footer">
                <span class="build-price">Total: {{ msg.buildData.pret_total }} RON</span>
                <span v-if="msg.buildData.diferenta > 0" class="build-savings">
                  Economie: {{ msg.buildData.diferenta }} RON
                </span>
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

      <!-- Mesaj dacă nu e logat -->
      <div v-if="!isLoggedIn" class="login-prompt">
        <p>🔒 Trebuie să fii autentificat pentru a folosi AI PC Architect.</p>
        <router-link to="/login" class="btn-login">Autentifică-te</router-link>
      </div>

      <div v-else class="chat-input-area">
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
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const userInput = ref('')
const messages = ref([])
const isTyping = ref(false)
const chatBox = ref(null)

// Verificare autentificare
const isLoggedIn = computed(() => {
  return !!localStorage.getItem('access_token')
})

// ── 1. Funcție pentru Scroll ──
const scrollToBottom = async () => {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

// ── 2. Funcție pentru ștergerea conversației ──
const resetChat = () => {
  localStorage.removeItem('ai_chat_history')
  messages.value = []
  initChat()
}

// ── 3. Formatare mesaj (bold, newlines) ──
const formatMessage = (text) => {
  if (!text) return ''
  // Escapăm HTML-ul pentru securitate, apoi aplicăm formatarea minimală
  let safe = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // Bold: **text**
  safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  // Newlines
  safe = safe.replace(/\n/g, '<br>')
  return safe
}

// ── 4. Inițializare & Încărcare Memorie (Cache) ──
const initChat = () => {
  const istoricSalvat = localStorage.getItem('ai_chat_history')
  
  if (istoricSalvat) {
    try {
      messages.value = JSON.parse(istoricSalvat)
    } catch {
      localStorage.removeItem('ai_chat_history')
      messages.value = []
    }
    scrollToBottom()
  } else {
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

// ── 5. Salvare Automată în Cache ──
watch(messages, (newMessages) => {
  localStorage.setItem('ai_chat_history', JSON.stringify(newMessages))
}, { deep: true })


// ── 6. Trimiterea mesajului către Django Backend ──
const sendMessage = async () => {
  if (!userInput.value.trim() || isTyping.value) return

  const userText = userInput.value
  messages.value.push({ role: 'user', text: userText })
  userInput.value = ''
  isTyping.value = true
  scrollToBottom()

  try {
    const token = localStorage.getItem('access_token')
    
    const response = await axios.post(
      import.meta.env.VITE_AI_AGENT_URL + '/chat/',
      {
        mesaj_nou: userText,
        istoric: messages.value.map(m => ({ role: m.role, text: m.text }))
      },
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const raspunsAI = response.data

    messages.value.push({
      role: 'ai',
      text: raspunsAI.mesaj_text,
      isBuild: raspunsAI.contine_build,
      buildData: raspunsAI.build_data
    })

  } catch (error) {
    if (error.response && error.response.status === 401) {
      messages.value.push({
        role: 'ai',
        text: '🔒 Sesiunea ta a expirat. Te rog să te autentifici din nou.',
        isBuild: false
      })
    } else {
      messages.value.push({
        role: 'ai',
        text: 'Scuze, am întâmpinat o eroare de conexiune cu serverul. Te rog să încerci din nou.',
        isBuild: false
      })
    }
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

// ── 7. Logica butonului "Încarcă în Builder" ──
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

.ai-info { flex-grow: 1; }
.ai-info h2 { color: white; font-size: 1.2rem; margin-bottom: 3px; }
.ai-info .status { color: #10b981; font-size: 0.85rem; font-weight: 600; }

.btn-reset {
  background: none;
  border: 1px solid #2a2d3e;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 1.2rem;
  transition: 0.2s;
}
.btn-reset:hover { border-color: #ef4444; background: rgba(239,68,68,0.1); }

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

/* ── Build Card ── */
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
.build-parts-list li { margin-bottom: 6px; display: flex; justify-content: space-between; }
.build-parts-list strong { color: #94a3b8; }
.part-price { color: #10b981; font-weight: 600; font-size: 0.85rem; }

.build-section { margin: 10px 0; }
.section-title { color: #c084fc; font-size: 0.95rem; margin-bottom: 8px; }

/* Bottleneck badge */
.bottleneck-badge {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}
.bottleneck-ok { background: rgba(16,185,129,0.15); color: #10b981; }
.bottleneck-warn { background: rgba(245,158,11,0.15); color: #f59e0b; }

/* Compatibilitate */
.compat-badge {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}
.compat-ok { background: rgba(16,185,129,0.15); color: #10b981; }
.compat-warn { background: rgba(239,68,68,0.15); color: #ef4444; }
.compat-issues { list-style: disc; padding-left: 20px; margin-top: 6px; font-size: 0.82rem; color: #fca5a5; }

/* FPS Grid */
.fps-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.fps-card {
  background: #1a1b26;
  border: 1px solid #2a2d3e;
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
}
.fps-game { color: #e2e8f0; font-weight: 600; }
.fps-preset { color: #94a3b8; }

/* Rating-uri */
.rating-general { font-size: 0.9rem; color: #94a3b8; }
.rating-s { color: #10b981; font-weight: bold; font-size: 1.2em; }
.rating-a { color: #3b82f6; font-weight: bold; font-size: 1.2em; }
.rating-b { color: #f59e0b; font-weight: bold; font-size: 1.2em; }
.rating-c { color: #ef4444; font-weight: bold; font-size: 1.2em; }
.rating-d { color: #6b7280; font-weight: bold; font-size: 1.2em; }

.fps-rating {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.8rem;
}
.fps-rating.rating-s { background: rgba(16,185,129,0.2); }
.fps-rating.rating-a { background: rgba(59,130,246,0.2); }
.fps-rating.rating-b { background: rgba(245,158,11,0.2); }
.fps-rating.rating-c { background: rgba(239,68,68,0.2); }

.build-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.build-price { font-weight: bold; color: #10b981; font-size: 1.1rem; }
.build-savings { color: #3b82f6; font-size: 0.85rem; }

.btn-load-build {
  background: #a855f7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: 0.2s;
}
.btn-load-build:hover { background: #c084fc; }

/* ── Login prompt ── */
.login-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background-color: #0f111a;
  border-top: 1px solid #2a2d3e;
  gap: 10px;
}
.login-prompt p { color: #94a3b8; margin: 0; }
.btn-login {
  background: #3b82f6;
  color: white;
  padding: 10px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: bold;
  transition: 0.2s;
}
.btn-login:hover { background: #2563eb; }

/* ── Input area ── */
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