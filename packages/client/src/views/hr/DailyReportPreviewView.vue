<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NTag, NSpace, NCard, NSelect, NDatePicker, NModal, NDescriptions, NDescriptionsItem, NEmpty, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import * as dailyReportsApi from '@/api/hr/daily-reports'
import type { DailyReport, ReportTemplate } from '@/api/hr/daily-reports'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const message = useMessage()
const reports = ref<DailyReport[]>([])
const templates = ref<ReportTemplate[]>([])
const loading = ref(false)
const generating = ref(false)
const showPreviewModal = ref(false)
const showTemplateModal = ref(false)
const previewReport = ref<DailyReport | null>(null)
const previewTemplate = ref<ReportTemplate | null>(null)
const selectedTemplateId = ref<string | null>(null)
const reportDate = ref<number | null>(null)

const columns: DataTableColumns<DailyReport> = [
  { title: '标题', key: 'title', width: 200, ellipsis: { tooltip: true } },
  { title: '报告日期', key: 'report_date', width: 120 },
  { title: '模板', key: 'template_name', width: 130 },
  {
    title: '生成方式',
    key: 'generated_by',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: row.generated_by === 'manual' ? 'info' : 'default' }, () => row.generated_by === 'manual' ? '手动' : '自动'),
  },
  { title: '生成时间', key: 'generated_at', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'tiny', onClick: () => handlePreview(row) }, () => '预览'),
    ]),
  },
]

const templateColumns: DataTableColumns<ReportTemplate> = [
  { title: '模板名称', key: 'name', width: 160 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '变量', key: 'variables', width: 200, render: (row) => row.variables.join(', ') },
  {
    title: '默认',
    key: 'is_default',
    width: 70,
    render: (row) => row.is_default ? h(NTag, { size: 'small', type: 'success' }, () => '默认') : '',
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row) => h(NButton, { size: 'tiny', onClick: () => handleViewTemplate(row) }, () => '查看'),
  },
]

onMounted(async () => {
  await Promise.all([fetchReports(), fetchTemplates()])
})

async function fetchReports() {
  loading.value = true
  try {
    const res = await dailyReportsApi.listDailyReports()
    reports.value = res.items
  } catch {
    message.error('获取日报列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchTemplates() {
  try {
    templates.value = await dailyReportsApi.listReportTemplates()
  } catch {
    templates.value = []
  }
}

async function handleGenerate() {
  generating.value = true
  try {
    const data: any = {}
    if (selectedTemplateId.value) data.template_id = selectedTemplateId.value
    if (reportDate.value) data.report_date = new Date(reportDate.value).toISOString().split('T')[0]
    await dailyReportsApi.generateDailyReport(data)
    message.success('日报生成成功')
    await fetchReports()
  } catch {
    message.error('日报生成失败')
  } finally {
    generating.value = false
  }
}

function handlePreview(report: DailyReport) {
  previewReport.value = report
  showPreviewModal.value = true
}

function handleViewTemplate(template: ReportTemplate) {
  previewTemplate.value = template
  showTemplateModal.value = true
}

const templateOptions = () => {
  return templates.value.map(t => ({ label: t.name, value: t.id }))
}
</script>

<template>
  <ErrorBoundary>
    <div class="daily-report-view">
      <header class="page-header">
        <h2 class="header-title">日报预览</h2>
      </header>

      <div class="report-actions">
        <NCard size="small" title="生成日报">
          <div class="generate-form">
            <NSelect
              v-model:value="selectedTemplateId"
              :options="templateOptions()"
              placeholder="选择模板（可选）"
              clearable
              style="width: 200px;"
            />
            <NDatePicker
              v-model:value="reportDate"
              type="date"
              clearable
              placeholder="选择日期（默认今天）"
              style="width: 200px;"
            />
            <NButton type="primary" :loading="generating" @click="handleGenerate">
              {{ generating ? '生成中...' : '生成日报' }}
            </NButton>
          </div>
        </NCard>
      </div>

      <div class="section-title">日报模板</div>
      <NDataTable
        :columns="templateColumns"
        :data="templates"
        :row-key="(row: ReportTemplate) => row.id"
        :pagination="false"
        striped
        size="small"
        style="margin-bottom: 24px;"
      />

      <div class="section-title">历史日报</div>
      <TableSkeleton v-if="loading" :rows="5" :columns="5" />
      <NDataTable
        v-else
        :columns="columns"
        :data="reports"
        :row-key="(row: DailyReport) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="800"
        striped
      />

      <NModal v-model:show="showPreviewModal" preset="card" :title="previewReport?.title ?? '日报预览'" style="max-width: 800px;">
        <template v-if="previewReport">
          <div class="report-meta">
            <span>日期: {{ previewReport.report_date }}</span>
            <span>模板: {{ previewReport.template_name }}</span>
            <span>生成时间: {{ previewReport.generated_at }}</span>
          </div>
          <div class="report-content" v-html="previewReport.content" />
        </template>
      </NModal>

      <NModal v-model:show="showTemplateModal" preset="card" :title="`模板 - ${previewTemplate?.name ?? ''}`" style="max-width: 700px;">
        <template v-if="previewTemplate">
          <div class="template-meta">
            <p>{{ previewTemplate.description }}</p>
            <p>变量: {{ previewTemplate.variables.join(', ') || '无' }}</p>
          </div>
          <div class="template-content">
            <pre>{{ previewTemplate.template_content }}</pre>
          </div>
        </template>
      </NModal>
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.daily-report-view {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0;
  }
}

.report-actions {
  margin-bottom: 24px;
}

.generate-form {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 12px;
}

.report-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: $text-muted;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid $border-light;
}

.report-content {
  line-height: 1.8;
  font-size: 14px;
  color: $text-primary;
  max-height: 500px;
  overflow-y: auto;

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;

    th, td {
      border: 1px solid $border-color;
      padding: 6px 10px;
      font-size: 13px;
    }

    th {
      background: $bg-secondary;
      font-weight: 600;
    }
  }
}

.template-meta {
  font-size: 13px;
  color: $text-secondary;
  margin-bottom: 12px;

  p {
    margin: 4px 0;
  }
}

.template-content {
  pre {
    background: var(--code-bg);
    padding: 16px;
    border-radius: $radius-sm;
    font-family: $font-code;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
    max-height: 400px;
    overflow-y: auto;
    color: $text-primary;
  }
}
</style>
