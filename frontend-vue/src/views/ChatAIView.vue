<template>
  <div class="chat-page">
    <!-- SIDEBAR STÂNGA (vizibil doar pe desktop) -->
    <div class="chat-sidebar">
      <!-- 1. AVATAR MARE AI -->
      <div class="sidebar-avatar-section">
        <div class="sidebar-avatar">
          <span class="avatar-icon">💡</span>
        </div>
        <div class="sidebar-titles">
          <h2>RigMaster AI</h2>
          <span class="sub-badge">v2.0 · Gemini Powered</span>
        </div>
      </div>

      <!-- 2. BADGE STATUS -->
      <div class="sidebar-status">
        <div class="status-badge">
          <span class="pulse-dot"></span> ONLINE
        </div>
      </div>

      <div class="sidebar-divider"></div>

      <!-- 4. CAPABILITĂȚI -->
      <div class="sidebar-capabilities">
        <h4 class="sidebar-heading">Ce poate face</h4>
        <ul class="cap-list">
          <li><span class="cap-icon">⚡</span> Recomandă build-uri pe buget</li>
          <li><span class="cap-icon">🔍</span> Analizează bottleneck-uri</li>
          <li><span class="cap-icon">💰</span> Compară prețuri din eMag/Altex</li>
          <li><span class="cap-icon">🎮</span> Estimează FPS per joc</li>
          <li><span class="cap-icon">🔧</span> Verifică compatibilitatea</li>
        </ul>
      </div>

      <div class="sidebar-divider"></div>

      <!-- 6. SESIUNE CURENTĂ -->
      <div class="sidebar-session">
        <h4 class="sidebar-heading">Sesiunea curentă</h4>
        <div class="session-stat">
          <span class="stat-label">Mesaje:</span>
          <span class="stat-value">{{ messages.length }}</span>
        </div>
        <div class="session-stat">
          <span class="stat-label">Total tokens:</span>
          <span class="stat-value">~{{ messages.length * 150 }}</span>
        </div>
      </div>

      <!-- 7. Bottom sidebar: Șterge conversația -->
      <button class="btn-clear-chat" @click="resetChat">Șterge conversația</button>
    </div>

    <!-- CONTAINER CHAT PRINCIPAL -->
    <div class="chat-main-container">
      
      <!-- HEADER CHAT -->
      <div class="chat-main-header">
        <div class="header-left">
          <div class="header-avatar-small">AI</div>
          <div class="header-titles">
            <h3 class="title">RigMaster AI</h3>
            <span class="subtitle">Asistent PC · Powered by Gemini</span>
          </div>
        </div>
        
        <div class="header-right">
          <div class="badge-active">+ Active</div>
          <button class="btn-icon-settings" title="Setări" @click="resetChat">⚙️</button>
        </div>
      </div>

      <!-- ZONA MESAJE -->
      <div class="chat-messages-area" ref="chatBox">
        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message-wrapper', msg.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <!-- Avatar User / AI -->
          <div class="msg-avatar" :class="msg.role === 'user' ? 'user-avatar' : 'ai-avatar'">
            {{ msg.role === 'user' ? '👤' : 'AI' }}
          </div>

          <div class="msg-content">
            <div class="msg-header-row">
              <span class="msg-author">{{ msg.role === 'ai' ? 'RigMaster AI' : 'Tu' }}</span>
              <span class="msg-time">{{ new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }}</span>
            </div>

            <div class="msg-bubble">
              <p class="msg-text" v-html="formatMessage(msg.text)"></p>
            </div>

            <!-- CARDURI COMPONENTE RECOMANDATE (AI Message Only) -->
            <div class="recommended-components" v-if="msg.role === 'ai' && msg.isBuild && msg.buildData?.build">
              <div 
                class="comp-card" 
                v-for="(comp, type) in msg.buildData.build" 
                :key="type" 
                v-if="comp"
              >
                <button class="comp-close" title="Remove">×</button>
                <div class="comp-header-row">
                  <span class="comp-type">{{ type }}</span>
                  <span class="comp-price-small">{{ comp.pret }} RON</span>
                </div>
                <img :src="comp.imagine_url || 'https://placehold.co/100x90/111827/00e5ff?text=' + type" alt="Component" class="comp-img" />
                <h4 class="comp-name">{{ (comp.nume || "").substring(0, 25) }}...</h4>
                <p class="comp-desc">Recomandat pt. sistemul tău</p>
                <div class="comp-price-large">{{ comp.pret }} RON</div>
                <button class="comp-add-btn" @click="incarcaInBuilder(msg.buildData)">Add to Build</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Typing Indicator -->
        <div v-if="isTyping" class="message-wrapper ai-message">
          <div class="msg-avatar ai-avatar">AI</div>
          <div class="msg-content">
            <div class="msg-header-row">
              <span class="msg-author">RigMaster AI</span>
            </div>
            <div class="msg-bubble">
              <div class="typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- STAREA "NEAUTENTIFICAT" -->
      <div class="auth-gate" v-if="!isLoggedIn">
        <div class="auth-gate-icon">🔐</div>
        <h3>Autentifică-te pentru a continua</h3>
        <p>RigMaster AI îți poate recomanda build-uri personalizate, analiza bottleneck-uri și estima FPS-ul pentru jocurile tale.</p>
        <div class="auth-gate-actions">
          <button class="btn-primary" @click="$router.push('/login')">Log In</button>
          <button class="btn-outline" @click="$router.push('/register')">Creează cont gratuit</button>
        </div>
        <p class="auth-gate-note">✓ Gratuit · ✓ Fără card · ✓ Acces instant</p>
      </div>

      <!-- INPUT BAR -->
      <div class="input-bar-container" :class="{ 'is-disabled': !isLoggedIn }">
        <div class="input-wrapper" :title="!isLoggedIn ? 'Autentifică-te pentru a scrie' : ''">
          <textarea 
            v-model="userInput" 
            @keyup.enter.prevent="sendMessage"
            class="chat-input"
            placeholder="Întreabă RigMaster despre build-ul tău..." 
            :disabled="isTyping || !isLoggedIn"
            rows="1"
          ></textarea>
          
          <div class="input-actions-right">
            <button class="btn-icon-attachment">✨</button>
            <button @click="sendMessage" :disabled="isTyping || !userInput.trim() || !isLoggedIn" class="send-btn">
              ➔
            </button>
          </div>
        </div>
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
/* =====================================================================
   BACKGROUND GLOBAL AL PAGINII
===================================================================== */
.chat-page {
  display: flex;
  height: calc(100vh - 64px);
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 24px 0;
  gap: 24px;
  background: radial-gradient(ellipse 80% 60% at 50% 0%,
    rgba(124,58,237,0.12) 0%, transparent 70%),
    radial-gradient(ellipse 60% 40% at 80% 100%,
    rgba(37,99,235,0.08) 0%, transparent 60%),
    #08070f;
  font-family: 'Inter', sans-serif;
}

