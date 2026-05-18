<script setup lang="ts">
/**
 * ReportExport — M8 报表导出组件
 *
 * Props: loading
 * 表单：报表类型 + 格式 + 日期范围
 * 导出按钮 + 进度条
 * 下载完成提示
 * 最近导出历史列表
 * Emits: export, download
 */
import { ref, computed } from 'vue'
import {
  NCard, NForm, NFormItem, NSelect, NDatePicker, NButton, NSpace,
  NProgress, NTag, NEmpty, NIcon, useMessage,
} from 'naive-ui'
import type { SelectOption } from 'naive-ui'

const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  export: [params: ExportParams]
  download: [reportId: string]
}>()

// ── Types ────────────────────────────────────────────────────

export interface ExportParams {
  report_type: 'funnel' | 'trend' | 'position' | 'channel' | 'full'
  format: 'excel' | 'pdf'
  date_from?: string
  date_to?: string
}

interface ExportHistoryItem {
  id: string
  report_type: string
  format: string
  created_at: string
  status: 'pending' | 'completed' | 'failed'
  file_size?: string
}

// ── State ────────────────────────────────────────────────────

const message = useMessage()

const reportType = ref<ExportParams['report_type']>('full')
const reportFormat = ref<ExportParams['format']>('excel')
const dateRange = ref<[number, number] | null>(null)
const exportProgress = ref(0)
const isExporting = ref(false)

const exportHistory = ref<ExportHistoryItem[]>([])

// ── Options ──────────────────────────────────────────────────

const reportTypeOptions: SelectOption[] = [
  { label: '漏斗分析报表', value: 'funnel' },
  { label: '趋势分析报表', value: 'trend' },
  { label: '岗位效能报表', value: 'position' },
  { label: '渠道ROI报表', value: 'channel' },
  { label: '全量综合报表', value: 'full' },
]

const formatOptions: SelectOption[] = [
  { label: 'Excel (.xlsx)', value: 'excel' },
  { label: 'PDF', value: 'pdf' },
]

// ── Computed ─────────────────────────────────────────────────

const canExport = computed(() => {
  return !isExporting.value && !props.loading
})

const reportTypeLabel = computed(() => {
  const opt = reportTypeOptions.find(o => o.value === reportType.value)
  return opt?.label ?? reportType.value
})

// ── Actions ──────────────────────────────────────────────────

async function handleExport() {
  if (!canExport.value) return

  const params: ExportParams = {
    report_type: reportType.value,
    format: reportFormat.value,
  }

  if (dateRange.value) {
    params.date_from = new Date(dateRange.value[0]).toISOString().split('T')[0]
    params.date_to = new Date(dateRange.value[1]).toISOString().split('T')[0]
  }

  isExporting.value = true
  exportProgress.value = 0

  // Simulate progress
  const progressInterval = setInterval(() => {
    if (exportProgress.value < 90) {
      exportProgress.value += Math.random() * 15
    }
  }, 300)

  try {
    emit('export', params)

    // Simulate completion after API call
    // In real implementation, the parent component would handle actual API
    await new Promise(resolve => setTimeout(resolve, 1500))

    clearInterval(progressInterval)
    exportProgress.value = 100

    // Add to history
    const historyItem: ExportHistoryItem = {
      id: `report-${Date.now()}`,
      report_type: reportType.value,
      format: reportFormat.value,
      created_at: new Date().toISOString(),
      status: 'completed',
      file_size: '2.4 MB',
    }
    exportHistory.value.unshift(historyItem)
    if (exportHistory.value.length > 10) {
      exportHistory.value = exportHistory.value.slice(0, 10)
    }

    message.success('报表导出成功！')
  } catch {
    clearInterval(progressInterval)
    exportProgress.value = 0
    message.error('报表导出失败，请重试')
  } finally {
    isExporting.value = false
    setTimeout(() => { exportProgress.value = 0 }, 2000)
  }
}

function handleDownload(reportId: string) {
  emit('download', reportId)
  message.info('开始下载...')
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getStatusType(status: ExportHistoryItem['status']): 'success' | 'warning' | 'error' {
  if (status === 'completed') return 'success'
  if (status === 'pending') return 'warning'
  return 'error'
}

function getStatusLabel(status: ExportHistoryItem['status']): string {
  if (status === 'completed') return '完成'
  if (status === 'pending') return '生成中'
  return '失败'
}

function getReportTypeLabel(type: string): string {
  const opt = reportTypeOptions.find(o => o.value === type)
  return opt?.label ?? type
}
</script>

<template>
  <div class="report-export">
    <!-- Export form -->
    <NCard size="small" title="报表导出">
      <NForm label-placement="left" label-width="80" :show-feedback="false">
        <NFormItem label="报表类型">
          <NSelect
            v-model:value="reportType"
            :options="reportTypeOptions"
            style="width: 100%;"
          />
        </NFormItem>
        <NFormItem label="导出格式">
          <NSelect
            v-model:value="reportFormat"
            :options="formatOptions"
            style="width: 100%;"
          />
        </NFormItem>
        <NFormItem label="日期范围">
          <NDatePicker
            v-model:value="dateRange"
            type="daterange"
            clearable
            style="width: 100%;"
          />
        </NFormItem>

        <!-- Progress bar -->
        <div v-if="isExporting || exportProgress > 0" class="export-progress">
          <NProgress
            type="line"
            :percentage="Math.min(Math.round(exportProgress), 100)"
            :status="exportProgress >= 100 ? 'success' : 'default'"
            :height="16"
            indicator-placement="inside"
          />
        </div>

        <div class="export-actions">
          <NButton
            type="primary"
            :loading="isExporting"
            :disabled="!canExport"
            @click="handleExport"
          >
            {{ isExporting ? '导出中...' : '导出报表' }}
          </NButton>
        </div>
      </NForm>
    </NCard>

    <!-- Export history -->
    <NCard size="small" title="最近导出" style="margin-top: 16px;">
      <div v-if="exportHistory.length === 0" class="history-empty">
        <NEmpty description="暂无导出记录" size="small" />
      </div>

      <div v-else class="history-list">
        <div
          v-for="item in exportHistory"
          :key="item.id"
          class="history-item"
        >
          <div class="history-info">
            <div class="history-title">
              {{ getReportTypeLabel(item.report_type) }}
              <NTag size="tiny" :type="getStatusType(item.status)">
                {{ getStatusLabel(item.status) }}
              </NTag>
            </div>
            <div class="history-meta">
              <span>{{ item.format.toUpperCase() }}</span>
              <span v-if="item.file_size"> · {{ item.file_size }}</span>
              <span> · {{ formatDate(item.created_at) }}</span>
            </div>
          </div>
          <NButton
            v-if="item.status === 'completed'"
            text
            size="small"
            type="primary"
            @click="handleDownload(item.id)"
          >
            下载
          </NButton>
        </div>
      </div>
    </NCard>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.report-export {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.export-progress {
  margin: 12px 0;
}

.export-actions {
  margin-top: 16px;
}

// History
.history-empty {
  padding: 16px 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: $radius-sm;
  border: 1px solid $border-light;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $border-color;
  }
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-title {
  font-size: 13px;
  font-weight: 500;
  color: $text-primary;
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-meta {
  font-size: 11px;
  color: $text-muted;
  margin-top: 2px;
}
</style>
