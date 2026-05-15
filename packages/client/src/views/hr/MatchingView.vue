<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NSelect, NButton, NSpin, NEmpty, NGrid, NGridItem, NProgress } from 'naive-ui'
import { usePositionStore } from '@/stores/hr/positions'
import { useMatchingStore } from '@/stores/hr/matching'

const positionStore = usePositionStore()
const matchingStore = useMatchingStore()
const selectedPositionId = ref<string | null>(null)

onMounted(() => {
  positionStore.fetchPositions({ status: 'open' })
})

async function handleMatch() {
  if (!selectedPositionId.value) return
  await matchingStore.matchCandidatesForPosition(selectedPositionId.value)
}
</script>

<template>
  <div class="matching-view">
    <header class="page-header">
      <h2 class="header-title">智能匹配</h2>
      <p class="header-desc">AI驱动的岗位-候选人匹配矩阵</p>
    </header>

    <!-- Position selector -->
    <div class="match-controls">
      <NSelect
        v-model:value="selectedPositionId"
        :options="positionStore.positions.map(p => ({ label: p.title, value: p.id }))"
        placeholder="选择一个在招岗位"
        style="width: 300px;"
      />
      <NButton type="primary" :disabled="!selectedPositionId" :loading="matchingStore.loading" @click="handleMatch">
        开始匹配
      </NButton>
    </div>

    <!-- Match Matrix -->
    <NSpin :show="matchingStore.loading">
      <div v-if="matchingStore.matches.length" class="match-matrix">
        <NGrid :cols="1" :y-gap="12">
          <NGridItem v-for="match in matchingStore.matches" :key="match.id">
            <NCard size="small" class="match-row">
              <div class="match-info">
                <span class="candidate-name">{{ match.candidate_name }}</span>
                <NProgress
                  type="line"
                  :percentage="Math.round(match.overall_score * 100)"
                  :color="match.overall_score >= 0.8 ? '#18a058' : match.overall_score >= 0.6 ? '#f0a020' : '#d03050'"
                  :height="16"
                  style="width: 200px;"
                />
                <span class="score-text">{{ Math.round(match.overall_score * 100) }}%</span>
              </div>
              <div v-if="match.suggestions?.length" class="match-explanation">
                {{ match.suggestions.join('；') }}
              </div>
            </NCard>
          </NGridItem>
        </NGrid>
      </div>
      <NEmpty v-else description="选择岗位后点击匹配按钮查看结果" />
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.matching-view {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 4px;
  }

  .header-desc {
    font-size: 14px;
    color: $text-muted;
    margin: 0;
  }
}

.match-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.match-row {
  .match-info {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .candidate-name {
    font-weight: 500;
    min-width: 120px;
  }

  .score-text {
    font-weight: 600;
    min-width: 50px;
    text-align: right;
  }

  .match-explanation {
    margin-top: 8px;
    font-size: 13px;
    color: $text-muted;
  }
}
</style>