/* =====================================================================
   SIDEBAR STÂNGA
===================================================================== */
.chat-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 16px;
  padding: 20px;
  height: calc(100% - 24px); /* Păstrăm spațiu jos din cauza paddingului general */
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
}

.sidebar-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 16px;
}
.sidebar-avatar {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  background: linear-gradient(135deg, #5b21b6, #2563eb);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.avatar-icon {
  font-size: 32px;
  color: white;
}
.sidebar-titles {
  text-align: center;
}
.sidebar-titles h2 {
  font-weight: bold;
  color: #fff;
  margin: 0 0 4px;
  font-size: 1.1rem;
}
.sub-badge {
  font-size: 0.75rem;
  color: #8b9db5;
}

.sidebar-status {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
.status-badge {
  background: rgba(0,229,160,0.1);
  border: 1px solid rgba(0,229,160,0.25);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 0.75rem;
  color: #00e5a0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
.pulse-dot {
  width: 8px;
  height: 8px;
  background: #00e5a0;
  border-radius: 50%;
  animation: pulse-dot-anim 1.5s infinite;
}
@keyframes pulse-dot-anim {
  0% { opacity: 1; }
  50% { opacity: 0.3; }
  100% { opacity: 1; }
}

.sidebar-divider {
  height: 1px;
  background: rgba(255,255,255,0.07);
  margin: 16px 0;
}

.sidebar-heading {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #8b9db5;
  margin: 0 0 12px;
}
.cap-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cap-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: #c4c9d4;
}
.cap-icon {
  font-size: 16px;
}

.sidebar-session {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.session-stat {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
}
.stat-label {
  color: #8b9db5;
}
.stat-value {
  color: #00e5ff;
  font-weight: 600;
}

.btn-clear-chat {
  width: 100%;
  background: transparent;
  border: 1px solid rgba(239,68,68,0.3);
  color: rgba(239,68,68,0.7);
  padding: 10px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: auto;
}
.btn-clear-chat:hover {
  border-color: #ef4444;
  color: #ef4444;
}

/* =====================================================================
   CONTAINER CHAT PRINCIPAL
===================================================================== */
.chat-main-container {
  background: rgba(10, 8, 25, 0.9);
  border: 1px solid rgba(124, 58, 237, 0.3);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
  height: calc(100% - 24px); /* Păstrăm spațiu jos */
  margin-bottom: 24px;
  overflow: hidden;
  box-shadow: 0 0 60px rgba(124,58,237,0.15), inset 0 0 80px rgba(37,99,235,0.05);
  position: relative; /* for auth-gate overlay */
}

/* HEADER CHAT */
.chat-main-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-avatar-small {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #2563eb);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: bold;
  font-size: 0.8rem;
}
.header-titles {
  display: flex;
  flex-direction: column;
}
.header-titles .title {
  font-weight: 700;
  font-size: 0.95rem;
  color: #f0f4ff;
  margin: 0;
}
.header-titles .subtitle {
  font-size: 0.75rem;
  color: #8b9db5;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge-active {
  background: rgba(0,229,160,0.12);
  border: 1px solid rgba(0,229,160,0.3);
  color: #00e5a0;
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 0.75rem;
}
.btn-icon-settings {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255,255,255,0.05);
  color: #8b9db5;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.btn-icon-settings:hover {
  background: rgba(255,255,255,0.1);
}

/* ZONA MESAJE */
.chat-messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chat-messages-area::-webkit-scrollbar { width: 4px; }
.chat-messages-area::-webkit-scrollbar-track { background: transparent; }
.chat-messages-area::-webkit-scrollbar-thumb { background: rgba(124,58,237,0.4); border-radius: 4px; }

.message-wrapper {
  display: flex;
  width: 100%;
}

.msg-content {
  display: flex;
  flex-direction: column;
  max-width: 80%;
}

/* AI Message */
.ai-message {
  flex-direction: row;
  gap: 12px;
  align-items: flex-start;
}
.ai-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #2563eb);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: bold;
  font-size: 0.65rem;
  flex-shrink: 0;
}
.ai-message .msg-bubble {
  background: rgba(37,99,235,0.08);
  border: 1px solid rgba(124,58,237,0.2);
  border-radius: 4px 14px 14px 14px;
  padding: 12px 16px;
}
.ai-message .msg-header-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  padding-left: 4px;
}
.ai-message .msg-author {
  font-size: 0.8rem;
  font-weight: 700;
  color: #818cf8;
}

