<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NInputNumber, NDatePicker, NButton, NDivider, NCollapse, NCollapseItem, NSpace, NTag, NProgress, NAlert } from 'naive-ui'
import { useMessage } from 'naive-ui'
import * as offersApi from '@/api/hr/offers'
import type { Offer, CreateOfferRequest, SalarySuggestion, OfferTemplate } from '@/api/hr/offers'
import * as candidatesApi from '@/api/hr/candidates'
import * as positionsApi from '@/api/hr/positions'

const props = defineProps<{ show: boolean; editData?: Offer | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const message = useMessage()
const loading = ref(false)
const aiLoading = ref(false)

const showInternal = computed({
  get: () => props.show,
  set: (v) => { if (!v) emit('close') },
})

// ─── 表单字段 ────────────────────────────────────────────────
const candidateId = ref<string | null>(null)
const positionId = ref<string | null>(null)
const templateId = ref<string | null>(null)
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

// ─── 选项数据 ────────────────────────────────────────────────
const candidateOptions = ref<{ label: string; value: string }[]>([])
const positionOptions = ref<{ label: string; value: string }[]>([])
const templateOptions = ref<{ label: string; value: string }[]>([])
const templates = ref<OfferTemplate[]>([])

const employmentTypeOptions = [
  { label: '全职', value: 'full_time' },
  { label: '兼职', value: 'part_time' },
  { label: '合同', value: 'contract' },
  { label: '实习', value: 'intern' },
]

// ─── AI 薪资建议 ─────────────────────────────────────────────
const salarySuggestion = ref<SalarySuggestion | null>(null)

const totalCompensation = computed(() => {
  const base = baseSalary.value ?? 0
  const months = annualBonusMonths.value ?? 0
  const signOn = signOnBonus.value ?? 0
  return base * (12 + months) + signOn
})

const suggestedTotal = computed(() => {
  if (!salarySuggestion.value) return null
  return salarySuggestion.value.total_compensation
})

// ─── 加载选项 ────────────────────────────────────────────────
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

  // 加载模板
  try {
    templates.value = await offersApi.getOfferTemplates()
    templateOptions.value = templates.value.map(t => ({
      label: t.name + (t.is_default ? ' (默认)' : ''),
      value: t.id,
    }))
    // 设置默认模板
    const defaultTpl = templates.value.find(t => t.is_default)
    if (defaultTpl) templateId.value = defaultTpl.id
  } catch {
    // 模板加载失败不影响创建流程
  }

  if (props.editData) {
    fillFormFromEditData(props.editData)
  }
})

function fillFormFromEditData(data: Offer) {
  candidateId.value = data.candidate_id
  positionId.value = data.position_id
  baseSalary.value = data.base_salary
  annualBonusMonths.value = data.annual_bonus_months
  signOnBonus.value = data.sign_on_bonus
  equity.value = data.equity ?? ''
  benefitsSummary.value = data.benefits_summary ?? ''
  employmentType.value = data.employment_type
  proposedStartDate.value = data.proposed_start_date
    ? new Date(data.proposed_start_date).getTime()
    : null
  probationMonths.value = data.probation_months ?? 3
  workLocation.value = data.work_location ?? ''
  expiryDate.value = data.expiry_date
    ? new Date(data.expiry_date).getTime()
    : null
  notes.value = data.notes ?? ''
}

// ─── AI 生成薪资建议 ─────────────────────────────────────────
async function handleGenerateSuggestion() {
  if (!candidateId.value || !positionId.value) {
    message.warning('请先选择候选人和岗位')
    return
  }

  aiLoading.value = true
  try {
    const candidate = candidateOptions.value.find(c => c.value === candidateId.value)
    const position = positionOptions.value.find(p => p.value === positionId.value)

    const result = await offersApi.generateSalaryRecommendation({
      candidate: { id: candidateId.value, name: candidate?.label },
      position: { id: positionId.value, title: position?.label },
    })
    salarySuggestion.value = result as SalarySuggestion
    message.success('AI 薪资建议已生成')
  } catch (e: any) {
    message.error(e?.message ?? '生成建议失败')
  } finally {
    aiLoading.value = false
  }
}

/** 一键应用 AI 建议 */
function applySuggestion() {
  if (!salarySuggestion.value) return
  baseSalary.value = salarySuggestion.value.base_salary
  annualBonusMonths.value = salarySuggestion.value.annual_bonus_months
  signOnBonus.value = salarySuggestion.value.sign_on_bonus
  equity.value = salarySuggestion.value.equity
  message.success('已应用 AI 建议')
}

// ─── AI 自动生成 ─────────────────────────────────────────────
async function handleAiGenerate() {
  if (!positionId.value || !candidateId.value) {
    message.warning('请先选择候选人和岗位')
    return
  }

  aiLoading.value = true
  try {
    const result = await offersApi.generateOffer(positionId.value, candidateId.value)
    salarySuggestion.value = result.suggestion

    // 自动填入 AI 建议值
    if (result.offer) {
      if (result.offer.base_salary != null) baseSalary.value = result.offer.base_salary
      if (result.offer.annual_bonus_months != null) annualBonusMonths.value = result.offer.annual_bonus_months
      if (result.offer.sign_on_bonus != null) signOnBonus.value = result.offer.sign_on_bonus
      if (result.offer.equity) equity.value = result.offer.equity
      if (result.offer.benefits_summary) benefitsSummary.value = result.offer.benefits_summary
      if (result.offer.work_location) workLocation.value = result.offer.work_location
      if (result.offer.probation_months != null) probationMonths.value = result.offer.probation_months
    }
    message.success('AI 已自动生成 Offer 建议')
  } catch (e: any) {
    message.error(e?.message ?? 'AI 生成失败')
  } finally {
    aiLoading.value = false
  }
}

