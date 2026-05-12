<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AgentTree from '@/components/hermes/agents/AgentTree.vue'

const { t } = useI18n()
</script>

<template>
  <div class="agents-view">
    <header class="page-header">
      <h2 class="header-title">{{ t('agents.title') }}</h2>
    </header>
    <div class="agents-content">
      <AgentTree />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.agents-view {
  height: calc(100 * var(--vh));
  display: flex;
  flex-direction: column;
}

.agents-content {
  flex: 1;
  overflow-y: auto;
}
</style>
