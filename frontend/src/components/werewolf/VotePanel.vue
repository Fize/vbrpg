<template>
  <div class="vote-panel">
    <div class="panel-header">
      <h3 class="panel-title">投票阶段</h3>
      <p class="panel-desc">选择一名玩家进行投票，或选择弃票</p>
    </div>
    
    <div v-if="hasVoted" class="voted-status">
      <el-icon :size="32" color="var(--el-color-success)"><CircleCheck /></el-icon>
      <span v-if="myVote">已投票给 {{ getPlayerName(myVote) }}</span>
      <span v-else>已弃票</span>
    </div>
    
    <div v-else class="vote-content">
      <!-- 候选人列表 -->
      <div class="candidate-list">
        <div 
          v-for="candidate in candidates" 
          :key="candidate.id"
          class="candidate-item"
          :class="{ selected: selectedCandidate?.id === candidate.id }"
          @click="selectCandidate(candidate)"
        >
          <div class="candidate-avatar">
            <span class="seat-number">{{ candidate.seat_number || '?' }}</span>
          </div>
          <div class="candidate-info">
            <span class="candidate-name">{{ candidate.name || candidate.username }}</span>
            <span v-if="candidate.vote_count > 0" class="vote-count">
              {{ candidate.vote_count }} 票
            </span>
          </div>
          <el-icon v-if="selectedCandidate?.id === candidate.id" class="check-icon">
            <Check />
          </el-icon>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="vote-actions">
        <el-button size="large" @click="handleAbstain">
          弃票
        </el-button>
        <el-button 
          type="primary" 
          size="large"
          :disabled="!selectedCandidate"
          @click="handleVote"
        >
          确认投票
        </el-button>
      </div>
    </div>
    
    <!-- 投票结果预览 -->
    <div v-if="showResults" class="vote-results">
      <h4 class="results-title">当前票数</h4>
      <div class="results-list">
        <div 
          v-for="candidate in sortedCandidates" 
          :key="candidate.id"
          class="result-item"
        >
          <span class="result-name">{{ candidate.name }}</span>
          <div class="result-bar">
            <div 
              class="result-fill" 
              :style="{ width: getVotePercent(candidate.vote_count) + '%' }"
            ></div>
          </div>
          <span class="result-count">{{ candidate.vote_count || 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { CircleCheck, Check } from '@element-plus/icons-vue'

const props = defineProps({
  candidates: {
    type: Array,
    default: () => []
  },
  myVote: {
    type: String,
    default: null
  },
  hasVoted: {
    type: Boolean,
    default: false
  },
  showResults: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['vote', 'abstain'])

const selectedCandidate = ref(null)

// 按票数排序的候选人
const sortedCandidates = computed(() => {
  return [...props.candidates].sort((a, b) => (b.vote_count || 0) - (a.vote_count || 0))
})

// 最高票数
const maxVotes = computed(() => {
  return Math.max(...props.candidates.map(c => c.vote_count || 0), 1)
})

// 获取玩家名称
function getPlayerName(playerId) {
  const player = props.candidates.find(c => c.id === playerId)
  return player?.name || player?.username || '未知'
}

// 计算票数百分比
function getVotePercent(voteCount) {
  return ((voteCount || 0) / maxVotes.value) * 100
}

// 选择候选人
function selectCandidate(candidate) {
  if (props.hasVoted) return
  selectedCandidate.value = selectedCandidate.value?.id === candidate.id ? null : candidate
}

// 确认投票
function handleVote() {
  if (selectedCandidate.value) {
    emit('vote', selectedCandidate.value)
  }
}

// 弃票
function handleAbstain() {
  emit('abstain')
}
</script>

<style scoped>
.vote-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  text-align: center;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px;
}

.panel-desc {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.voted-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: #f0f9eb;
  border-radius: 12px;
  color: var(--el-color-success);
  font-size: 16px;
  font-weight: 500;
}

.vote-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border: 2px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.candidate-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.candidate-item.selected {
  background: #ecf5ff;
  border-color: var(--el-color-primary);
}

.candidate-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.seat-number {
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.candidate-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.candidate-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.vote-count {
  font-size: 12px;
  color: var(--el-color-danger);
}

.check-icon {
  color: var(--el-color-primary);
}

.vote-actions {
  display: flex;
  gap: 12px;
}

.vote-actions .el-button {
  flex: 1;
}

.vote-results {
  padding: 16px;
  background: #fafafa;
  border-radius: 12px;
}

.results-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-name {
  width: 80px;
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-bar {
  flex: 1;
  height: 8px;
  background: #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}

.result-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--el-color-primary) 0%, var(--el-color-primary-light-3) 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.result-count {
  width: 30px;
  text-align: right;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

/* 滚动条样式 */
.candidate-list::-webkit-scrollbar {
  width: 6px;
}

.candidate-list::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

/* 响应式 */
@media (max-width: 768px) {
  .candidate-list {
    max-height: 200px;
  }
}
</style>
