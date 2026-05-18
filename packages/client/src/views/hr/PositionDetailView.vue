<script setup lang="ts">
import { computed, onMounted, ref, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePositionStore } from '@/stores/hr/positions'
import { useCandidateStore } from '@/stores/hr/candidates'
import { useMatchingStore } from '@/stores/hr/matching'
import {
  NPageHeader,
  NTabs,
  NTabPane,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NButton,
  NSpace,
  NDataTable,
  NSpin,
  NEmpty,
  NProgress,
  NSwitch,
  NGrid,
  NGridItem,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import type { Candidate } from '@/api/hr/candidates'
import AiContextBar from '@/components/hr/AiContextBar.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const positionStore = usePositionStore()
const candidateStore = useCandidateStore()
const matchingStore = useMatchingStore()

const position = computed(() => positionStore.current)
const candidatesLoaded = ref(false)
const matchingStarted = ref(false)
const activeTab = ref('info')

const employmentTypeMap: Record<string, string> = {
  full_time: '全职',
  part_time: '兼职',
  contract: '合同工',
  internship: '实习',
}

const priorityColorMap: Record<string, 'default' | 'info' | 'warning' | 'error'> = {
  low: 'default',
  normal: 'info',
  high: 'warning',
  urgent: 'error',
}

const priorityLabelMap: Record<string, string> = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

const stageMap: Record<string, string> = {
  applied: '已申请',
  screened: '已筛选',
  interviewed: '面试中',
  offered: '已发Offer',
  hired: '已入职',
  rejected: '已拒绝',
}

const stageColorMap: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error'> = {
  applied: 'default',
  screened: 'info',
  interviewed: 'warning',
  offered: 'success',
  hired: 'success',
  rejected: 'error',
}

const sourceMap: Record<string, string> = {
  resume_upload: '简历上传',
  referral: '内推',
  linkedin: 'LinkedIn',
  website: '官网',
  headhunting: '猎头',
  other: '其他',
}

const candidateColumns: DataTableColumns<Candidate> = [
  { title: '姓名', key: 'name', width: 120 },
  { title: '邮箱', key: 'email', width: 200 },
  {
    title: '阶段',
    key: 'stage',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: stageColorMap[row.stage] || 'default' }, { default: () => stageMap[row.stage] || row.stage }),
  },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: (row) => h(NTag, { size: 'small', type: row.status === 'active' ? 'success' : 'default' }, { default: () => row.status === 'active' ? '活跃' : '非活跃' }),
  },
  {
    title: '来源',
    key: 'source',
    width: 100,
    render: (row) => sourceMap[row.source] || row.source,
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row) =>
      h(
        NButton,
        { size: 'small', text: true, type: 'primary', onClick: () => router.push({ name: 'hr.candidateDetail', params: { id: row.id } }) },
        { default: () => '查看' },
      ),
  },
]

onMounted(async () => {
  await positionStore.fetchPosition(route.params.id as string)
})

async function handleClose() {
  try {
    await positionStore.updatePosition(route.params.id as string, { status: 'closed' })
    await positionStore.fetchPosition(route.params.id as string)
    message.success('岗位已关闭')
  } catch {
    message.error('关闭岗位失败')
  }
}

async function handleReopen() {
  try {
    await positionStore.updatePosition(route.params.id as string, { status: 'open' })
    await positionStore.fetchPosition(route.params.id as string)
    message.success('岗位已重新开放')
  } catch {
    message.error('重新开放失败')
  }
}

async function handleTabChange(name: string) {
  activeTab.value = name
  if (name === 'candidates' && !candidatesLoaded.value) {
    try {
      await candidateStore.fetchCandidates({ position_id: route.params.id as string })
      candidatesLoaded.value = true
    } catch {
      message.error('加载候选人失败')
    }
  }
}

async function handleMatch() {
  matchingStarted.value = true
  try {
    await matchingStore.matchCandidatesForPosition(route.params.id as string)
  } catch {
    message.error('匹配失败')
  }
}
</script>

