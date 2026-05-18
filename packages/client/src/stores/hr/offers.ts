import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as offersApi from '@/api/hr/offers'
import type {
  Offer,
  OfferListParams,
  CreateOfferRequest,
  UpdateOfferRequest,
  SalarySuggestion,
  CompensationBenchmark,
  ApprovalHistory,
  ApprovalNode,
  OfferTemplate,
  NegotiationAdvice,
} from '@/api/hr/offers'

export const useOfferStore = defineStore('hr-offers', () => {
  // ─── 基础状态 ──────────────────────────────────────────────
  const offers = ref<Offer[]>([])
  const current = ref<Offer | null>(null)
  const loading = ref(false)
  const total = ref(0)

  // ─── M6 新增状态 ───────────────────────────────────────────
  const salarySuggestion = ref<SalarySuggestion | null>(null)
  const compensationBenchmark = ref<CompensationBenchmark | null>(null)
  const approvalHistory = ref<ApprovalHistory[]>([])
  const approvalNodes = ref<ApprovalNode[]>([])
  const offerTemplates = ref<OfferTemplate[]>([])
  const negotiationAdvice = ref<NegotiationAdvice | null>(null)
  const detailLoading = ref(false)

  // ─── 计算属性 ──────────────────────────────────────────────
  const pendingOffers = computed(() => offers.value.filter(o =>
    o.status === 'pending_approval' || o.status === 'approved'
  ))

  const acceptedOffers = computed(() => offers.value.filter(o => o.status === 'accepted'))

  const statsCards = computed(() => {
    const list = offers.value
    return {
      total: total.value || list.length,
      pendingApproval: list.filter(o => o.status === 'pending_approval').length,
      sent: list.filter(o => o.status === 'sent').length,
      accepted: list.filter(o => o.status === 'accepted').length,
      rejected: list.filter(o => o.status === 'rejected').length,
    }
  })

  // ─── 基础 CRUD ──────────────────────────────────────────────
  async function fetchOffers(params?: OfferListParams) {
    loading.value = true
    try {
      const res = await offersApi.listOffers(params)
      offers.value = res.items
      total.value = res.total
    } catch (err) {
      console.error('Failed to fetch offers:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchOffer(id: string) {
    loading.value = true
    detailLoading.value = true
    try {
      current.value = await offersApi.getOffer(id)
    } catch (err) {
      console.error('Failed to fetch offer:', err)
    } finally {
      loading.value = false
      detailLoading.value = false
    }
  }

  async function createOffer(data: CreateOfferRequest): Promise<Offer> {
    const offer = await offersApi.createOffer(data)
    offers.value.unshift(offer)
    return offer
  }

  async function updateOffer(id: string, data: UpdateOfferRequest): Promise<Offer> {
    const offer = await offersApi.updateOffer(id, data)
    const idx = offers.value.findIndex(o => o.id === id)
    if (idx !== -1) offers.value[idx] = offer
    if (current.value?.id === id) current.value = offer
    return offer
  }

  async function approveOffer(id: string, comment?: string) {
    const offer = await offersApi.approveOffer(id, comment)
    const idx = offers.value.findIndex(o => o.id === id)
    if (idx !== -1) offers.value[idx] = offer
    if (current.value?.id === id) current.value = offer
  }

  async function sendOffer(id: string) {
    const offer = await offersApi.sendOffer(id)
    const idx = offers.value.findIndex(o => o.id === id)
    if (idx !== -1) offers.value[idx] = offer
    if (current.value?.id === id) current.value = offer
  }

  // ─── M6 新增 Actions ───────────────────────────────────────

  /** AI 生成 Offer */
  async function generateOffer(positionId: string, candidateId: string) {
    loading.value = true
    try {
      const result = await offersApi.generateOffer(positionId, candidateId)
      salarySuggestion.value = result.suggestion
      return result
    } catch (err) {
      console.error('Failed to generate offer:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /** 审批 Offer */
  async function approveOfferWithData(id: string, data: { comment?: string; approved: boolean }) {
    loading.value = true
    try {
      const offer = await offersApi.approveOfferWithData(id, data)
      const idx = offers.value.findIndex(o => o.id === id)
      if (idx !== -1) offers.value[idx] = offer
      if (current.value?.id === id) current.value = offer
      return offer
    } finally {
      loading.value = false
    }
  }

  /** 拒绝 Offer */
  async function rejectOfferWithData(id: string, data: { reason: string }) {
    loading.value = true
    try {
      const offer = await offersApi.rejectOfferWithData(id, data)
      const idx = offers.value.findIndex(o => o.id === id)
      if (idx !== -1) offers.value[idx] = offer
      if (current.value?.id === id) current.value = offer
      return offer
    } finally {
      loading.value = false
    }
  }

  /** 撤回 Offer */
  async function withdrawOffer(id: string, reason?: string) {
    loading.value = true
    try {
      await offersApi.withdrawOfferWithData(id, reason ? { reason } : undefined)
      offers.value = offers.value.filter(o => o.id !== id)
      if (current.value?.id === id) current.value = null
    } finally {
      loading.value = false
    }
  }

  /** 反报价 */
  async function counterOffer(id: string, data: offersApi.CounterOfferRequest) {
    loading.value = true
    try {
      const offer = await offersApi.counterOffer(id, data)
      const idx = offers.value.findIndex(o => o.id === id)
      if (idx !== -1) offers.value[idx] = offer
      if (current.value?.id === id) current.value = offer
      return offer
    } finally {
      loading.value = false
    }
  }

  /** 获取薪资对标 */
  async function fetchBenchmark(offerId: string) {
    try {
      compensationBenchmark.value = await offersApi.getCompensationBenchmark(offerId)
    } catch (err) {
      console.error('Failed to fetch benchmark:', err)
    }
  }

  /** 获取谈判建议 */
  async function fetchNegotiationAdvice(offerId: string) {
    try {
      negotiationAdvice.value = await offersApi.getNegotiationAdvice(offerId)
    } catch (err) {
      console.error('Failed to fetch negotiation advice:', err)
    }
  }

  /** 获取审批历史 */
  async function fetchApprovalHistory(offerId: string) {
    try {
      approvalHistory.value = await offersApi.getApprovalHistory(offerId)
    } catch (err) {
      console.error('Failed to fetch approval history:', err)
    }
  }

  /** 获取 Offer 模板 */
  async function fetchOfferTemplates() {
    try {
      offerTemplates.value = await offersApi.getOfferTemplates()
    } catch (err) {
      console.error('Failed to fetch offer templates:', err)
    }
  }

  /** 创建 Offer 模板 */
  async function createOfferTemplate(data: { name: string; description?: string; content: string; is_default?: boolean }) {
    const template = await offersApi.createOfferTemplate(data)
    offerTemplates.value.push(template)
    return template
  }

  /** 清除详情数据 */
  function clearDetail() {
    current.value = null
    salarySuggestion.value = null
    compensationBenchmark.value = null
    approvalHistory.value = []
    approvalNodes.value = []
    negotiationAdvice.value = null
  }

  return {
    // state
    offers, current, loading, total, detailLoading,
    salarySuggestion, compensationBenchmark, approvalHistory, approvalNodes,
    offerTemplates, negotiationAdvice,
    // computed
    pendingOffers, acceptedOffers, statsCards,
    // actions
    fetchOffers, fetchOffer, createOffer, updateOffer, approveOffer, sendOffer,
    generateOffer, approveOfferWithData, rejectOfferWithData, withdrawOffer,
    counterOffer, fetchBenchmark, fetchNegotiationAdvice, fetchApprovalHistory,
    fetchOfferTemplates, createOfferTemplate, clearDetail,
  }
})
