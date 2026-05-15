<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NPageHeader, NCard, NDescriptions, NDescriptionsItem, NTag, NButton, NSpace, NSteps, NStep, NDivider, NSpin } from 'naive-ui'
import { useMessage } from 'naive-ui'
import { useOfferStore } from '@/stores/hr/offers'
import * as offersApi from '@/api/hr/offers'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const offerStore = useOfferStore()

const offer = computed(() => offerStore.current)
const actionLoading = ref(false)

const statusConfig: Record<string, { label: string; type: string }> = {
  draft: { label: '草稿', type: 'default' },
  pending_approval: { label: '待审批', type: 'warning' },
  approved: { label: '已审批', type: 'info' },
  sent: { label: '已发送', type: 'info' },
  accepted: { label: '已接受', type: 'success' },
  rejected: { label: '已拒绝', type: 'error' },
  withdrawn: { label: '已撤回', type: 'default' },
  expired: { label: '已过期', type: 'error' },
}

const currentStep = computed(() => {
  const s = offer.value?.status
  if (!s) return 0
  const map: Record<string, number> = {
    draft: 0,
    pending_approval: 1,
    approved: 2,
    sent: 3,
    accepted: 4,
    rejected: -1,
    withdrawn: -1,
    expired: -1,
  }
  return map[s] ?? 0
})

const stepStatus = computed(() => {
  const s = offer.value?.status
  if (s === 'rejected') return 'error' as const
  if (s === 'withdrawn' || s === 'expired') return 'error' as const
  return 'process' as const
})

function formatDate(date: string | null | undefined): string {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

function formatSalary(value: number | null | undefined): string {
  if (value == null) return '-'
  return `¥${value.toLocaleString('zh-CN')}`
}

function goBack() {
  router.push({ name: 'hr.offers' })
}

async function handleSubmitApproval() {
  actionLoading.value = true
  try {
    await offerStore.updateOffer(route.params.id as string, { status: 'pending_approval' } as any)
    message.success('已提交审批')
    await offerStore.fetchOffer(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleApprove() {
  actionLoading.value = true
  try {
    await offersApi.approveOffer(route.params.id as string)
    message.success('审批通过')
    await offerStore.fetchOffer(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleReject() {
  actionLoading.value = true
  try {
    await offersApi.rejectOffer(route.params.id as string)
    message.success('已拒绝')
    await offerStore.fetchOffer(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleSend() {
  actionLoading.value = true
  try {
    await offersApi.sendOffer(route.params.id as string)
    message.success('Offer已发送')
    await offerStore.fetchOffer(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleMarkAccepted() {
  actionLoading.value = true
  try {
    await offerStore.updateOffer(route.params.id as string, { status: 'accepted' } as any)
    message.success('已标记为接受')
    await offerStore.fetchOffer(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleMarkRejected() {
  actionLoading.value = true
  try {
    await offerStore.updateOffer(route.params.id as string, { status: 'rejected' } as any)
    message.success('已标记为拒绝')
    await offerStore.fetchOffer(route.params.id as string)
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleWithdraw() {
  actionLoading.value = true
  try {
    await offersApi.withdrawOffer(route.params.id as string)
    message.success('Offer已撤回')
    router.push({ name: 'hr.offers' })
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  offerStore.fetchOffer(route.params.id as string)
})
</script>

<template>
  <div class="offer-detail">
    <NPageHeader title="Offer 详情" @back="goBack" />

    <NSpin :show="offerStore.loading">
      <template v-if="offer">
        <NCard title="状态流转" class="section-card">
          <NSteps :current="currentStep" :status="stepStatus">
            <NStep title="草稿" />
            <NStep title="待审批" />
            <NStep title="已审批" />
            <NStep title="已发送" />
            <NStep title="已接受" />
          </NSteps>
        </NCard>

        <NCard title="Offer 详情" class="section-card">
          <NDescriptions bordered :column="2" label-placement="left">
            <NDescriptionsItem label="状态">
              <NTag
                v-if="statusConfig[offer.status]"
                :type="statusConfig[offer.status].type as any"
                size="small"
              >
                {{ statusConfig[offer.status].label }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="候选人ID">{{ offer.candidate_id || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="岗位ID">{{ offer.position_id || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="基础月薪">{{ formatSalary(offer.base_salary) }}</NDescriptionsItem>
            <NDescriptionsItem label="年终奖月数">{{ offer.annual_bonus_months ?? '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="签字费">{{ formatSalary(offer.sign_on_bonus) }}</NDescriptionsItem>
            <NDescriptionsItem label="股权/期权">{{ offer.equity || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="用工类型">{{ offer.employment_type || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="预计入职日期">{{ offer.proposed_start_date || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="试用期">{{ offer.probation_months != null ? `${offer.probation_months} 个月` : '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="工作地点">{{ offer.work_location || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="有效期至">{{ offer.expiry_date || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="福利概述" :span="2">{{ offer.benefits_summary || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="备注" :span="2">{{ offer.notes || '-' }}</NDescriptionsItem>
            <NDescriptionsItem label="创建时间">{{ formatDate(offer.created_at) }}</NDescriptionsItem>
            <NDescriptionsItem label="更新时间">{{ formatDate(offer.updated_at) }}</NDescriptionsItem>
            <NDescriptionsItem label="发送时间">{{ formatDate(offer.sent_at) }}</NDescriptionsItem>
            <NDescriptionsItem label="回复时间">{{ formatDate(offer.responded_at) }}</NDescriptionsItem>
            <NDescriptionsItem label="回复备注" :span="2">{{ offer.response_note || '-' }}</NDescriptionsItem>
          </NDescriptions>
        </NCard>

        <NCard title="操作区域" class="section-card">
          <NSpace>
            <NButton v-if="offer.status === 'draft'" type="primary" :loading="actionLoading" @click="handleSubmitApproval">
              提交审批
            </NButton>

            <template v-if="offer.status === 'pending_approval'">
              <NButton type="success" :loading="actionLoading" @click="handleApprove">
                批准
              </NButton>
              <NButton type="error" :loading="actionLoading" @click="handleReject">
                拒绝
              </NButton>
            </template>

            <NButton v-if="offer.status === 'approved'" type="primary" :loading="actionLoading" @click="handleSend">
              发送Offer
            </NButton>

            <template v-if="offer.status === 'sent'">
              <NButton type="success" :loading="actionLoading" @click="handleMarkAccepted">
                标记接受
              </NButton>
              <NButton type="error" :loading="actionLoading" @click="handleMarkRejected">
                标记拒绝
              </NButton>
            </template>

            <NButton
              v-if="['draft', 'pending_approval', 'approved', 'sent'].includes(offer.status)"
              :loading="actionLoading"
              @click="handleWithdraw"
            >
              撤回
            </NButton>
          </NSpace>
        </NCard>
      </template>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.offer-detail {
  padding: 24px;
}

.section-card {
  margin-top: 20px;
}
</style>
