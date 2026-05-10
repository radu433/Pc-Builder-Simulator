import { createRouter, createWebHistory } from 'vue-router'
import BuilderView from '../views/BuilderView.vue'
import SavedBuildsView from '../views/SavedBuildsView.vue' 
import LoginView from '../views/LogInView.vue'
import RegisterView from '../views/RegisterView.vue'
import ProfileView from '../views/ProfileView.vue'
import DocumentatiiView from '../views/DocumentatieView.vue'

const routes = [
  {
    path: '/',
    name: 'PCBuilder',
    component: BuilderView
  },
  {
    path: '/completed-builds',
    name: 'CompletedBuilds',
    component: SavedBuildsView
  },
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView
  },
  { path: '/login', 
    name: 'Login', 
    component: LoginView },
  { path: '/register', 
    name: 'Register', 
    component: RegisterView },
  {
      path: '/documentatii',
      name: 'documentatii',
      component: DocumentatiiView 
    },
    {
      path: '/ghid/:id',
      name: 'ghid-detaliu',
      component: () => import('../views/GhidView.vue')
},
{
  path: '/chat-ai',
  name: 'chat-ai',
  component: () => import('../views/ChatAIView.vue')
}
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router