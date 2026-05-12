<script setup lang="ts">
import { ref } from 'vue'
import { NTag, NEmpty } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import type { JobAgentInfo } from '@/api/hermes/agents'

defineProps<{ jobs: JobAgentInfo[] }>()

const { t } = useI18n()
const expandedJob = ref<string | null>(null)

function toggleExpand(jobId: string) {
  expandedJob.value = expandedJob.value === jobId ? null : jobId
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

function statusType(status: string | null): 'success' | 'error' | 'default' {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed' || status === 'error') return 'error'
  return 'default'
}
</script>

<template>
  <div class="job-list">
    <div class="section-title">{{ t('agents.scheduledJobs') }}</div>
    <NEmpty v-if="jobs.length === 0" :description="t('agents.noJobs')" size="small" />
    <div v-else class="job-items">
      <div v-for="job in jobs" :key="job.jobId" class="job-card">
        <div class="job-header">
          <span class="job-name">{{ job.name }}</span>
          <div class="job-tags">
            <NTag size="small" :type="job.enabled ? 'success' : 'default'" round>
              {{ job.enabled ? t('agents.enabled') : t('agents.disabled') }}
            </NTag>
            <NTag v-if="job.lastStatus" size="small" :type="statusType(job.lastStatus)" round>
              {{ job.lastStatus }}
            </NTag>
          </div>
        </div>
        <div class="job-meta">
          <span>{{ job.scheduleDisplay }}</span>
        </div>
        <div class="job-times">
          <span v-if="job.lastRunAt">{{ t('agents.lastRun') }}: {{ formatTime(job.lastRunAt) }}</span>
          <span v-if="job.nextRunAt">{{ t('agents.nextRun') }}: {{ formatTime(job.nextRunAt) }}</span>
        </div>
        <div
          v-if="job.lastOutput"
          class="job-output-toggle"
          @click="toggleExpand(job.jobId)"
        >
          <span class="job-output-label">{{ t('agents.lastOutput') }}</span>
          <span class="job-output-arrow">{{ expandedJob === job.jobId ? '▲' : '▼' }}</span>
        </div>
        <div v-if="job.lastOutput && expandedJob === job.jobId" class="job-output-content">
          {{ job.lastOutput }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.job-list {
  margin-bottom: 20px;
}

.section-title {
  font-size: 12px;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.job-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.job-card {
  padding: 10px 12px;
  border: 1px solid $border-light;
  border-radius: 6px;
  background: $bg-card;
}

.job-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.job-name {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.job-tags {
  display: flex;
  gap: 4px;
}

.job-meta {
  font-size: 12px;
  color: $text-secondary;
  margin-bottom: 4px;
}

.job-times {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: $text-muted;
}

.job-output-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid $border-light;
  cursor: pointer;
  user-select: none;
}

.job-output-label {
  font-size: 11px;
  color: $text-muted;
}

.job-output-arrow {
  font-size: 10px;
  color: $text-muted;
}

.job-output-content {
  margin-top: 6px;
  padding: 8px;
  font-size: 12px;
  font-family: monospace;
  color: $text-secondary;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}
</style>
