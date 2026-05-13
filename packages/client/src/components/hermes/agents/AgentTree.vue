<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NTag, NStatistic, NSpin, NEmpty } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { fetchAgentTree, type AgentsDashboardResponse } from '@/api/hermes/agents'
import AgentTreeNode from './AgentTreeNode.vue'
import GatewayStatusList from './GatewayStatusList.vue'
import GroupChatAgentList from './GroupChatAgentList.vue'
import JobAgentList from './JobAgentList.vue'

const { t } = useI18n()
const loading = ref(false)
const data = ref<AgentsDashboardResponse | null>(null)

function platformState(info: unknown): string {
  if (typeof info === 'string') return info
  if (info && typeof info === 'object' && 'state' in info) return (info as { state: string }).state
  return 'unknown'
}

onMounted(async () => {
  loading.value = true
  try {
    data.value = await fetchAgentTree()
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="agents-dashboard">
    <NSpin v-if="loading" size="large" class="loading-spin" />

    <template v-else-if="data">
      <!-- Platforms -->
      <div v-if="Object.keys(data.platforms).length > 0" class="platforms-row">
        <div class="section-label">{{ t('agents.platforms') }}</div>
        <div class="platforms-list">
          <NTag
            v-for="(info, name) in data.platforms"
            :key="name"
            :type="platformState(info) === 'connected' ? 'success' : 'default'"
            size="small"
            round
          >
            {{ name }}
          </NTag>
        </div>
      </div>

      <!-- Summary stats -->
      <div class="dashboard-header">
        <NStatistic :label="t('agents.activeAgents')" :value="data.activeAgents" />
        <NStatistic :label="t('agents.gateways')" :value="data.gateways.length" />
        <NStatistic :label="t('agents.groupChatAgents')" :value="data.groupChatAgents.length" />
        <NStatistic :label="t('agents.scheduledJobs')" :value="data.jobs.length" />
      </div>

      <!-- Section 1: Gateways -->
      <GatewayStatusList :gateways="data.gateways" />

      <!-- Section 2: Group Chat Agents -->
      <GroupChatAgentList :agents="data.groupChatAgents" />

      <!-- Section 3: Scheduled Jobs -->
      <JobAgentList :jobs="data.jobs" />

      <!-- Section 4: Delegation Chains -->
      <div class="delegation-section">
        <div class="section-label">{{ t('agents.delegationChains') }}</div>
        <div v-if="!data.sqliteAvailable" class="sqlite-warning">
          <NTag type="warning" size="small" round>{{ t('agents.sqliteUnavailable') }}</NTag>
        </div>
        <div v-else-if="data.delegationTree.length === 0" class="empty-tree">
          <NEmpty :description="t('agents.noDelegations')" size="small" />
        </div>
        <div v-else class="tree-body">
          <AgentTreeNode v-for="node in data.delegationTree" :key="node.session_id" :node="node" />
        </div>
      </div>
    </template>

    <NEmpty v-else :description="t('agents.noData')" />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.agents-dashboard {
  padding: 16px 20px;
}

.loading-spin {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.platforms-row {
  margin-bottom: 16px;
}

.section-label {
  font-size: 12px;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.platforms-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dashboard-header {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid $border-light;
}

.delegation-section {
  margin-bottom: 20px;
}

.sqlite-warning {
  margin-top: 8px;
}

.empty-tree {
  padding: 12px 0;
}

.tree-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 8px;
}
</style>
