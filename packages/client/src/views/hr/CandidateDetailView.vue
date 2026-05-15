<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCandidateStore } from '@/stores/hr/candidates'
import { useResumeStore } from '@/stores/hr/resumes'
import { useInterviewStore } from '@/stores/hr/interviews'
import { useOfferStore } from '@/stores/hr/offers'
import {
  NPageHeader, NTabs, NTabPane, NCard, NDescriptions, NDescriptionsItem,
  NTag, NButton, NSpace, NDataTable, NSpin, NEmpty, NAvatar,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import ResumeViewer from '@/components/hr/ResumeViewer.vue'
import InterviewTimeline from '@/components/hr/InterviewTimeline.vue'
import OfferStatusBadge from '@/components/hr/OfferStatusBadge.vue'
import type { Resume } from '@/api/hr/resumes'
import type { Interview } from '@/api/hr/interviews'
import type { Offer } from '@/api/hr/offers'

const route = useRoute()
const router = useRouter()
const candidateStore = useCandidateStore()
const resumeStore = useResumeStore()
const interviewStore = useInterviewStore()
const offerStore = useOfferStore()

const candidate = computed(() => candidateStore.current)

const stageColorMap: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  applied: 'default',
  screened: 'info',
  interviewed: 'warning',
  offered: 'success',
  hired: 'success',
  rejected: 'error',
}

const sourceLabelMap: Record<string, string> = {
  resume_upload: '简历上传',
  referral: '内部推荐',
  linkedin: 'LinkedIn',
  website: '官网投递',
  headhunting: '猎头',
  other: '其他',
}

const showResumeViewer = ref(false)
const viewingResume = ref<Resume | null>(null)

function handleViewResume(row: Resume) {
  viewingResume.value = row
  showResumeViewer.value = true
}

function handleViewOffer(row: Offer) {
  router.push({ name: 'hr.offerDetail', params: { id: row.id } })
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatSalary(value: number | null): string {
  if (value == null) return '-'
  return `${(value / 1000).toFixed(0)}K`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

const resumeStatusColor: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  pending: 'default',
  processing: 'warning',
  completed: 'success',
  failed: 'error',
}

const resumeStatusLabel: Record<string, string> = {
  pending: '待解析',
  processing: '解析中',
  completed: '已完成',
  failed: '失败',
}

const resumeColumns: DataTableColumns<Resume> = [
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true } },
  {
    title: '解析状态',
    key: 'parse_status',
    width: 100,
    render: (row) => h(NTag, { type: resumeStatusColor[row.parse_status], size: 'small' }, { default: () => resumeStatusLabel[row.parse_status] }),
  },
  {
    title: 'AI标签',
    key: 'tags',
    width: 200,
    render: (row) => h(NSpace, { size: 4 }, () => row.tags.map(tag => h(NTag, { size: 'small', type: 'info' }, { default: () => tag }))),
  },
  {
    title: '文件大小',
    key: 'file_size',
    width: 100,
    render: (row) => formatFileSize(row.file_size),
  },
  { title: '上传时间', key: 'created_at', width: 160, render: (row) => formatDateTime(row.created_at) },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row) => h(NButton, { size: 'small', text: true, onClick: () => handleViewResume(row) }, { default: () => '查看' }),
  },
]

const interviewColumns: DataTableColumns<Interview> = [
  { title: '轮次', key: 'round_number', width: 70 },
  { title: '类型', key: 'interview_type', width: 120 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: row.status === 'completed' ? 'success' : row.status === 'cancelled' ? 'error' : 'info' }, { default: () => row.status }),
  },
  {
    title: '计划时间',
    key: 'scheduled_at',
    width: 160,
    render: (row) => formatDateTime(row.scheduled_at),
  },
  {
    title: '时长',
    key: 'duration_minutes',
    width: 80,
    render: (row) => `${row.duration_minutes}分钟`,
  },
  {
    title: '评分',
    key: 'overall_score',
    width: 80,
    render: (row) => row.overall_score != null ? `${row.overall_score}/10` : '-',
  },
]

const offerColumns: DataTableColumns<Offer> = [
  { title: '岗位', key: 'position_id', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(OfferStatusBadge, { status: row.status }),
  },
  {
    title: '基本薪资',
    key: 'base_salary',
    width: 100,
    render: (row) => formatSalary(row.base_salary),
  },
  {
    title: '入职日期',
    key: 'proposed_start_date',
    width: 120,
    render: (row) => row.proposed_start_date || '-',
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    render: (row) => formatDateTime(row.created_at),
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row) => h(NButton, { size: 'small', text: true, onClick: () => handleViewOffer(row) }, { default: () => '查看' }),
  },
]