/* User Message */
.user-message {
  flex-direction: row-reverse;
  gap: 12px;
  align-items: flex-start;
}
.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b9db5;
  font-size: 14px;
  flex-shrink: 0;
}
.user-message .msg-bubble {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px 4px 14px 14px;
  padding: 12px 16px;
}
.user-message .msg-header-row {
  display: flex;
  flex-direction: row-reverse;
  justify-content: space-between;
  margin-bottom: 4px;
  padding-right: 4px;
}
.user-message .msg-author {
  font-size: 0.8rem;
  font-weight: 700;
  color: #94a3b8;
}

.msg-time {
  font-size: 0.72rem;
  color: #4a5568;
}

.msg-text {
  font-size: 0.9rem;
  color: #e2e8f0;
  line-height: 1.6;
  margin: 0;
  word-wrap: break-word;
}

/* =====================================================================
   CARDURI COMPONENTE RECOMANDATE
===================================================================== */
.recommended-components {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  overflow-x: auto;
  margin-top: 14px;
  padding-bottom: 10px;
}
.recommended-components::-webkit-scrollbar { height: 4px; }
.recommended-components::-webkit-scrollbar-track { background: transparent; }
.recommended-components::-webkit-scrollbar-thumb { background: rgba(0, 229, 255, 0.3); border-radius: 4px; }

.comp-card {
  min-width: 170px;
  max-width: 200px;
  flex-shrink: 0;
  background: rgba(15, 10, 30, 0.9);
  border: 1px solid rgba(124, 58, 237, 0.35);
  border-radius: 12px;
  padding: 12px;
  position: relative;
  transition: all 0.2s ease;
}
.comp-card:hover {
  border-color: rgba(0, 229, 255, 0.5);
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.15);
}

