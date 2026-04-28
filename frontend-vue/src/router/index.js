import { createRouter, createWebHistory } from 'vue-router'
import BuilderView from '../views/BuilderView.vue'
import SavedBuildsView from '../views/SavedBuildsView.vue' 

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ACEASTA ESTE LINIA CARE ÎȚI LIPSEȘTE:
export default router