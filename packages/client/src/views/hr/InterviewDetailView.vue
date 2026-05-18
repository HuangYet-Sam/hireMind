<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useInterviewStore } from '@/stores/hr/interviews'
import {
  NPageHeader, NCard, NDescriptions, NDescriptionsItem, NTag, NButton,
  NSpace, NSteps, NStep, NForm, NFormItem, NInput, NSelect, NInputNumber,
  NDivider, NSpin,
} from 'naive-ui'
import { useMessage } from 'naive-ui'
import * as interviewsApi from '@/api/hr/interviews'
import AiContextBar from '@/components/hr/AiContextBar.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const interviewStore = useInterviewStore()

const loading = ref(false)

const interviewTypeLabels: Record<string, string> = {
  phone_screen: '电话筛选',
  technical: '技术面试',
  behavioral: '行为面试',
  hr: 'HR面试',
  final: '终面',
  panel: '群面',
  case_study: '案例面试',
}

const statusConfig: Record<string, { label: string; type: 'default' | 'info' | 'warning' | 'success' | 'error' }> = {
  scheduled: { label: '已安排', type: 'default' },
  confirmed: { label: '已确认', type: 'info' },
  in_progress: { label: '进行中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'error' },
}

const recommendationOptions = [
  { label: '强烈推荐', value: 'strongly_recommend' },
  { label: '推荐', value: 'recommend' },
  { label: '一般', value: 'neutral' },
  { label: '不推荐', value: 'not_recommend' },
  { label: '强烈不推荐', value: 'strongly_not_recommend' },
]

const feedback = ref({
  score: null as number | null,
  recommendation: null as string | null,
  strengths: '',
  weaknesses: '',
  comments: '',
})

const interview = computed(() => interviewStore.current)

const formattedTime = computed(() => {
  if (!interview.value?.scheduled_at) return '-'
  return new Date(interview.value.scheduled_at).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const currentStep = computed(() => {
  const status = interview.value?.status
  const stepMap: Record<string, number> = {
    scheduled: 0,
    confirmed: 1,
    in_progress: 2,
    completed: 3,
  }
  if (status === 'cancelled' || status === 'no_show') return 0
  return stepMap[status ?? 'scheduled'] ?? 0
})

const canCancel = computed(() => {
  const status = interview.value?.status
  return status === 'scheduled' || status === 'confirmed'
})

const canSubmitFeedback = computed(() => {
  const status = interview.value?.status
  return (status === 'completed' || status === 'in_progress') && !interview.value?.summary
})

const showFeedbackSection = computed(() => {
  const status = interview.value?.status
  return status === 'completed' || status === 'in_progress'
})

function goBack() {
  router.push({ name: 'hr.interviews' })
}

async function handleCancel() {
  loading.value = true
  try {
    await interviewStore.cancelInterview(route.params.id as string)
    message.success('面试已取消')
    router.push({ name: 'hr.interviews' })
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    loading.value = false
  }
}

async function submitFeedback() {
  if (!feedback.value.score) {
    message.warning('请填写评分')
    return
  }
  loading.value = true
  try {
    await interviewsApi.submitFeedback(route.params.id as string, feedback.value)
    message.success('反馈提交成功')
    await interviewStore.fetchInterview(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '提交失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  interviewStore.fetchInterview(route.params.id as string)
})
</script>

<template>
  <div class="interview-detail">
    <NSpin :show="interviewStore.loading">
      <NPageHeader title="面试详情" @back="goBack" />

      <AiContextBar
        entity-type="interview"
        :entity-id="(route.params.id as string)"
      />

      <NCard title="面试信息" style="margin-top: 16px">
        <NDescriptions v-if="interview" :column="2" bordered>
          <NDescriptionsItem label="候选人ID">
            {{ interview.candidate_id }}
          </NDescriptionsItem>
          <NDescriptionsItem label="岗位ID">
            {{ interview.position_id }}
          </NDescriptionsItem>
          <NDescriptionsItem label="轮次">
            第 {{ interview.round_number }} 轮
          </NDescriptionsItem>
          <NDescriptionsItem label="面试类型">
            <NTag :type="'primary'" size="small">
              {{ interviewTypeLabels[interview.interview_type] || interview.interview_type }}
            </NTag>
          </NDescriptionsItem>
          <NDescriptionsItem label="计划时间">
            {{ formattedTime }}
          </NDescriptionsItem>
          <NDescriptionsItem label="时长">
            {{ interview.duration_minutes }} 分钟
          </NDescriptionsItem>
          <NDescriptionsItem label="地点/会议链接" :span="2">
            {{ interview.location || '-' }}
          </NDescriptionsItem>
          <NDescriptionsItem label="状态">
            <NTag
              v-if="statusConfig[interview.status]"
              :type="statusConfig[interview.status].type"
              size="small"
            >
              {{ statusConfig[interview.status].label }}
            </NTag>
            <span v-else>{{ interview.status }}</span>
          </NDescriptionsItem>
          <NDescriptionsItem label="备注">
            {{ interview.summary || '-' }}
          </NDescriptionsItem>
        </NDescriptions>
      </NCard>

      <NCard title="状态流转" style="margin-top: 16px">
        <NSteps :current="currentStep">
          <NStep title="已安排" description="面试已安排" />
          <NStep title="已确认" description="面试已确认" />
          <NStep title="进行中" description="面试正在进行" />
          <NStep title="已完成" description="面试已完成" />
        </NSteps>
      </NCard>

      <NCard v-if="showFeedbackSection" title="反馈" style="margin-top: 16px">
        <template v-if="interview?.summary">
          <div class="feedback-summary">{{ interview.summary }}</div>
          <div v-if="interview.overall_score" style="margin-top: 12px">
            <strong>评分：</strong>{{ interview.overall_score }} / 10
          </div>
          <div v-if="interview.recommendation" style="margin-top: 8px">
            <strong>推荐：</strong>{{ interview.recommendation }}
          </div>
        </template>

        <template v-if="canSubmitFeedback">
          <NDivider />
          <NForm label-placement="left" label-width="80">
            <NFormItem label="评分">
              <NInputNumber
                v-model:value="feedback.score"
                :min="1"
                :max="10"
                placeholder="1-10"
                style="width: 200px"
              />
            </NFormItem>
            <NFormItem label="推荐">
              <NSelect
                v-model:value="feedback.recommendation"
                :options="recommendationOptions"
                placeholder="请选择推荐程度"
                style="width: 300px"
              />
            </NFormItem>
            <NFormItem label="优势">
              <NInput
                v-model:value="feedback.strengths"
                type="textarea"
                :rows="3"
                placeholder="请输入候选人优势"
              />
            </NFormItem>
            <NFormItem label="不足">
              <NInput
                v-model:value="feedback.weaknesses"
                type="textarea"
                :rows="3"
                placeholder="请输入候选人不足"
              />
            </NFormItem>
            <NFormItem label="备注">
              <NInput
                v-model:value="feedback.comments"
                type="textarea"
                :rows="3"
                placeholder="请输入备注"
              />
            </NFormItem>
            <NFormItem>
              <NSpace>
                <NButton type="primary" :loading="loading" @click="submitFeedback">
                  提交反馈
                </NButton>
              </NSpace>
            </NFormItem>
          </NForm>
        </template>
      </NCard>

      <NCard v-if="interview?.summary && !showFeedbackSection" title="AI 摘要" style="margin-top: 16px">
        <div class="feedback-summary">{{ interview.summary }}</div>
      </NCard>

      <NSpace style="margin-top: 16px">
        <NButton v-if="canCancel" type="error" :loading="loading" @click="handleCancel">
          取消面试
        </NButton>
      </NSpace>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.interview-detail {
  padding: 24px;
}

.feedback-summary {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--n-text-color);
}
</style>
