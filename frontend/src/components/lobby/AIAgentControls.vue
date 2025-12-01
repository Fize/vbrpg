<template>
  <div class="ai-agent-controls">
    <div class="controls-header">
      <h3>AI玩家管理</h3>
      <button
        class="add-ai-button"
        :disabled="!lobbyStore.hasCapacity || isAddingAI"
        @click="handleAddAI"
      >
        <span v-if="!isAddingAI">+ 添加AI玩家</span>
        <span v-else>添加中...</span>
      </button>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>

    <!-- AI Agents List -->
    <div v-if="lobbyStore.aiAgents.length > 0" class="ai-agents-list">
      <div
        v-for="agent in lobbyStore.aiAgents"
        :key="agent.id"
        class="ai-agent-item"
      >
        <span class="ai-agent-name">{{ agent.name }}</span>
        <button
          class="remove-ai-button"
          :disabled="isRemovingAI === agent.id"
          @click="handleRemoveAI(agent.id)"
          :title="`移除 ${agent.name}`"
        >
          ×
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>暂无AI玩家</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { roomsApi } from '@/services/api'
import { useLobbyStore } from '@/stores/lobby'

const lobbyStore = useLobbyStore()

const isAddingAI = ref(false)
const isRemovingAI = ref(null)
const errorMessage = ref('')

const handleAddAI = async () => {
  if (!lobbyStore.hasCapacity) {
    errorMessage.value = '房间已满，无法添加更多AI玩家'
    return
  }

  isAddingAI.value = true
  errorMessage.value = ''

  try {
    const response = await roomsApi.addAIAgent(lobbyStore.roomCode)
    
    // Add AI agent to store
    lobbyStore.addParticipant(response.ai_agent)
  } catch (error) {
    console.error('Failed to add AI agent:', error)
    
    if (error.response) {
      if (error.response.status === 409) {
        errorMessage.value = '房间已满或游戏已开始'
      } else if (error.response.status === 403) {
        errorMessage.value = '无权限添加AI玩家'
      } else {
        errorMessage.value = '添加AI玩家失败，请重试'
      }
    } else {
      errorMessage.value = '网络错误，请检查连接'
    }
  } finally {
    isAddingAI.value = false
  }
}

const handleRemoveAI = async (agentId) => {
  isRemovingAI.value = agentId
  errorMessage.value = ''

  try {
    await roomsApi.removeAIAgent(lobbyStore.roomCode, agentId)
    
    // Remove AI agent from store
    lobbyStore.removeParticipant(agentId)
  } catch (error) {
    console.error('Failed to remove AI agent:', error)
    
    if (error.response) {
      if (error.response.status === 403) {
        errorMessage.value = '无权限移除AI玩家'
      } else if (error.response.status === 404) {
        errorMessage.value = 'AI玩家不存在'
      } else if (error.response.status === 409) {
        errorMessage.value = '游戏已开始，无法移除AI玩家'
      } else {
        errorMessage.value = '移除AI玩家失败，请重试'
      }
    } else {
      errorMessage.value = '网络错误，请检查连接'
    }
  } finally {
    isRemovingAI.value = null
  }
}
</script>

<style scoped>
.ai-agent-controls {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.controls-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.controls-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.add-ai-button {
  padding: 8px 16px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.add-ai-button:hover:not(:disabled) {
  background: #45a049;
  transform: translateY(-1px);
}

.add-ai-button:disabled {
  background: #cccccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.error-message {
  background: #ffebee;
  color: #c62828;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 14px;
  border-left: 4px solid #c62828;
}

.ai-agents-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-agent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  transition: background 0.2s;
}

.ai-agent-item:hover {
  background: #eeeeee;
}

.ai-agent-name {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 500;
}

.remove-ai-button {
  width: 24px;
  height: 24px;
  border: none;
  background: #f44336;
  color: white;
  border-radius: 50%;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-ai-button:hover:not(:disabled) {
  background: #d32f2f;
  transform: scale(1.1);
}

.remove-ai-button:disabled {
  background: #cccccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: #9e9e9e;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}
</style>
