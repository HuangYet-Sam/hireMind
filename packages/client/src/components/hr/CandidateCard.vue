<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NAvatar, NTag, NButton, NSpace } from 'naive-ui'
import type { Candidate } from '@/api/hr/candidates'

const props = defineProps<{
  candidate: Candidate
}>()

const emit = defineEmits<{
  view: [id: string]
}>()

const statusColor = computed(() => {
  const map: Record<string, string> = { new: 'default', screening: 'warning', interviewing: 'info', offered: 'success', hired: 'success', rejected: 'error', withdrawn: 'default' }
  return map[props.candidate.status] || 'default'
})
</script>

<template>
  <NCard size="small" class="candidate-card" hoverable>
    <div class="card-header">
      <div class="user-info">
        <NAvatar :size="36" round>{{ candidate.name.charAt(0) }}</NAvatar>
        <div>
          <div class="name">{{ candidate.name }}</div>
          <div class="company">{{ candidate.current_title }} @ {{ candidate.current_company || '-' }}</div>
        </div>
      </div>
      <NTag :type="statusColor" size="small">{{ candidate.status }}</NTag>
    </div>

    <div class="card-body">
      <div class="meta-row">
        <span>{{ candidate.years_of_experience ?? '-' }} 年经验</span>
        <span>来源: {{ candidate.source }}</span>
      </div>
      <div v-if="candidate.match_score !== null" class="match-score">
        匹配度: {{ Math.round(candidate.match_score * 100) }}%
      </div>
    </div>

    <div class="card-footer">
      <NButton size="tiny" type="primary" @click="emit('view', candidate.id)">360°视图</NButton>
    </div>
  </NCard>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.candidate-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;

    .user-info {
      display: flex;
      align-items: center;
      gap: 10px;

      .name { font-weight: 600; font-size: 15px; color: $text-primary; }
      .company { font-size: 12px; color: $text-muted; }
    }
  }

  .card-body {
    .meta-row {
      display: flex;
      gap: 16px;
      font-size: 13px;
      color: $text-secondary;
      margin-bottom: 4px;
    }

    .match-score {
      font-size: 13px;
      font-weight: 500;
      color: var(--success);
    }
  }

  .card-footer {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid $border-light;
  }
}
</style>
