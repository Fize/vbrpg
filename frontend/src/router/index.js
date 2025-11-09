import { createRouter, createWebHistory } from 'vue-router'
import GameLibrary from '@/views/GameLibrary.vue'
import GameDetails from '@/views/GameDetails.vue'
import GameRoomConfigView from '@/views/GameRoomConfigView.vue'
import GameRoomLobby from '@/views/GameRoomLobby.vue'
import GameBoard from '@/views/GameBoard.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    redirect: '/games'
  },
  {
    path: '/games',
    name: 'GameLibrary',
    component: GameLibrary,
    meta: {
      title: '游戏大厅'
    }
  },
  {
    path: '/games/:slug',
    name: 'GameDetails',
    component: GameDetails,
    meta: {
      title: '游戏详情'
    }
  },
  {
    path: '/room-config',
    name: 'GameRoomConfig',
    component: GameRoomConfigView,
    meta: {
      title: '创建房间'
    }
  },
  {
    path: '/rooms/:code',
    name: 'GameRoomLobby',
    component: GameRoomLobby,
    meta: {
      title: '游戏房间'
    }
  },
  {
    path: '/game/:code',
    name: 'GameBoard',
    component: GameBoard,
    meta: {
      title: '游戏中'
    }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: {
      title: '个人资料'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, from, next) => {
  // Set page title
  document.title = to.meta.title || 'AI 桌游平台'
  next()
})

export default router

