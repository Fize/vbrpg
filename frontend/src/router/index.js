import { createRouter, createWebHistory } from 'vue-router'
import LobbyView from '@/views/LobbyView.vue'
import GameDetails from '@/views/GameDetails.vue'
import CreateRoomView from '@/views/CreateRoomView.vue'
import RoomLobbyView from '@/views/RoomLobbyView.vue'
import WerewolfGameView from '@/views/WerewolfGameView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    redirect: '/lobby'
  },
  {
    path: '/lobby',
    name: 'Lobby',
    component: LobbyView,
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
    path: '/room/create',
    name: 'CreateRoom',
    component: CreateRoomView,
    meta: {
      title: '创建房间'
    }
  },
  {
    path: '/room/:code',
    name: 'RoomLobby',
    component: RoomLobbyView,
    meta: {
      title: '房间等待'
    }
  },
  {
    path: '/game/:code',
    name: 'GameBoard',
    component: WerewolfGameView,
    meta: {
      title: '游戏中'
    }
  },
  {
    path: '/werewolf/:code',
    name: 'WerewolfGame',
    component: WerewolfGameView,
    meta: {
      title: '狼人杀'
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

