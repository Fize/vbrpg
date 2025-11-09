<template>
  <el-card class="account-upgrade">
    <template #header>
      <div class="card-header">
        <h3>升级账户</h3>
        <el-tag type="warning">访客模式</el-tag>
      </div>
    </template>

    <div class="upgrade-content">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="upgrade-notice"
      >
        <template #title>
          您当前使用的是访客账户
        </template>
        升级为永久账户后，您的游戏数据将永久保存，并可以自定义用户名。
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="upgrade-form"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="当前用户名">
          <el-input :value="currentUsername" disabled />
        </el-form-item>

        <el-form-item label="新用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名（3-20个字符）"
            :maxlength="20"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="loading"
            :disabled="!form.username"
          >
            {{ loading ? '升级中...' : '立即升级' }}
          </el-button>
          <el-button @click="handleCancel">
            取消
          </el-button>
        </el-form-item>
      </el-form>

      <div class="upgrade-benefits">
        <h4>升级后您将获得：</h4>
        <ul>
          <li><el-icon><Check /></el-icon> 永久保存游戏数据</li>
          <li><el-icon><Check /></el-icon> 自定义用户名</li>
          <li><el-icon><Check /></el-icon> 完整的游戏统计</li>
          <li><el-icon><Check /></el-icon> 更多即将推出的功能</li>
        </ul>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  currentUsername: {
    type: String,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['upgrade', 'cancel'])

const formRef = ref(null)
const form = reactive({
  username: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为 3-20 个字符', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/,
      message: '用户名只能包含字母、数字、下划线和中文',
      trigger: 'blur'
    },
    {
      validator: (rule, value, callback) => {
        if (value.startsWith('Guest_')) {
          callback(new Error('不能使用 Guest_ 开头的用户名'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    emit('upgrade', form.username)
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped>
.account-upgrade {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 20px;
}

.upgrade-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.upgrade-notice {
  margin-bottom: 8px;
}

.upgrade-form {
  margin-top: 16px;
}

.upgrade-benefits {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
}

.upgrade-benefits h4 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 16px;
}

.upgrade-benefits ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.upgrade-benefits li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #606266;
}

.upgrade-benefits li .el-icon {
  color: #67c23a;
  font-size: 18px;
}
</style>