.comp-close {
  position: absolute;
  top: 8px; right: 8px;
  width: 20px; height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #8b9db5;
  font-size: 0.75rem;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.comp-close:hover { background: rgba(255, 255, 255, 0.2); }

.comp-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.comp-type {
  font-size: 0.72rem;
  font-weight: 700;
  color: #00e5ff;
  text-transform: uppercase;
}
.comp-price-small {
  font-size: 0.72rem;
  color: #8b9db5;
  margin-right: 20px;
}
.comp-img {
  width: 100%;
  height: 90px;
  object-fit: contain;
  margin-bottom: 8px;
}
.comp-name {
  font-weight: 700;
  font-size: 0.88rem;
  color: #fff;
  margin: 4px 0;
}
.comp-desc {
  font-size: 0.75rem;
  color: #8b9db5;
  margin-bottom: 6px;
}
.comp-price-large {
  font-size: 1rem;
  font-weight: 700;
  color: #00e5a0;
  margin-bottom: 10px;
}
.comp-add-btn {
  width: 100%;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.comp-add-btn:hover {
  background: rgba(0, 229, 160, 0.15);
  border-color: #00e5a0;
  color: #00e5a0;
}

/* =====================================================================
   TYPING INDICATOR
===================================================================== */
.typing-dots {
  display: flex;
  align-items: center;
  height: 100%;
}
.typing-dots span {
  display: inline-block; 
  width: 6px; 
  height: 6px; 
  background: #818cf8; 
  border-radius: 50%; 
  margin: 0 3px; 
  animation: typing-anim 0.6s infinite ease both;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes typing-anim {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

/* =====================================================================
   STAREA NEAUTENTIFICAT (AUTH GATE)
===================================================================== */
.auth-gate {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  width: 90%;
  max-width: 380px;
  background: rgba(10, 8, 25, 0.95);
  padding: 30px;
  border-radius: 16px;
  border: 1px solid rgba(124,58,237,0.3);
  box-shadow: 0 0 40px rgba(0,0,0,0.8);
  z-index: 10;
}
.auth-gate-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}
.auth-gate h3 {
  font-size: 1.2rem;
  font-weight: 700;
  color: #f0f4ff;
  margin: 0 0 8px;
}
.auth-gate p {
  font-size: 0.88rem;
  color: #8b9db5;
  line-height: 1.6;
  margin: 0 0 20px;
}
.auth-gate-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.btn-primary {
  background: #7c3aed;
  color: #fff;
  border-radius: 8px;
  padding: 10px 24px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s;
}
.btn-primary:hover {
  background: #6d28d9;
}
.btn-outline {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
  border-radius: 8px;
  padding: 10px 24px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s;
}
.btn-outline:hover {
  border-color: rgba(255,255,255,0.4);
}
.auth-gate-note {
  font-size: 0.75rem !important;
  color: #4a5568 !important;
  margin: 16px 0 0 !important;
}

/* =====================================================================
   INPUT BAR
===================================================================== */
.input-bar-container {
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: rgba(5,4,15,0.8);
}
.input-bar-container.is-disabled {
  opacity: 0.4;
}
.input-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px;
  padding: 10px 14px;
  transition: border-color 0.2s;
}
.input-wrapper:focus-within {
  border-color: rgba(124,58,237,0.5);
  box-shadow: 0 0 0 3px rgba(124,58,237,0.1);
}
.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e2e8f0;
  font-size: 0.9rem;
  resize: none;
  max-height: 120px;
}
.chat-input::placeholder {
  color: #4a5568;
}
.input-actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-icon-attachment {
  width: 32px;
  height: 32px;
  background: rgba(255,255,255,0.05);
  border-radius: 8px;
  border: none;
  color: #8b9db5;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-icon-attachment:hover {
  background: rgba(255,255,255,0.1);
}
.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #2563eb);
  border: none;
  color: #fff;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.send-btn:hover:not(:disabled) {
  filter: brightness(1.15);
  box-shadow: 0 0 16px rgba(124,58,237,0.4);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* =====================================================================
   RESPONSIVE
===================================================================== */
@media (max-width: 768px) {
  .chat-sidebar {
    display: none;
  }
  .chat-page {
    padding: 0;
    gap: 0;
  }
  .chat-main-container {
    border-radius: 0;
    border-left: none;
    border-right: none;
    height: calc(100vh - 64px); /* Păstrăm tot ecranul - navbar */
    margin-bottom: 0;
  }
  .user-message .msg-bubble, .ai-message .msg-bubble {
    max-width: 90%;
  }
  .auth-gate {
    width: 90%;
    padding: 20px;
  }
}
</style>
