<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NPageHeader, NCard, NDescriptions, NDescriptionsItem, NTag, NButton, NSpace,
  NSteps, NStep, NDivider, NSpin, NAvatar, NProgress, NTimeline, NTimelineItem,
  NModal, NInput, NForm, NFormItem, useMessage,
} from 'naive-ui'
import { useOfferStore } from '@/stores/hr/offers'
import * as offersApi from '@/api/hr/offers'
import type { ApprovalNode, ApprovalHistory, CompensationBenchmark } from '@/api/hr/offers'
import AiContextBar from '@/components/hr/AiContextBar.vue'
import OfferApprovalFlow from '@/components/hr/OfferApprovalFlow.vue'
import CompensationChart from '@/components/hr/CompensationChart.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const offerStore = useOfferStore()

const offer = computed(() => offerStore.current)
const actionLoading = ref(false)

// ─── 审批流程数据 ────────────────────────────────────────────
const approvalNodes = ref<ApprovalNode[]>([])
const approvalHistory = ref<ApprovalHistory[]>([])

// ─── 薪资对标数据 ────────────────────────────────────────────
const benchmark = ref<CompensationBenchmark | null>(null)

// ─── 反报价弹窗 ──────────────────────────────────────────────
const showCounterModal = ref(false)
const counterBaseSalary = ref<number | null>(null)
const counterBonusMonths = ref<number | null>(null)
const counterEquity = ref('')
const counterSignOnBonus = ref<number | null>(null)
const counterReason = ref('')
const counterLoading = ref(false)

// ─── 拒绝弹窗 ────────────────────────────────────────────────
const showRejectModal = ref(false)
const rejectReason = ref('')
const rejectLoading = ref(false)

const statusConfig: Record<string, { label: string; type: string }> = {
  draft: { label: '草稿', type: 'default' },
  pending_approval: { label: '待审批', type: 'warning' },
  approved: { label: '已审批', type: 'info' },
  sent: { label: '已发送', type: 'info' },
  accepted: { label: '已接受', type: 'success' },
  rejected: { label: '已拒绝', type: 'error' },
  withdrawn: { label: '已撤回', type: 'default' },
  expired: { label: '已过期', type: 'error' },
  countered: { label: '反报价', type: 'warning' },
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
    countered: 3,
  }
  return map[s] ?? 0
})

const stepStatus = computed(() => {
  const s = offer.value?.status
  if (s === 'rejected' || s === 'withdrawn' || s === 'expired') return 'error' as const
  return 'process' as const
})

// ─── 面试评分摘要 ────────────────────────────────────────────
const interviewScores = computed(() => offer.value?.interview_scores ?? [])
const avgInterviewScore = computed(() => {
  const scores = interviewScores.value
  if (!scores.length) return null
  return (scores.reduce((sum, s) => sum + s.score, 0) / scores.length).toFixed(1)
})

// ─── 匹配分数 ────────────────────────────────────────────────
const matchScore = computed(() => offer.value?.match_score ?? null)

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

// ─── 加载数据 ────────────────────────────────────────────────
async function loadAllData() {
  const id = route.params.id as string
  await offerStore.fetchOffer(id)

  // 并行加载附加数据
  try {
    const [nodes, history, bench] = await Promise.allSettled([
      offersApi.getApprovalHistory(id).catch(() => []),
      offersApi.getApprovalHistory(id),
      offersApi.getCompensationBenchmark(id).catch(() => null),
    ])
    if (history.status === 'fulfilled') approvalHistory.value = history.value
    if (bench.status === 'fulfilled' && bench.value) benchmark.value = bench.value
  } catch {
    // 非关键数据，加载失败不影响页面
  }
}

// ─── 操作 ────────────────────────────────────────────────────
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
    await loadAllData()
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleRejectConfirm() {
  rejectLoading.value = true
  try {
    await offersApi.rejectOfferWithData(route.params.id as string, { reason: rejectReason.value || '审批拒绝' })
    message.success('已拒绝')
    showRejectModal.value = false
    rejectReason.value = ''
    await loadAllData()
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    rejectLoading.value = false
  }
}

