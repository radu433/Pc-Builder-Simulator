import { createRouter, createWebHistory } from 'vue-router'
import BuilderView from '../views/BuilderView.vue'
import SavedBuildsView from '../views/SavedBuildsView.vue' 
import LoginView from '../views/LogInView.vue'
import RegisterView from '../views/RegisterView.vue'
import ProfileView from '../views/ProfileView.vue'

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
    component: RegisterView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router