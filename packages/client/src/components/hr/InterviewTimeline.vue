<script setup lang="ts">
import type { Interview } from '@/api/hr/interviews'

defineProps<{
  interviews: Interview[]
}>()

const statusColorMap: Record<string, string> = {
  scheduled: '#f0a020',
  confirmed: '#4a90d9',
  in_progress: '#18a058',
  completed: '#888',
  cancelled: '#d03050',
  no_show: '#d03050',
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="interview-timeline">
    <div v-if="!interviews.length" class="empty">暂无面试记录</div>
    <div v-for="(item, idx) in interviews" :key="item.id" class="timeline-item">
      <div class="timeline-dot" :style="{ background: statusColorMap[item.status] }" />
      <div v-if="idx < interviews.length - 1" class="timeline-line" />
      <div class="timeline-content">
        <div class="timeline-header">
          <span class="round">第{{ item.round }}轮 · {{ item.type }}</span>
          <span class="date">{{ formatDate(item.scheduled_at) }}</span>
        </div>
        <div class="timeline-body">
          <span>{{ item.candidate_name }} — {{ item.position_title }}</span>
          <span v-if="item.score !== null" class="score">评分: {{ item.score }}/10</span>
        </div>
        <div v-if="item.ai_summary" class="ai-note">{{ item.ai_summary }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.interview-timeline {
  position: relative;
  padding-left: 24px;
}

.timeline-item {
  position: relative;
  padding-bottom: 20px;

  .timeline-dot {
    position: absolute;
    left: -24px;
    top: 4px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    z-index: 1;
  }

  .timeline-line {
    position: absolute;
    left: -19px;
    top: 16px;
    width: 2px;
    height: calc(100% - 16px);
    background: $border-light;
  }
}

.timeline-content {
  .timeline-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;

    .round { font-weight: 500; font-size: 14px; color: $text-primary; }
    .date { font-size: 12px; color: $text-muted; }
  }

  .timeline-body {
    font-size: 13px;
    color: $text-secondary;
    display: flex;
    gap: 12px;

    .score { color: var(--success); font-weight: 500; }
  }

  .ai-note {
    margin-top: 4px;
    font-size: 12px;
    color: $text-muted;
    padding: 4px 8px;
    background: rgba(var(--accent-info-rgb), 0.06);
    border-radius: 4px;
  }
}

.empty {
  text-align: center;
  padding: 20px;
  color: $text-muted;
  font-size: 14px;
}
</style>
