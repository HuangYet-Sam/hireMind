<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResumeStore } from '@/stores/hr/resumes'
import {
  NPageHeader, NTabs, NTabPane, NCard, NDescriptions, NDescriptionsItem,
  NTag, NButton, NSpace, NSpin, NEmpty, NCode,
} from 'naive-ui'
import type { Resume } from '@/api/hr/resumes'
import AiContextBar from '@/components/hr/AiContextBar.vue'

const route = useRoute()
const router = useRouter()
const resumeStore = useResumeStore()

const resume = computed(() => resumeStore.current)

const parseStatusColor: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  pending: 'default',
  processing: 'warning',
  completed: 'success',
  failed: 'error',
}

const parseStatusLabel: Record<string, string> = {
  pending: '待解析',
  processing: '解析中',
  completed: '已完成',
  failed: '失败',
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

const reparsing = ref(false)
const activeTab = ref('info')

async function handleReparse() {
  if (!resume.value) return
  reparsing.value = true
  try {
    await resumeStore.reparseResume(resume.value.id)
  } finally {
    reparsing.value = false
  }
}

function handleViewCandidate(candidateId: string) {
  router.push({ name: 'hr.candidateDetail', params: { id: candidateId } })
}

// Parsed data computed helpers
const parsedSkills = computed(() => {
  const data = resume.value?.parsed_data
  if (!data) return []
  return (data.skills as string[]) || []
})

const parsedEducation = computed(() => {
  const data = resume.value?.parsed_data
  if (!data) return []
  return (data.education as Record<string, unknown>[]) || []
})

const parsedWorkExperience = computed(() => {
  const data = resume.value?.parsed_data
  if (!data) return []
  return (data.work_experience as Record<string, unknown>[]) || []
})

onMounted(async () => {
  const id = route.params.id as string
  await resumeStore.fetchResume(id)
})
</script>

<template>
  <div class="resume-detail">
    <NSpin :show="resumeStore.loading">
      <NPageHeader @back="router.push({ name: 'hr.resumes' })">
        <template #title>
          <div style="display:flex;align-items:center;gap:12px">
            <div>
              <div style="font-size:18px;font-weight:600">{{ resume?.original_filename || '加载中...' }}</div>
              <div style="font-size:13px;color:#999">ID: {{ resume?.id || '-' }}</div>
            </div>
          </div>
        </template>
        <template #extra>
          <NSpace>
            <NTag :type="parseStatusColor[resume?.parse_status || '']">
              {{ parseStatusLabel[resume?.parse_status || ''] || resume?.parse_status }}
            </NTag>
            <NTag v-if="resume?.language" type="info">{{ resume.language }}</NTag>
          </NSpace>
        </template>
      </NPageHeader>

      <AiContextBar
        entity-type="resume"
        :entity-id="(route.params.id as string)"
        :active-tab="activeTab"
      />

      <NTabs v-model:value="activeTab" type="line" style="margin-top: 20px;">
        <NTabPane name="info" tab="基本信息">
          <NCard>
            <NDescriptions label-placement="left" :column="2" bordered>
              <NDescriptionsItem label="文件名">{{ resume?.original_filename || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="文件大小">{{ resume?.file_size ? formatFileSize(resume.file_size) : '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="Content-Type">{{ resume?.content_type || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="语言">{{ resume?.language || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="页数">{{ resume?.page_count ?? '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="解析状态">
                <NTag :type="parseStatusColor[resume?.parse_status || '']" size="small">
                  {{ parseStatusLabel[resume?.parse_status || ''] || resume?.parse_status }}
                </NTag>
              </NDescriptionsItem>
              <NDescriptionsItem label="关联候选人">
                <NButton
                  v-if="resume?.candidate_id"
                  text
                  type="primary"
                  @click="handleViewCandidate(resume.candidate_id)"
                >
                  {{ resume.candidate_id }}
                </NButton>
                <span v-else>-</span>
              </NDescriptionsItem>
              <NDescriptionsItem label="上传者">{{ resume?.uploaded_by || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="上传时间">{{ formatDateTime(resume?.created_at ?? null) }}</NDescriptionsItem>
              <NDescriptionsItem label="更新时间">{{ formatDateTime(resume?.updated_at ?? null) }}</NDescriptionsItem>
            </NDescriptions>
          </NCard>

          <NCard title="文件操作" size="small" style="margin-top: 16px;">
            <NSpace>
              <NButton type="primary" :loading="reparsing" @click="handleReparse">
                重新解析
              </NButton>
              <NButton tag="a" :href="`/api/v1/resumes/${resume?.id}/download`" target="_blank" :disabled="!resume">
                下载文件
              </NButton>
            </NSpace>
          </NCard>
        </NTabPane>

        <NTabPane name="parsed" tab="解析结果">
          <template v-if="resume?.parse_status === 'completed' && resume?.parsed_data">
            <NCard title="技能" size="small" style="margin-bottom: 12px;">
              <NSpace size="4">
                <NTag v-for="skill in parsedSkills" :key="skill" size="small" type="info">{{ skill }}</NTag>
                <span v-if="!parsedSkills.length" style="color: #999">未提取到技能</span>
              </NSpace>
            </NCard>

            <NCard title="教育经历" size="small" style="margin-bottom: 12px;">
              <NEmpty v-if="!parsedEducation.length" description="未提取到教育经历" />
              <NDescriptions v-for="(edu, idx) in parsedEducation" :key="idx" bordered :column="2" label-placement="left" size="small" style="margin-bottom: 8px;">
                <NDescriptionsItem v-for="(value, key) in edu" :key="String(key)" :label="String(key)">
                  {{ typeof value === 'object' ? JSON.stringify(value) : value }}
                </NDescriptionsItem>
              </NDescriptions>
            </NCard>

            <NCard title="工作经历" size="small" style="margin-bottom: 12px;">
              <NEmpty v-if="!parsedWorkExperience.length" description="未提取到工作经历" />
              <NDescriptions v-for="(exp, idx) in parsedWorkExperience" :key="idx" bordered :column="2" label-placement="left" size="small" style="margin-bottom: 8px;">
                <NDescriptionsItem v-for="(value, key) in exp" :key="String(key)" :label="String(key)">
                  {{ typeof value === 'object' ? JSON.stringify(value) : value }}
                </NDescriptionsItem>
              </NDescriptions>
            </NCard>

            <NCard title="原始解析数据" size="small">
              <NCode :code="JSON.stringify(resume.parsed_data, null, 2)" language="json" word-wrap />
            </NCard>
          </template>
          <NEmpty v-else :description="resume?.parse_status === 'processing' ? '正在解析中，请稍后刷新页面' : resume?.parse_status === 'pending' ? '等待解析' : '解析失败或尚未解析'" />
        </NTabPane>

        <NTabPane name="ai" tab="AI 操作">
          <NCard title="AI 辅助功能">
            <NEmpty description="AI 操作功能即将上线，敬请期待">
              <template #extra>
                <NSpace vertical>
                  <NButton disabled>AI 总结简历</NButton>
                  <NButton disabled>AI 生成面试问题</NButton>
                  <NButton disabled>AI 评估匹配度</NButton>
                  <NButton disabled>AI 提取关键信息</NButton>
                </NSpace>
              </template>
            </NEmpty>
          </NCard>
        </NTabPane>
      </NTabs>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.resume-detail {
  padding: 24px;
}
</style>
