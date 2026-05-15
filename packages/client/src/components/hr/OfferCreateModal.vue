<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NInputNumber, NDatePicker, NButton } from 'naive-ui'
import { useMessage } from 'naive-ui'
import * as offersApi from '@/api/hr/offers'
import type { Offer, CreateOfferRequest } from '@/api/hr/offers'
import * as candidatesApi from '@/api/hr/candidates'
import * as positionsApi from '@/api/hr/positions'

const props = defineProps<{ show: boolean; editData?: Offer | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const message = useMessage()
const loading = ref(false)

const showInternal = computed({
  get: () => props.show,
  set: (v) => { if (!v) emit('close') },
})

const candidateId = ref<string | null>(null)
const positionId = ref<string | null>(null)
const baseSalary = ref<number | null>(null)
const annualBonusMonths = ref<number | null>(null)
const signOnBonus = ref<number | null>(null)
const equity = ref('')
const benefitsSummary = ref('')
const employmentType = ref<string | null>(null)
const proposedStartDate = ref<number | null>(null)
const probationMonths = ref(3)
const workLocation = ref('')
const expiryDate = ref<number | null>(null)
const notes = ref('')

const candidateOptions = ref<{ label: string; value: string }[]>([])
const positionOptions = ref<{ label: string; value: string }[]>([])

const employmentTypeOptions = [
  { label: '全职', value: 'full_time' },
  { label: '兼职', value: 'part_time' },
  { label: '合同', value: 'contract' },
  { label: '实习', value: 'intern' },
]

onMounted(async () => {
  try {
    const [candidatesRes, positionsRes] = await Promise.all([
      candidatesApi.listCandidates({ page_size: 200 }),
      positionsApi.listPositions({ status: 'open', page_size: 200 }),
    ])
    candidateOptions.value = (candidatesRes.items ?? []).map((c) => ({
      label: c.name,
      value: c.id,
    }))
    positionOptions.value = (positionsRes.items ?? []).map((p) => ({
      label: p.title,
      value: p.id,
    }))
  } catch {
    message.error('加载选项数据失败')
  }

  if (props.editData) {
    candidateId.value = props.editData.candidate_id
    positionId.value = props.editData.position_id
    baseSalary.value = props.editData.base_salary
    annualBonusMonths.value = props.editData.annual_bonus_months
    signOnBonus.value = props.editData.sign_on_bonus
    equity.value = props.editData.equity ?? ''
    benefitsSummary.value = props.editData.benefits_summary ?? ''
    employmentType.value = props.editData.employment_type
    proposedStartDate.value = props.editData.proposed_start_date
      ? new Date(props.editData.proposed_start_date).getTime()
      : null
    probationMonths.value = props.editData.probation_months ?? 3
    workLocation.value = props.editData.work_location ?? ''
    expiryDate.value = props.editData.expiry_date
      ? new Date(props.editData.expiry_date).getTime()
      : null
    notes.value = props.editData.notes ?? ''
  }
})

function resetForm() {
  candidateId.value = null
  positionId.value = null
  baseSalary.value = null
  annualBonusMonths.value = null
  signOnBonus.value = null
  equity.value = ''
  benefitsSummary.value = ''
  employmentType.value = null
  proposedStartDate.value = null
  probationMonths.value = 3
  workLocation.value = ''
  expiryDate.value = null
  notes.value = ''
}

async function handleSubmit() {
  if (!candidateId.value) {
    message.warning('请选择候选人')
    return
  }

  loading.value = true
  try {
    const payload: CreateOfferRequest = {
      candidate_id: candidateId.value,
    }
    if (positionId.value) payload.position_id = positionId.value
    if (baseSalary.value != null) payload.base_salary = baseSalary.value
    if (annualBonusMonths.value != null) payload.annual_bonus_months = annualBonusMonths.value
    if (signOnBonus.value != null) payload.sign_on_bonus = signOnBonus.value
    if (equity.value) payload.equity = equity.value
    if (benefitsSummary.value) payload.benefits_summary = benefitsSummary.value
    if (employmentType.value) payload.employment_type = employmentType.value
    if (proposedStartDate.value != null) payload.proposed_start_date = new Date(proposedStartDate.value).toISOString()
    if (probationMonths.value != null) payload.probation_months = probationMonths.value
    if (workLocation.value) payload.work_location = workLocation.value
    if (expiryDate.value != null) payload.expiry_date = new Date(expiryDate.value).toISOString()
    if (notes.value) payload.notes = notes.value

    if (props.editData) {
      await offersApi.updateOffer(props.editData.id, payload)
      message.success('Offer已更新')
    } else {
      await offersApi.createOffer(payload)
      message.success('Offer已创建')
    }

    resetForm()
    showInternal.value = false
    emit('saved')
  } catch (e: any) {
    message.error(e?.message ?? '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <NModal
    v-model:show="showInternal"
    preset="card"
    :title="editData ? '编辑Offer' : '创建Offer'"
    :style="{ width: 'min(560px, calc(100vw - 32px))' }"
    :mask-closable="!loading"
    @after-leave="resetForm"
  >
    <NForm label-placement="left" label-width="100">
      <NFormItem label="候选人" required>
        <NSelect
          v-model:value="candidateId"
          :options="candidateOptions"
          :disabled="!!editData"
          filterable
          placeholder="请选择候选人"
        />
      </NFormItem>

      <NFormItem label="关联岗位">
        <NSelect
          v-model:value="positionId"
          :options="positionOptions"
          filterable
          clearable
          placeholder="请选择岗位"
        />
      </NFormItem>

      <NFormItem label="基础月薪">
        <NInputNumber
          v-model:value="baseSalary"
          :min="0"
          :precision="2"
          placeholder="请输入基础月薪"
          style="width: 100%"
        />
      </NFormItem>

      <NFormItem label="年终奖月数">
        <NInputNumber
          v-model:value="annualBonusMonths"
          :min="0"
          :max="12"
          placeholder="请输入年终奖月数"
          style="width: 100%"
        />
      </NFormItem>

      <NFormItem label="签字费">
        <NInputNumber
          v-model:value="signOnBonus"
          :min="0"
          :precision="2"
          placeholder="请输入签字费"
          style="width: 100%"
        />
      </NFormItem>

      <NFormItem label="股权/期权">
        <NInput v-model:value="equity" placeholder="请输入股权/期权信息" />
      </NFormItem>

      <NFormItem label="福利概述">
        <NInput
          v-model:value="benefitsSummary"
          type="textarea"
          :rows="3"
          placeholder="请输入福利概述"
        />
      </NFormItem>

      <NFormItem label="用工类型">
        <NSelect
          v-model:value="employmentType"
          :options="employmentTypeOptions"
          clearable
          placeholder="请选择用工类型"
        />
      </NFormItem>

      <NFormItem label="预计入职日期">
        <NDatePicker
          v-model:value="proposedStartDate"
          type="date"
          style="width: 100%"
          clearable
        />
      </NFormItem>

      <NFormItem label="试用期(月)">
        <NInputNumber
          v-model:value="probationMonths"
          :min="0"
          :max="12"
          placeholder="试用期月数"
          style="width: 100%"
        />
      </NFormItem>

      <NFormItem label="工作地点">
        <NInput v-model:value="workLocation" placeholder="请输入工作地点" />
      </NFormItem>

      <NFormItem label="Offer有效期">
        <NDatePicker
          v-model:value="expiryDate"
          type="date"
          style="width: 100%"
          clearable
        />
      </NFormItem>

      <NFormItem label="备注">
        <NInput
          v-model:value="notes"
          type="textarea"
          :rows="3"
          placeholder="请输入备注"
        />
      </NFormItem>
    </NForm>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: 8px">
        <NButton @click="showInternal = false">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">
          {{ editData ? '保存' : '创建' }}
        </NButton>
      </div>
    </template>
  </NModal>
</template>