<template>
  <div class="position-detail">
    <NSpin :show="positionStore.loading && !position">
      <NPageHeader
        @back="router.push({ name: 'hr.positions' })"
        :title="position?.title || '加载中...'"
        :subtitle="position ? `ID: ${position.id}` : ''"
      >
        <template #extra>
          <NSpace>
            <NButton
              v-if="position && (position.status === 'draft' || position.status === 'open')"
              type="error"
              @click="handleClose"
            >
              关闭岗位
            </NButton>
            <NButton
              v-if="position && (position.status === 'paused' || position.status === 'closed')"
              type="primary"
              @click="handleReopen"
            >
              重新开放
            </NButton>
          </NSpace>
        </template>
      </NPageHeader>

      <AiContextBar
        entity-type="position"
        :entity-id="(route.params.id as string)"
        :active-tab="activeTab"
      />

      <NTabs
        v-if="position"
        type="line"
        style="margin-top: 16px"
        @update:value="handleTabChange"
      >
        <NTabPane name="info" tab="岗位信息">
          <NDescriptions
            bordered
            :column="2"
            label-placement="left"
            style="margin-top: 12px"
          >
            <NDescriptionsItem label="部门">
              {{ position.department_id }}
            </NDescriptionsItem>
            <NDescriptionsItem label="工作地点">
              <NSpace align="center">
                <span>{{ position.location }}</span>
                <NSwitch :value="position.is_remote" disabled size="small" />
                <span style="font-size: 12px; color: var(--text-muted)">
                  {{ position.is_remote ? '支持远程' : '不支持远程' }}
                </span>
              </NSpace>
            </NDescriptionsItem>
            <NDescriptionsItem label="用工类型">
              {{ employmentTypeMap[position.employment_type] || position.employment_type }}
            </NDescriptionsItem>
            <NDescriptionsItem label="优先级">
              <NTag :type="priorityColorMap[position.priority]" size="small">
                {{ priorityLabelMap[position.priority] || position.priority }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="招聘人数">
              {{ position.headcount }}
            </NDescriptionsItem>
            <NDescriptionsItem label="薪资范围">
              {{ position.salary_min != null ? `${position.salary_min}` : '-' }}
              ~
              {{ position.salary_max != null ? `${position.salary_max}` : '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="学历要求">
              {{ position.education_requirement || '不限' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="经验要求">
              {{ position.experience_years_min != null ? `${position.experience_years_min}年以上` : '不限' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="技能标签" :span="2">
              <NSpace>
                <NTag
                  v-for="(skill, idx) in position.required_skills"
                  :key="idx"
                  size="small"
                  type="info"
                >
                  {{ typeof skill === 'string' ? skill : skill.name || JSON.stringify(skill) }}
                </NTag>
                <NTag v-if="!position.required_skills?.length" type="default" size="small">无</NTag>
              </NSpace>
            </NDescriptionsItem>
            <NDescriptionsItem label="加分技能" :span="2">
              <NSpace>
                <NTag
                  v-for="skill in position.preferred_skills"
                  :key="skill"
                  size="small"
                  type="success"
                >
                  {{ skill }}
                </NTag>
                <NTag v-if="!position.preferred_skills?.length" type="default" size="small">无</NTag>
              </NSpace>
            </NDescriptionsItem>
          </NDescriptions>

          <NCard title="岗位描述" size="small" style="margin-top: 16px">
            <p class="detail-text">{{ position.description || '暂无描述' }}</p>
          </NCard>

          <NCard title="岗位要求" size="small" style="margin-top: 12px">
            <p class="detail-text" style="white-space: pre-wrap">{{ position.requirements || '暂无要求' }}</p>
          </NCard>

          <NCard title="福利待遇" size="small" style="margin-top: 12px">
            <p class="detail-text" style="white-space: pre-wrap">{{ position.benefits || '暂无福利信息' }}</p>
          </NCard>
        </NTabPane>

        <NTabPane name="candidates" tab="候选人">
          <div style="margin-top: 12px">
            <NDataTable
              :columns="candidateColumns"
              :data="candidateStore.candidates"
              :loading="candidateStore.loading"
              :bordered="false"
              striped
            />
            <NEmpty
              v-if="!candidateStore.loading && !candidateStore.candidates.length"
              description="暂无候选人"
              style="margin-top: 24px"
            />
          </div>
        </NTabPane>

        <NTabPane name="matching" tab="智能匹配">
          <div style="margin-top: 12px">
            <NSpace vertical>
              <NButton
                type="primary"
                @click="handleMatch"
                :loading="matchingStore.loading"
              >
                开始匹配
              </NButton>

              <NSpin :show="matchingStore.loading">
                <template v-if="matchingStore.matches.length">
                  <NGrid :cols="1" :x-gap="12" :y-gap="12">
                    <NGridItem v-for="match in matchingStore.matches" :key="match.id">
                      <NCard size="small">
                        <template #header>
                          <NSpace align="center">
                            <span>{{ match.candidate_name || match.candidate_id }}</span>
                            <NTag size="small" type="info">
                              综合匹配度
                            </NTag>
                          </NSpace>
                        </template>
                        <NProgress
                          type="line"
                          :percentage="Math.round(match.overall_score * 100)"
                          :color="match.overall_score >= 0.7 ? '#18a058' : match.overall_score >= 0.4 ? '#f0a020' : '#d03050'"
                          :height="20"
                          :text-inside="true"
                          style="margin-bottom: 16px"
                        />
                        <NDescriptions bordered :column="2" label-placement="left" size="small">
                          <NDescriptionsItem label="技能匹配分">
                            {{ Math.round(match.skill_score * 100) }}%
                          </NDescriptionsItem>
                          <NDescriptionsItem label="经验匹配分">
                            {{ Math.round(match.experience_score * 100) }}%
                          </NDescriptionsItem>
                          <NDescriptionsItem label="学历匹配分">
                            {{ Math.round(match.education_score * 100) }}%
                          </NDescriptionsItem>
                          <NDescriptionsItem label="加分项">
                            {{ Math.round(match.bonus_score * 100) }}%
                          </NDescriptionsItem>
                        </NDescriptions>

                        <div v-if="match.matched_skills?.length" style="margin-top: 12px">
                          <span class="skill-label">匹配技能：</span>
                          <NSpace inline>
                            <NTag v-for="skill in match.matched_skills" :key="skill" size="small" type="success">
                              {{ skill }}
                            </NTag>
                          </NSpace>
                        </div>

                        <div v-if="match.missing_skills?.length" style="margin-top: 8px">
                          <span class="skill-label">缺失技能：</span>
                          <NSpace inline>
                            <NTag v-for="skill in match.missing_skills" :key="skill" size="small" type="error">
                              {{ skill }}
                            </NTag>
                          </NSpace>
                        </div>

                        <div v-if="match.suggestions?.length" style="margin-top: 8px">
                          <span class="skill-label">建议：</span>
                          <p class="detail-text">{{ match.suggestions.join('；') }}</p>
                        </div>
                      </NCard>
                    </NGridItem>
                  </NGrid>
                </template>
                <NEmpty
                  v-else-if="!matchingStore.loading && matchingStarted"
                  description="未找到匹配的候选人"
                  style="margin-top: 24px"
                />
              </NSpin>
            </NSpace>
          </div>
        </NTabPane>
      </NTabs>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.position-detail {
  padding: 24px;
}

.detail-text {
  color: var(--text-secondary);
  line-height: 1.8;
  white-space: pre-wrap;
  margin: 0;
}

.detail-list {
  padding-left: 20px;
  margin: 0;
  color: var(--text-secondary);
  line-height: 2;
}

.skill-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-right: 8px;
}
</style>