function resetForm() {
  candidateId.value = null
  positionId.value = null
  templateId.value = null
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
  salarySuggestion.value = null
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
    if (templateId.value) payload.template_id = templateId.value
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
    :style="{ width: 'min(700px, calc(100vw - 32px))' }"
    :mask-closable="!loading"
    @after-leave="resetForm"
  >
    <!-- AI 薪资建议区域 -->
    <NCollapse v-if="!editData" class="ai-section">
      <NCollapseItem title="🤖 AI 薪资助手" name="ai">
        <div class="ai-actions">
          <NSpace>
            <NButton
              type="primary"
              :loading="aiLoading"
              :disabled="!candidateId || !positionId"
              @click="handleAiGenerate"
            >
              AI 自动生成
            </NButton>
            <NButton
              :loading="aiLoading"
              :disabled="!candidateId || !positionId"
              @click="handleGenerateSuggestion"
            >
              仅生成建议
            </NButton>
          </NSpace>
        </div>

        <!-- AI 建议展示 -->
        <div v-if="salarySuggestion" class="suggestion-card">
          <div class="suggestion-header">
            <span class="suggestion-title">AI 建议</span>
            <NTag
              :type="salarySuggestion.confidence >= 0.8 ? 'success' : salarySuggestion.confidence >= 0.5 ? 'warning' : 'error'"
              size="small"
            >
              置信度 {{ (salarySuggestion.confidence * 100).toFixed(0) }}%
            </NTag>
          </div>
          <div class="suggestion-body">
            <div class="suggestion-items">
              <div class="suggestion-item">
                <span class="item-label">基础月薪</span>
                <span class="item-value">¥{{ salarySuggestion.base_salary.toLocaleString() }}</span>
              </div>
              <div class="suggestion-item">
                <span class="item-label">年终奖月数</span>
                <span class="item-value">{{ salarySuggestion.annual_bonus_months }} 月</span>
              </div>
              <div class="suggestion-item">
                <span class="item-label">签字费</span>
                <span class="item-value">¥{{ (salarySuggestion.sign_on_bonus ?? 0).toLocaleString() }}</span>
              </div>
              <div class="suggestion-item">
                <span class="item-label">股权/期权</span>
                <span class="item-value">{{ salarySuggestion.equity || '-' }}</span>
              </div>
              <div class="suggestion-item">
                <span class="item-label">市场百分位</span>
                <span class="item-value">P{{ salarySuggestion.market_percentile }}</span>
              </div>
              <div class="suggestion-item total">
                <span class="item-label">总包估算</span>
                <span class="item-value">¥{{ salarySuggestion.total_compensation.toLocaleString() }}</span>
              </div>
            </div>
            <div v-if="salarySuggestion.reasoning" class="suggestion-reason">
              <strong>理由：</strong>{{ salarySuggestion.reasoning }}
            </div>
          </div>
          <NButton size="small" type="primary" ghost @click="applySuggestion" style="margin-top: 8px;">
            ✨ 一键应用建议
          </NButton>
        </div>
      </NCollapseItem>
    </NCollapse>

    <NDivider v-if="!editData" style="margin: 8px 0 16px" />

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

      <NFormItem label="Offer模板">
        <NSelect
          v-model:value="templateId"
          :options="templateOptions"
          clearable
          placeholder="请选择模板（可选）"
        />
      </NFormItem>

      <NDivider style="margin: 8px 0">薪资结构</NDivider>

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

      <div class="total-compensation">
        <span class="total-label">预估总包：</span>
        <span class="total-value">¥{{ totalCompensation.toLocaleString() }}</span>
        <NTag v-if="suggestedTotal" size="small" :type="Math.abs(totalCompensation - suggestedTotal) < suggestedTotal * 0.05 ? 'success' : 'warning'" style="margin-left: 8px;">
          AI建议: ¥{{ suggestedTotal.toLocaleString() }}
        </NTag>
      </div>

      <NDivider style="margin: 8px 0" />

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

<style scoped lang="scss">
@use '@/styles/variables' as *;

.ai-section {
  margin-bottom: 8px;
}

.ai-actions {
  margin-bottom: 12px;
}

.suggestion-card {
  background: $bg-secondary;
  border-radius: $radius-md;
  padding: 12px;
  margin-top: 8px;

  .suggestion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;

    .suggestion-title {
      font-weight: 600;
      font-size: 14px;
      color: $text-primary;
    }
  }

  .suggestion-body {
    .suggestion-items {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;

      @media (max-width: $breakpoint-mobile) {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .suggestion-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 6px 8px;
      background: $bg-card;
      border-radius: $radius-sm;

      .item-label {
        font-size: 11px;
        color: $text-muted;
      }

      .item-value {
        font-size: 14px;
        font-weight: 500;
        color: $text-primary;
      }

      &.total {
        grid-column: 1 / -1;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        background: rgba(var(--accent-info-rgb), 0.06);

        .item-value {
          font-size: 16px;
          color: var(--accent-info);
        }
      }
    }

    .suggestion-reason {
      margin-top: 8px;
      font-size: 12px;
      color: $text-secondary;
      padding: 6px 8px;
      background: $bg-card;
      border-radius: $radius-sm;
      line-height: 1.5;
    }
  }
}

.total-compensation {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: $bg-secondary;
  border-radius: $radius-sm;
  margin-bottom: 12px;

  .total-label {
    font-size: 13px;
    color: $text-secondary;
  }

  .total-value {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin-left: 4px;
  }
}
</style>