onMounted(async () => {
  const id = route.params.id as string
  await candidateStore.fetchCandidate(id)
  await Promise.all([
    resumeStore.fetchResumes({ candidate_id: id }),
    interviewStore.fetchInterviews({ candidate_id: id }),
    offerStore.fetchOffers({ candidate_id: id }),
  ])
})
</script>

<template>
  <div class="candidate-detail">
    <NSpin :show="candidateStore.loading">
      <NPageHeader @back="router.push({ name: 'hr.candidates' })">
        <template #title>
          <div style="display:flex;align-items:center;gap:12px">
            <NAvatar round :size="40">{{ candidate?.name?.[0] || '?' }}</NAvatar>
            <div>
              <div style="font-size:18px;font-weight:600">{{ candidate?.name || '加载中...' }}</div>
              <div style="font-size:13px;color:#999">{{ candidate?.email }}</div>
            </div>
          </div>
        </template>
        <template #extra>
          <NSpace>
            <NTag :type="stageColorMap[candidate?.stage || '']">{{ candidate?.stage }}</NTag>
            <NTag :type="candidate?.status === 'active' ? 'success' : 'default'">{{ candidate?.status === 'active' ? '活跃' : '已归档' }}</NTag>
          </NSpace>
        </template>
      </NPageHeader>

      <NTabs type="line" style="margin-top: 20px;">
        <NTabPane name="profile" tab="基本信息">
          <NCard>
            <NDescriptions label-placement="left" :column="2" bordered>
              <NDescriptionsItem label="姓名">{{ candidate?.name || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="邮箱">{{ candidate?.email || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="手机号">{{ candidate?.phone || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="所在城市">{{ candidate?.location || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="当前公司">{{ candidate?.current_company || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="当前职位">{{ candidate?.current_title || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="工作年限">{{ candidate?.years_of_experience != null ? `${candidate.years_of_experience}年` : '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="学历">{{ candidate?.education || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="期望薪资">{{ formatSalary(candidate?.expected_salary ?? null) }}</NDescriptionsItem>
              <NDescriptionsItem label="来源">{{ sourceLabelMap[candidate?.source || ''] || candidate?.source || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="应聘岗位">{{ candidate?.position_id || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="申请时间">{{ formatDateTime(candidate?.applied_at ?? null) }}</NDescriptionsItem>
              <NDescriptionsItem label="分配招聘官">{{ candidate?.assigned_recruiter || '-' }}</NDescriptionsItem>
              <NDescriptionsItem label="技能标签">
                <NSpace size="4">
                  <NTag v-for="skill in (candidate?.skills || [])" :key="skill" size="small" type="info">{{ skill }}</NTag>
                  <span v-if="!candidate?.skills?.length">-</span>
                </NSpace>
              </NDescriptionsItem>
              <NDescriptionsItem label="标签" :span="2">
                <NSpace size="4">
                  <NTag v-for="tag in (candidate?.tags || [])" :key="tag" size="small">{{ tag }}</NTag>
                  <span v-if="!candidate?.tags?.length">-</span>
                </NSpace>
              </NDescriptionsItem>
              <NDescriptionsItem label="备注/摘要" :span="2">{{ candidate?.summary || '-' }}</NDescriptionsItem>
            </NDescriptions>
          </NCard>
        </NTabPane>

        <NTabPane name="resumes" tab="简历">
          <NCard>
            <NEmpty v-if="!resumeStore.resumes.length && !resumeStore.loading" description="暂无简历" />
            <NDataTable
              v-else
              :columns="resumeColumns"
              :data="resumeStore.resumes"
              :loading="resumeStore.loading"
              :bordered="false"
            />
          </NCard>
        </NTabPane>

        <NTabPane name="interviews" tab="面试">
          <NCard title="面试时间线">
            <InterviewTimeline :interviews="interviewStore.interviews" />
          </NCard>
          <NCard title="面试记录" style="margin-top: 16px;">
            <NEmpty v-if="!interviewStore.interviews.length && !interviewStore.loading" description="暂无面试记录" />
            <NDataTable
              v-else
              :columns="interviewColumns"
              :data="interviewStore.interviews"
              :loading="interviewStore.loading"
              :bordered="false"
            />
          </NCard>
        </NTabPane>

        <NTabPane name="offers" tab="Offer">
          <NCard>
            <NEmpty v-if="!offerStore.offers.length && !offerStore.loading" description="暂无Offer记录" />
            <NDataTable
              v-else
              :columns="offerColumns"
              :data="offerStore.offers"
              :loading="offerStore.loading"
              :bordered="false"
            />
          </NCard>
        </NTabPane>
      </NTabs>
    </NSpin>

    <ResumeViewer
      :show="showResumeViewer"
      :resume="viewingResume"
      @update:show="showResumeViewer = $event"
    />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.candidate-detail {
  padding: 24px;
}
</style>
