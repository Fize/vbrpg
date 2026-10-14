<script setup lang="ts">
import { computed } from "vue";
import { sessionState } from "../stores/session";

const user = computed(() => sessionState.user);
const roleLabel = computed(() => (user.value?.role === "admin" ? "管理员" : "普通用户"));

function formatDate(value: string | undefined): string {
  return value === undefined ? "—" : new Date(value).toLocaleString();
}
</script>

<template>
  <section class="lobby">
    <header class="page-head">
      <h1>大厅</h1>
      <p class="page-sub">当前阶段仅开放账号与模型配置；游戏目录、对局与邀请将在后续阶段提供。</p>
    </header>

    <el-card class="panel" shadow="never">
      <template #header>
        <span class="panel-title">我的账号</span>
      </template>

      <el-descriptions v-if="user" :column="2" border>
        <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="user.role === 'admin' ? 'warning' : 'info'" effect="plain" size="small">
            {{ roleLabel }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="账号状态">
          <el-tag :type="user.active ? 'success' : 'danger'" effect="plain" size="small">
            {{ user.active ? "正常" : "已停用" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(user.createdAt) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="panel" shadow="never">
      <el-empty description="游戏大厅将在后续阶段开放">
        <p class="empty-note">本阶段的验收范围：管理员建号与登录、Provider/模型统一配置。</p>
      </el-empty>
    </el-card>
  </section>
</template>

<style scoped>
.page-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin-bottom: var(--space-lg);
}

.page-sub {
  font-size: var(--text-base);
  color: var(--muted);
}

.panel {
  margin-bottom: var(--space-md);
}

.panel-title {
  font-size: var(--text-base);
  font-weight: 600;
}

.empty-note {
  font-size: var(--text-sm);
  color: var(--muted);
}
</style>
