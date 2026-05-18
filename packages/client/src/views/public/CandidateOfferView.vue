<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard, NDescriptions, NDescriptionsItem, NTag, NButton, NSpace, NSpin, NEmpty,
  NRadioGroup, NRadio, NInput, NInputNumber, NForm, NFormItem, NDivider,
  NModal, useNotification,
} from 'naive-ui'
import { publicGet, publicPost } from '@/api/hr/public'

const route = useRoute()
const notification = useNotification()

const token = route.params.token as string
const loading = ref(true)
const submitting = ref(false)
const expired = ref(false)
const responded = ref(false)
const offer = ref<any>(null)
const decision = ref<'accepted' | 'rejected' | null>(null)

// ─── 反报价状态 ──────────────────────────────────────────────
const showCounterForm = ref(false)
const counterBaseSalary = ref<number | null>(null)
const counterBonusMonths = ref<number | null>(null)
const counterEquity = ref('')
const counterSignOnBonus = ref<number | null>(null)
const counterReason = ref('')
const counterSubmitting = ref(false)

const canSubmit = computed(() => decision.value !== null)

// ─── 薪资结构展示 ────────────────────────────────────────────
const salaryBreakdown = computed(() => {
  if (!offer.value) return null
  const o = offer.value
  return {
    base: o.base_salary ?? o.salary_min ?? null,
    bonus: o.annual_bonus_months ?? null,
    signOn: o.sign_on_bonus ?? null,
    equity: o.equity ?? null,
    benefits: o.benefits_summary ?? null,
  }
})

const totalPackage = computed(() => {
  const s = salaryBreakdown.value
  if (!s?.base) return null
  const baseYear = s.base * 12
  const bonusYear = s.bonus ? s.base * s.bonus : 0
  const signOn = s.signOn ?? 0
  return baseYear + bonusYear + signOn
})

async function loadOffer() {
  loading.value = true
  try {
    const data = await publicGet(`/candidate/${token}/offer`)
    offer.value = data
    if (data?.candidate_decision) {
      responded.value = true
      decision.value = data.candidate_decision
    }
  } catch (e: any) {
    if (e?.message?.includes('401') || e?.message?.includes('expired') || e?.message?.includes('invalid')) {
      expired.value = true
    } else {
      notification.error({ title: '加载失败', content: '无法获取Offer信息', duration: 3000 })
    }
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!decision.value) return
  submitting.value = true
  try {
    await publicPost(`/candidate/${token}/offer`, { decision: decision.value })
    responded.value = true
    notification.success({
      title: decision.value === 'accepted' ? '已接受Offer' : '已拒绝Offer',
      duration: 3000,
    })
  } catch {
    notification.error({ title: '操作失败', content: '请稍后重试', duration: 3000 })
  } finally {
    submitting.value = false
  }
}

async function handleCounterOffer() {
  if (!counterReason.value.trim()) {
    notification.warning({ title: '请填写理由', duration: 2000 })
    return
  }
  counterSubmitting.value = true
  try {
    await publicPost(`/candidate/${token}/counter-offer`, {
      expected_base_salary: counterBaseSalary.value,
      expected_bonus_months: counterBonusMonths.value,
      expected_equity: counterEquity.value,
      expected_sign_on_bonus: counterSignOnBonus.value,
      reason: counterReason.value,
    })
    notification.success({ title: '反报价已提交', content: 'HR将尽快回复您', duration: 3000 })
    showCounterForm.value = false
    responded.value = true
    decision.value = 'countered'
  } catch {
    notification.error({ title: '提交失败', content: '请稍后重试', duration: 3000 })
  } finally {
    counterSubmitting.value = false
  }
}

function openCounterForm() {
  if (offer.value) {
    counterBaseSalary.value = offer.value.base_salary ?? offer.value.salary_min ?? null
    counterBonusMonths.value = offer.value.annual_bonus_months ?? null
    counterSignOnBonus.value = offer.value.sign_on_bonus ?? null
    counterEquity.value = offer.value.equity ?? ''
  }
  showCounterForm.value = true
}

onMounted(loadOffer)
</script>

