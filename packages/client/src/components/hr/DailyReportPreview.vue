<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NButton,
  NCard,
  NSelect,
  NSpace,
  NSpin,
  NEmpty,
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NDivider,
  NTimeline,
  NTimelineItem,
} from 'naive-ui'
import type { ReportResponse } from '@/api/hr/dashboard'

// ── Props ──────────────────────────────────────────────────
interface Props {
  report: ReportResponse | null
  reports: ReportResponse[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

// ── Emits ──────────────────────────────────────────────────
const emit = defineEmits<{
  (e: 'generate'): void
  (e: 'refresh'): void
  (e: 'export'): void
}>()

// ── Local state ────────────────────────────────────────────
const selectedReportId = ref<string | null>(null)

// ── Computed ───────────────────────────────────────────────
const reportOptions = computed(() =>
  props.reports.map((r) => ({
    label: `${r.title} (${r.generated_at?.split('T')[0] ?? r.generated_at})`,
    value: r.id,
  })),
)

const displayReport = computed(() => {
  if (!selectedReportId.value) return props.report
  return props.reports.find((r) => r.id === selectedReportId.value) ?? props.report
})

const reportDate = computed(() => {
  if (!displayReport.value) return ''
  return displayReport.value.generated_at ?? ''
})

// ── Helpers ────────────────────────────────────────────────
function parseContentSections(content: string) {
  if (!content) return { metrics: '', highlights: '', issues: '', suggestions: '' }
  // Try to parse sections from the content
  const metricsMatch = content.match(/##?\s*核心指标\s*([\s\S]*?)(?=##?\s|$)/i)
  const highlightsMatch = content.match(/##?\s*亮点\s*([\s\S]*?)(?=##?\s|$)/i)
  const issuesMatch = content.match(/##?\s*问题\s*([\s\S]*?)(?=##?\s|$)/i)
  const suggestionsMatch = content.match(/##?\s*建议\s*([\s\S]*?)(?=##?\s|$)/i)

  return {
    metrics: metricsMatch?.[1]?.trim() ?? '',
    highlights: highlightsMatch?.[1]?.trim() ?? '',
    issues: issuesMatch?.[1]?.trim() ?? '',
    suggestions: suggestionsMatch?.[1]?.trim() ?? '',
  }
}

function handleSelectReport(id: string) {
  selectedReportId.value = id
}

function handleGenerate() {
  emit('generate')
}

function handleRefresh() {
  emit('refresh')
}

function handleExport() {
  emit('export')
}
</script>

<template>
  <div class="daily-report-preview">
    <!-- Header toolbar -->
    <div class="report-toolbar">
      <div class="toolbar-left">
        <NSelect
          v-if="reports.length > 0"
          :value="selectedReportId"
          :options="reportOptions"
          placeholder="选择历史日报..."
          clearable
          style="width: 300px"
          @update:value="handleSelectReport"
        />
      </div>
      <NSpace size="small">
        <NButton size="small" @click="handleRefresh" :loading="loading">
          刷新
        </NButton>
        <NButton size="small" type="primary" @click="handleGenerate" :loading="loading">
          重新生成
        </NButton>
        <NButton size="small" @click="handleExport" :disabled="!displayReport">
          导出
        </NButton>
      </NSpace>
    </div>

    <!-- Loading state -->
    <NSpin v-if="loading" class="loading-spinner" />

    <!-- Empty state -->
    <NEmpty v-else-if="!displayReport" description="暂无日报数据，请先生成日报" />

    <!-- Report content -->
    <template v-else>
      <!-- Report header -->
      <div class="report-header">
        <h3 class="report-title">{{ displayReport.title }}</h3>
        <div class="report-meta">
          <span class="meta-item">日期: {{ reportDate }}</span>
        </div>
      </div>

      <NDivider style="margin: 12px 0" />

      <!-- Rendered content sections -->
      <div class="report-body" v-html="displayReport.content" />

      <!-- Fallback: structured view if HTML rendering is sparse -->
      <template
        v-if="displayReport.content && displayReport.content.length < 50"
      >
        <NDescriptions bordered :column="1" label-placement="left" size="small">
          <NDescriptionsItem label="标题">{{ displayReport.title }}</NDescriptionsItem>
          <NDescriptionsItem label="内容">
            {{ displayReport.content }}
          </NDescriptionsItem>
        </NDescriptions>
      </template>
    </template>

    <!-- History timeline (sidebar/compact) -->
    <div v-if="reports.length > 1" class="history-section">
      <NDivider style="margin: 16px 0 12px" />
      <div class="section-label">历史日报</div>
      <NTimeline size="small">
        <NTimelineItem
          v-for="r in reports.slice(0, 10)"
          :key="r.id"
          :type="r.id === displayReport?.id ? 'success' : 'default'"
        >
          <div
            class="timeline-item"
            :class="{ active: r.id === displayReport?.id }"
            @click="handleSelectReport(r.id)"
          >
            <span class="timeline-title">{{ r.title }}</span>
            <span class="timeline-date">
              {{ r.generated_at?.split('T')[0] ?? r.generated_at }}
            </span>
          </div>
        </NTimelineItem>
      </NTimeline>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.daily-report-preview {
  padding: 0;
}

.report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;

  .toolbar-left {
    flex: 1;
    min-width: 200px;
  }
}

.loading-spinner {
  display: block;
  margin: 40px auto;
}

.report-header {
  .report-title {
    font-size: 18px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 8px;
  }

  .report-meta {
    display: flex;
    gap: 16px;
    font-size: 13px;
    color: $text-muted;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }
}

.report-body {
  line-height: 1.8;
  font-size: 14px;
  color: $text-primary;
  max-height: 600px;
  overflow-y: auto;

  :deep(h1),
  :deep(h2),
  :deep(h3) {
    color: $text-primary;
    margin-top: 16px;
    margin-bottom: 8px;
  }

  :deep(h1) {
    font-size: 18px;
  }

  :deep(h2) {
    font-size: 16px;
    border-bottom: 1px solid $border-light;
    padding-bottom: 6px;
  }

  :deep(h3) {
    font-size: 14px;
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;

    th,
    td {
      border: 1px solid $border-color;
      padding: 6px 10px;
      font-size: 13px;
    }

    th {
      background: $bg-secondary;
      font-weight: 600;
    }
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 20px;
  }

  :deep(li) {
    margin-bottom: 4px;
  }
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: 8px;
}

.timeline-item {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: $radius-sm;
  transition: background $transition-fast;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &:hover {
    background: rgba(var(--accent-primary-rgb), 0.06);
  }

  &.active {
    background: rgba(var(--accent-primary-rgb), 0.1);
  }

  .timeline-title {
    font-size: 13px;
    color: $text-primary;
  }

  .timeline-date {
    font-size: 11px;
    color: $text-muted;
  }
}
</style>