async function handleSend() {
  actionLoading.value = true
  try {
    await offersApi.sendOffer(route.params.id as string)
    message.success('Offer已发送')
    await loadAllData()
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

async function handleCounterOffer() {
  counterLoading.value = true
  try {
    await offersApi.counterOffer(route.params.id as string, {
      expected_base_salary: counterBaseSalary.value ?? undefined,
      expected_bonus_months: counterBonusMonths.value ?? undefined,
      expected_equity: counterEquity.value || undefined,
      expected_sign_on_bonus: counterSignOnBonus.value ?? undefined,
      reason: counterReason.value,
    })
    message.success('反报价已提交')
    showCounterModal.value = false
    resetCounterForm()
    await loadAllData()
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    counterLoading.value = false
  }
}

function resetCounterForm() {
  counterBaseSalary.value = null
  counterBonusMonths.value = null
  counterEquity.value = ''
  counterSignOnBonus.value = null
  counterReason.value = ''
}

function openCounterModal() {
  if (offer.value) {
    counterBaseSalary.value = offer.value.base_salary
    counterBonusMonths.value = offer.value.annual_bonus_months
    counterEquity.value = offer.value.equity ?? ''
    counterSignOnBonus.value = offer.value.sign_on_bonus
  }
  showCounterModal.value = true
}

// ─── 审批流程操作 ────────────────────────────────────────────
async function handleNodeApprove(nodeId: string) {
  actionLoading.value = true
  try {
    await offersApi.approveOffer(route.params.id as string)
    message.success('审批通过')
    await loadAllData()
  } catch (e: any) {
    message.error(e?.message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleNodeReject(nodeId: string) {
  showRejectModal.value = true
}

onMounted(loadAllData)
</script>

<template>
  <div class="offer-detail">
    <NPageHeader title="Offer 详情" @back="goBack" />

    <AiContextBar
      entity-type="offer"
      :entity-id="(route.params.id as string)"
    />

    <NSpin :show="offerStore.loading">
      <template v-if="offer">
        <!-- 360° 决策上下文：候选人摘要 -->
        <NCard title="候选人概览" class="section-card">
          <div class="candidate-context">
            <div class="context-item">
              <span class="context-label">候选人</span>
              <span class="context-value">{{ offer.candidate_name || offer.candidate_id }}</span>
            </div>
            <div class="context-item">
              <span class="context-label">岗位</span>
              <span class="context-value">{{ offer.position_title || offer.position_id || '-' }}</span>
            </div>
            <div class="context-item">
              <span class="context-label">状态</span>
              <NTag
                v-if="statusConfig[offer.status]"
                :type="statusConfig[offer.status].type as any"
                size="small"
              >
                {{ statusConfig[offer.status].label }}
              </NTag>
            </div>

            <!-- 面试评分 -->
            <div v-if="interviewScores.length" class="context-item">
              <span class="context-label">面试评分</span>
              <div class="score-badges">
                <NTag
                  v-for="score in interviewScores"
                  :key="score.round"
                  size="small"
                  :type="score.score >= 7 ? 'success' : score.score >= 5 ? 'warning' : 'error'"
                  round
                >
                  R{{ score.round }}: {{ score.score }}/10
                </NTag>
                <NTag size="small" type="info" round>
                  均分: {{ avgInterviewScore }}
                </NTag>
              </div>
            </div>

            <!-- 匹配分数 -->
            <div v-if="matchScore != null" class="context-item">
              <span class="context-label">匹配分数</span>
              <NProgress
                type="circle"
                :percentage="matchScore"
                :width="48"
                :color="matchScore >= 80 ? 'var(--success)' : matchScore >= 60 ? 'var(--warning)' : 'var(--error)'"
              >
                {{ matchScore }}
              </NProgress>
            </div>
          </div>
        </NCard>

        <!-- 状态流转 -->
        <NCard title="状态流转" class="section-card">
          <NSteps :current="currentStep" :status="stepStatus">
            <NStep title="草稿" />
            <NStep title="待审批" />
            <NStep title="已审批" />
            <NStep title="已发送" />
            <NStep title="已接受" />
          </NSteps>
        </NCard>

        <!-- 审批流程可视化 -->
        <NCard title="审批流程" class="section-card">
          <OfferApprovalFlow
            :approvals="approvalNodes"
            :current-status="offer.status"
            @approve="handleNodeApprove"
            @reject="handleNodeReject"
          />
        </NCard>

        <!-- Offer 详情 -->
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

        <!-- 薪资对标图表 -->
        <NCard v-if="benchmark" title="薪资对标" class="section-card">
          <CompensationChart :benchmark="benchmark" />
        </NCard>

        <!-- 操作历史时间轴 -->
        <NCard title="操作历史" class="section-card">
          <NTimeline v-if="approvalHistory.length">
            <NTimelineItem
              v-for="item in approvalHistory"
              :key="item.id"
              :type="
                item.action === 'approved' ? 'success' :
                item.action === 'rejected' ? 'error' :
                item.action === 'withdrawn' ? 'warning' :
                'info'
              "
            >
              <div class="history-item">
                <div class="history-header">
                  <span class="history-action">
                    {{
                      { approved: '审批通过', rejected: '审批拒绝', withdrawn: '撤回', submitted: '提交', sent: '发送', countered: '反报价', status_changed: '状态变更' }[item.action]
                      ?? item.action
                    }}
                  </span>
                  <span class="history-actor">{{ item.actor_name }}</span>
                  <span class="history-time">{{ formatDate(item.created_at) }}</span>
                </div>
                <div v-if="item.from_status || item.to_status" class="history-status-change">
                  <NTag v-if="item.from_status" size="tiny" :type="statusConfig[item.from_status]?.type as any || 'default'">
                    {{ statusConfig[item.from_status]?.label || item.from_status }}
                  </NTag>
                  <span class="arrow">→</span>
                  <NTag v-if="item.to_status" size="tiny" :type="statusConfig[item.to_status]?.type as any || 'default'">
                    {{ statusConfig[item.to_status]?.label || item.to_status }}
                  </NTag>
                </div>
                <div v-if="item.comment" class="history-comment">{{ item.comment }}</div>
              </div>
            </NTimelineItem>
          </NTimeline>
          <div v-else class="empty-history">暂无操作记录</div>
        </NCard>

        <!-- 操作按钮区 -->
        <NCard title="操作" class="section-card">
          <NSpace>
            <NButton v-if="offer.status === 'draft'" type="primary" :loading="actionLoading" @click="handleSubmitApproval">
              提交审批
            </NButton>

            <template v-if="offer.status === 'pending_approval'">
              <NButton type="success" :loading="actionLoading" @click="handleApprove">
                批准
              </NButton>
              <NButton type="error" :loading="actionLoading" @click="showRejectModal = true">
                拒绝
              </NButton>
            </template>

            <NButton v-if="offer.status === 'approved'" type="primary" :loading="actionLoading" @click="handleSend">
              发送Offer
            </NButton>

            <template v-if="offer.status === 'sent'">
              <NButton type="warning" :loading="actionLoading" @click="openCounterModal">
                反报价
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

    <!-- 拒绝弹窗 -->
    <NModal v-model:show="showRejectModal" preset="dialog" title="拒绝Offer" positive-text="确认" negative-text="取消"
      :loading="rejectLoading"
      @positive-click="handleRejectConfirm"
    >
      <NFormItem label="拒绝理由">
        <NInput v-model:value="rejectReason" type="textarea" :rows="3" placeholder="请输入拒绝理由" />
      </NFormItem>
    </NModal>

    <!-- 反报价弹窗 -->
    <NModal
      v-model:show="showCounterModal"
      preset="card"
      title="反报价"
      style="width: min(500px, calc(100vw - 32px))"
    >
      <NForm label-placement="left" label-width="100">
        <NFormItem label="期望月薪">
          <NInputNumber v-model:value="counterBaseSalary" :min="0" style="width: 100%" placeholder="期望月薪" />
        </NFormItem>
        <NFormItem label="年终奖月数">
          <NInputNumber v-model:value="counterBonusMonths" :min="0" :max="12" style="width: 100%" placeholder="年终奖月数" />
        </NFormItem>
        <NFormItem label="签字费">
          <NInputNumber v-model:value="counterSignOnBonus" :min="0" style="width: 100%" placeholder="签字费" />
        </NFormItem>
        <NFormItem label="股权/期权">
          <NInput v-model:value="counterEquity" placeholder="股权/期权" />
        </NFormItem>
        <NFormItem label="理由" required>
          <NInput v-model:value="counterReason" type="textarea" :rows="3" placeholder="请说明反报价理由" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCounterModal = false">取消</NButton>
          <NButton type="primary" :loading="counterLoading" @click="handleCounterOffer">提交反报价</NButton>
        </NSpace>
      </template>
    </NModal>
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

.candidate-context {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: center;

  .context-item {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .context-label {
      font-size: 12px;
      color: $text-muted;
    }

    .context-value {
      font-size: 14px;
      font-weight: 500;
      color: $text-primary;
    }
  }

  .score-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
}

.history-item {
  .history-header {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 4px;

    .history-action {
      font-weight: 500;
      font-size: 14px;
      color: $text-primary;
    }

    .history-actor {
      font-size: 13px;
      color: $text-secondary;
    }

    .history-time {
      font-size: 12px;
      color: $text-muted;
    }
  }

  .history-status-change {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;

    .arrow {
      color: $text-muted;
    }
  }

  .history-comment {
    font-size: 13px;
    color: $text-secondary;
    padding: 4px 8px;
    background: $bg-secondary;
    border-radius: $radius-sm;
    margin-top: 4px;
  }
}

.empty-history {
  text-align: center;
  padding: 24px;
  color: $text-muted;
  font-size: 14px;
}
</style>
