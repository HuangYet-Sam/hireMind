<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NInputNumber, NDatePicker, NButton } from 'naive-ui'
import { useMessage } from 'naive-ui'
import * as interviewsApi from '@/api/hr/interviews'
import * as candidatesApi from '@/api/hr/candidates'
import * as positionsApi from '@/api/hr/positions'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const message = useMessage()

const loading = ref(false)
const showInternal = computed({
  get: () => props.show,
  set: (v) => { if (!v) emit('close') },
})

const formData = ref({
  candidate_id: null as string | null,
  position_id: null as string | null,
  round_number: 1,
  interview_type: null as string | null,
  scheduled_at: null as number | null,
  duration_minutes: 60,
  location: '',
  notes: '',
})

const candidateOptions = ref<{ label: string; value: string }[]>([])
const positionOptions = ref<{ label: string; value: string }[]>([])

const interviewTypeOptions = [
  { label: '电话筛选', value: 'phone_screen' },
  { label: '技术面试', value: 'technical' },
  { label: '行为面试', value: 'behavioral' },
  { label: 'HR面试', value: 'hr' },
  { label: '终面', value: 'final' },
  { label: '群面', value: 'panel' },
  { label: '案例面试', value: 'case_study' },
]

async function loadCandidates() {
  try {
    const res = await candidatesApi.listCandidates({ page: 1, page_size: 200 })
    candidateOptions.value = res.items.map((c) => ({
      label: `${c.name} (${c.email})`,
      value: c.id,
    }))
  } catch {
    message.error('加载候选人列表失败')
  }
}

async function loadPositions() {
  try {
    const res = await positionsApi.listPositions({ status: 'open', page: 1, page_size: 200 })
    positionOptions.value = res.items.map((p) => ({
      label: p.title,
      value: p.id,
    }))
  } catch {
    message.error('加载岗位列表失败')
  }
}

onMounted(() => {
  loadCandidates()
  loadPositions()
})

function resetForm() {
  formData.value = {
    candidate_id: null,
    position_id: null,
    round_number: 1,
    interview_type: null,
    scheduled_at: null,
    duration_minutes: 60,
    location: '',
    notes: '',
  }
}

async function handleSubmit() {
  if (!formData.value.candidate_id) {
    message.warning('请选择候选人')
    return
  }
  if (!formData.value.scheduled_at) {
    message.warning('请选择计划时间')
    return
  }

  loading.value = true
  try {
    const scheduledAt = formData.value.scheduled_at
      ? new Date(formData.value.scheduled_at).toISOString()
      : null

    await interviewsApi.createInterview({
      candidate_id: formData.value.candidate_id,
      position_id: formData.value.position_id || undefined,
      round_number: formData.value.round_number,
      interview_type: (formData.value.interview_type || 'phone_screen') as interviewsApi.Interview['interview_type'],
      scheduled_at: scheduledAt!,
      duration_minutes: formData.value.duration_minutes,
      location: formData.value.location || undefined,
      interviewer_ids: [],
    })
    message.success('面试安排成功')
    resetForm()
    showInternal.value = false
    emit('saved')
  } catch {
    message.error('安排面试失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <NModal
    v-model:show="showInternal"
    preset="card"
    title="安排面试"
    :style="{ width: 'min(520px, calc(100vw - 32px))' }"
    :mask-closable="!loading"
    @after-leave="emit('close')"
  >
    <NForm label-placement="left" label-width="100">
      <NFormItem label="候选人">
        <NSelect
          v-model:value="formData.candidate_id"
          :options="candidateOptions"
          filterable
          placeholder="请选择候选人"
        />
      </NFormItem>
      <NFormItem label="关联岗位">
        <NSelect
          v-model:value="formData.position_id"
          :options="positionOptions"
          filterable
          clearable
          placeholder="请选择岗位"
        />
      </NFormItem>
      <NFormItem label="轮次">
        <NInputNumber v-model:value="formData.round_number" :min="1" style="width: 100%" />
      </NFormItem>
      <NFormItem label="面试类型">
        <NSelect
          v-model:value="formData.interview_type"
          :options="interviewTypeOptions"
          placeholder="请选择面试类型"
        />
      </NFormItem>
      <NFormItem label="计划时间">
        <NDatePicker
          v-model:value="formData.scheduled_at"
          type="datetime"
          style="width: 100%"
          clearable
        />
      </NFormItem>
      <NFormItem label="时长(分钟)">
        <NInputNumber
          v-model:value="formData.duration_minutes"
          :min="15"
          :max="480"
          style="width: 100%"
        />
      </NFormItem>
      <NFormItem label="地点/会议链接">
        <NInput v-model:value="formData.location" placeholder="请输入地点或会议链接" />
      </NFormItem>
      <NFormItem label="备注">
        <NInput
          v-model:value="formData.notes"
          type="textarea"
          :rows="3"
          placeholder="请输入备注"
        />
      </NFormItem>
    </NForm>
    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: 8px">
        <NButton @click="showInternal = false">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">确认安排</NButton>
      </div>
    </template>
  </NModal>
</template>
