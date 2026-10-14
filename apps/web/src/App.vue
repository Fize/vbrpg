<script setup lang="ts">
import zhCn from "element-plus/es/locale/lang/zh-cn";
import AppShell from "./components/AppShell.vue";
</script>

<template>
  <el-config-provider :locale="zhCn">
    <AppShell>
      <RouterView />
    </AppShell>
  </el-config-provider>
</template>