<template>
  <div style="max-width: 680px; margin: 40px auto; padding: 24px;">
    <NCard title="候选人Offer回应" :segmented="{ content: true }">
      <NSpin v-if="loading" style="display: block; padding: 60px 0;" />
      <NEmpty v-else-if="expired" description="链接已过期或无效">
        <template #extra>
          <p style="color: #999; font-size: 13px;">请联系HR获取新的链接</p>
        </template>
      </NEmpty>
      <template v-else-if="offer">
        <!-- 基本信息 -->
        <NDescriptions bordered :column="1" size="small" style="margin-bottom: 20px;">
          <NDescriptionsItem label="岗位名称">{{ offer.position_title ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="部门">{{ offer.department ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="工作地点">{{ offer.location ?? offer.work_location ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="入职日期">{{ offer.start_date ?? offer.proposed_start_date ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="用工类型">{{ offer.employment_type ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="试用期">{{ offer.probation_months ? `${offer.probution_months ?? offer.probation_months} 个月` : '-' }}</NDescriptionsItem>
        </NDescriptions>

        <!-- 薪资结构 -->
        <NDivider style="margin: 12px 0">薪资结构</NDivider>
        <div v-if="salaryBreakdown" class="salary-breakdown">
          <div v-if="salaryBreakdown.base" class="salary-row">
            <span class="salary-label">基础月薪</span>
            <span class="salary-value">¥{{ salaryBreakdown.base.toLocaleString() }}</span>
          </div>
          <div v-if="salaryBreakdown.bonus" class="salary-row">
            <span class="salary-label">年终奖</span>
            <span class="salary-value">{{ salaryBreakdown.bonus }} 个月</span>
          </div>
          <div v-if="salaryBreakdown.signOn" class="salary-row">
            <span class="salary-label">签字费</span>
            <span class="salary-value">¥{{ salaryBreakdown.signOn.toLocaleString() }}</span>
          </div>
          <div v-if="salaryBreakdown.equity" class="salary-row">
            <span class="salary-label">股权/期权</span>
            <span class="salary-value">{{ salaryBreakdown.equity }}</span>
          </div>
          <div v-if="totalPackage" class="salary-row salary-total">
            <span class="salary-label">预估年包</span>
            <span class="salary-value">¥{{ totalPackage.toLocaleString() }}</span>
          </div>
        </div>
        <div v-else class="salary-range">
          <span>薪资范围: {{ offer.salary_min && offer.salary_max ? `¥${offer.salary_min.toLocaleString()} - ¥${offer.salary_max.toLocaleString()}` : '-' }}</span>
        </div>

        <!-- 福利 -->
        <template v-if="salaryBreakdown?.benefits">
          <NDivider style="margin: 12px 0">福利概述</NDivider>
          <div class="benefits-text">{{ salaryBreakdown.benefits }}</div>
        </template>

        <!-- Offer状态 -->
        <NDivider style="margin: 12px 0">Offer状态</NDivider>
        <NTag :type="offer.status === 'sent' ? 'info' : 'success'" size="small">
          {{ { sent: '待回应', accepted: '已接受', rejected: '已拒绝', countered: '反报价中' }[offer.status] ?? offer.status }}
        </NTag>

        <!-- 已回应状态 -->
        <div v-if="responded" style="text-align: center; padding: 24px 0;">
          <h3 style="margin: 0 0 8px;">
            {{
              decision === 'accepted' ? '✅ 您已接受此Offer' :
              decision === 'rejected' ? '❌ 您已拒绝此Offer' :
              '💬 反报价已提交'
            }}
          </h3>
          <p style="color: #999; margin: 0;">如有疑问请联系HR。</p>
        </div>

        <!-- 操作区 -->
        <template v-else>
          <NDivider style="margin: 16px 0">您的决定</NDivider>
          <NRadioGroup v-model:value="decision">
            <NSpace vertical>
              <NRadio value="accepted">接受Offer</NRadio>
              <NRadio value="rejected">拒绝Offer</NRadio>
            </NSpace>
          </NRadioGroup>

          <NSpace justify="space-between" style="margin-top: 20px;" align="center">
            <NButton type="warning" ghost @click="openCounterForm">
              提出反报价
            </NButton>
            <NButton type="primary" :loading="submitting" :disabled="!canSubmit" @click="handleSubmit">
              确认提交
            </NButton>
          </NSpace>
        </template>
      </template>
    </NCard>

    <!-- 反报价表单 -->
    <NModal
      v-model:show="showCounterForm"
      preset="card"
      title="提出反报价"
      style="width: min(500px, calc(100vw - 32px)); margin-top: 60px;"
    >
      <p style="color: #666; font-size: 13px; margin-bottom: 16px;">
        请填写您期望的薪资条件，HR将根据您的反馈进行评估。
      </p>
      <NForm label-placement="left" label-width="100">
        <NFormItem label="期望月薪">
          <NInputNumber
            v-model:value="counterBaseSalary"
            :min="0"
            style="width: 100%"
            placeholder="请输入期望月薪"
          />
        </NFormItem>
        <NFormItem label="年终奖月数">
          <NInputNumber
            v-model:value="counterBonusMonths"
            :min="0"
            :max="12"
            style="width: 100%"
            placeholder="请输入期望年终奖月数"
          />
        </NFormItem>
        <NFormItem label="签字费">
          <NInputNumber
            v-model:value="counterSignOnBonus"
            :min="0"
            style="width: 100%"
            placeholder="请输入期望签字费"
          />
        </NFormItem>
        <NFormItem label="股权/期权">
          <NInput v-model:value="counterEquity" placeholder="请输入期望股权/期权" />
        </NFormItem>
        <NFormItem label="理由" required>
          <NInput
            v-model:value="counterReason"
            type="textarea"
            :rows="4"
            placeholder="请说明您的反报价理由，例如：市场行情、个人经验等"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCounterForm = false">取消</NButton>
          <NButton type="primary" :loading="counterSubmitting" @click="handleCounterOffer">
            提交反报价
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.salary-breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.salary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  border-radius: 6px;
  background: #fafafa;
}

.salary-row.salary-total {
  background: rgba(74, 144, 217, 0.06);
  font-weight: 600;
  border-top: 1px solid #e8e8e8;
  margin-top: 4px;
  padding: 10px 12px;
}

.salary-label {
  color: #666;
  font-size: 13px;
}

.salary-value {
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 500;
}

.salary-total .salary-value {
  font-size: 16px;
  color: #4a90d9;
}

.salary-range {
  text-align: center;
  padding: 12px;
  color: #666;
}

.benefits-text {
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}
</style>
