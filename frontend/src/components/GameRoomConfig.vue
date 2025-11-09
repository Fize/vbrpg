<template>
  <el-dialog
    v-model="dialogVisible"
    title="创建游戏房间"
    width="500px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="left"
    >
      <el-form-item label="游戏">
        <el-input :value="game?.name" disabled />
      </el-form-item>

      <el-form-item label="玩家人数" prop="playerCount">
        <el-select
          v-model="form.playerCount"
          placeholder="选择玩家人数"
          style="width: 100%"
        >
          <el-option
            v-for="count in playerCountOptions"
            :key="count"
            :label="`${count} 人`"
            :value="count"
          />
        </el-select>
      </el-form-item>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #title>
          <p style="margin: 0; font-size: 14px;">
            如果真实玩家不足，AI 将自动填补空位
          </p>
        </template>
      </el-alert>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :loading="creating"
          @click="handleCreate"
        >
          创建房间
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { roomsApi } from '@/services/api'
import { useGameStore } from '@/stores/game'

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  game: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'created'])

const gameStore = useGameStore()
const formRef = ref(null)
const creating = ref(false)

// Form data
const form = ref({
  playerCount: null
})

// Computed
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const playerCountOptions = computed(() => {
  if (!props.game) return []
  const options = []
  for (let i = props.game.min_players; i <= props.game.max_players; i++) {
    options.push(i)
  }
  return options
})

// Form rules
const rules = {
  playerCount: [
    { required: true, message: '请选择玩家人数', trigger: 'change' }
  ]
}

// Watch game change to set default player count
watch(() => props.game, (newGame) => {
  if (newGame) {
    form.value.playerCount = newGame.min_players
  }
}, { immediate: true })

// Methods
function handleClose() {
  dialogVisible.value = false
  formRef.value?.resetFields()
}

async function handleCreate() {
  try {
    await formRef.value?.validate()
    
    creating.value = true
    gameStore.setLoading(true)
    gameStore.clearError()

    const roomData = await roomsApi.createRoom({
      game_type_slug: props.game.slug,
      max_players: form.value.playerCount,
      min_players: props.game.min_players
    })

    ElMessage.success('房间创建成功！')
    gameStore.setCurrentRoom(roomData)
    
    handleClose()
    emit('created', roomData.code)
  } catch (error) {
    console.error('Failed to create room:', error)
    const errorMessage = error.response?.data?.detail || '创建房间失败，请重试'
    ElMessage.error(errorMessage)
    gameStore.setError(errorMessage)
  } finally {
    creating.value = false
    gameStore.setLoading(false)
  }
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
