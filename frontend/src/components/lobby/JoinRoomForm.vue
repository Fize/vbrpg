<template>
  <div class="join-room-form">
    <h2>加入游戏房间</h2>
    
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="room-code">房间代码</label>
        <input
          id="room-code"
          ref="roomCodeInput"
          v-model="roomCode"
          type="text"
          placeholder="请输入房间代码"
          maxlength="6"
          :disabled="isLoading"
          @input="handleInput"
          class="room-code-input"
        />
        <p class="hint">6位字母数字组合（自动转换为大写）</p>
      </div>

      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <button
        type="submit"
        :disabled="!isValidCode || isLoading"
        class="submit-button"
      >
        {{ isLoading ? '加入中...' : '加入房间' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { roomsApi } from '@/services/api'

const router = useRouter()
const emit = defineEmits(['join-success'])

// Component state
const roomCode = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const roomCodeInput = ref(null)

// Computed properties
const isValidCode = computed(() => {
  return /^[A-Z0-9]{6}$/.test(roomCode.value)
})

// Methods
const handleInput = (event) => {
  // Convert to uppercase and remove non-alphanumeric characters
  const value = event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
  roomCode.value = value
  
  // Clear error message when user starts typing
  if (errorMessage.value) {
    errorMessage.value = ''
  }
}

const handleSubmit = async () => {
  if (!isValidCode.value || isLoading.value) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    // Call API to join room
    const response = await roomsApi.joinRoom(roomCode.value)
    
    // Emit success event with room data
    emit('join-success', response)
    
    // Navigate to lobby view
    router.push({
      name: 'lobby',
      params: { code: roomCode.value }
    })
  } catch (error) {
    // Handle different error types
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || ''

      if (status === 404) {
        errorMessage.value = '房间不存在，请检查房间代码'
      } else if (status === 409) {
        if (detail.toLowerCase().includes('full')) {
          errorMessage.value = '房间已满，无法加入'
        } else if (detail.toLowerCase().includes('started') || detail.toLowerCase().includes('progress')) {
          errorMessage.value = '游戏已开始，无法加入'
        } else if (detail.toLowerCase().includes('duplicate') || detail.toLowerCase().includes('already')) {
          errorMessage.value = '您已在该房间中'
        } else {
          errorMessage.value = '无法加入房间：' + detail
        }
      } else {
        errorMessage.value = '加入房间失败，请稍后重试'
      }
    } else {
      errorMessage.value = '网络错误，请检查您的连接'
    }
  } finally {
    isLoading.value = false
  }
}

// Lifecycle
onMounted(() => {
  // Autofocus on input field
  if (roomCodeInput.value) {
    roomCodeInput.value.focus()
  }
})
</script>

<style scoped>
.join-room-form {
  max-width: 400px;
  margin: 2rem auto;
  padding: 2rem;
  background: var(--color-background-soft);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

h2 {
  margin: 0 0 1.5rem;
  text-align: center;
  color: var(--color-heading);
}

.form-group {
  margin-bottom: 1rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--color-text);
}

.room-code-input {
  width: 100%;
  padding: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  text-align: center;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  border: 2px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  transition: border-color 0.3s;
}

.room-code-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.room-code-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.error-message {
  padding: 0.75rem;
  margin-bottom: 1rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
  color: #c33;
  font-size: 0.875rem;
}

.submit-button {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: var(--color-primary);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.submit-button:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.submit-button:active:not(:disabled) {
  transform: translateY(0);
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
