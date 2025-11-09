<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    :close-on-press-escape="!critical"
    :show-close="!critical"
    class="error-dialog"
  >
    <div class="error-content">
      <el-icon class="error-icon" :size="48">
        <CircleClose v-if="type === 'error'" />
        <WarningFilled v-else-if="type === 'warning'" />
        <InfoFilled v-else />
      </el-icon>
      
      <div class="error-message">
        <p class="error-title">{{ message }}</p>
        <p v-if="details" class="error-details">{{ details }}</p>
      </div>
    </div>

    <div v-if="showRetry || showClose" class="error-actions">
      <el-button
        v-if="showRetry"
        type="primary"
        @click="handleRetry"
        :loading="retrying"
      >
        {{ retryText }}
      </el-button>
      <el-button
        v-if="showClose"
        @click="handleClose"
      >
        {{ closeText }}
      </el-button>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { CircleClose, WarningFilled, InfoFilled } from '@element-plus/icons-vue'

interface Props {
  modelValue?: boolean
  type?: 'error' | 'warning' | 'info'
  title?: string
  message: string
  details?: string
  critical?: boolean
  showRetry?: boolean
  showClose?: boolean
  retryText?: string
  closeText?: string
  width?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  type: 'error',
  title: '错误',
  critical: false,
  showRetry: false,
  showClose: true,
  retryText: '重试',
  closeText: '关闭',
  width: '400px'
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'retry': []
  'close': []
}>()

const retrying = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const handleRetry = async () => {
  retrying.value = true
  try {
    emit('retry')
  } finally {
    retrying.value = false
  }
}

const handleClose = () => {
  visible.value = false
  emit('close')
}
</script>

<style scoped>
.error-dialog :deep(.el-dialog__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.error-dialog :deep(.el-dialog__body) {
  padding: 24px 20px;
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.error-icon {
  flex-shrink: 0;
  margin-top: 4px;
}

.error-icon.el-icon {
  color: #f56c6c;
}

.error-icon.el-icon--warning {
  color: #e6a23c;
}

.error-icon.el-icon--info {
  color: #409eff;
}

.error-message {
  flex: 1;
}

.error-title {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  line-height: 1.5;
}

.error-details {
  margin: 8px 0 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

.error-actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
