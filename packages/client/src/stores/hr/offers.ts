import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as offersApi from '@/api/hr/offers'
import type { Offer, OfferListParams, CreateOfferRequest, UpdateOfferRequest } from '@/api/hr/offers'

export const useOfferStore = defineStore('hr-offers', () => {
  const offers = ref<Offer[]>([])
  const current = ref<Offer | null>(null)
  const loading = ref(false)
  const total = ref(0)

  const pendingOffers = computed(() => offers.value.filter(o =>
    o.status === 'pending_approval' || o.status === 'approved'
  ))

  const acceptedOffers = computed(() => offers.value.filter(o => o.status === 'accepted'))

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
    try {
      current.value = await offersApi.getOffer(id)
    } catch (err) {
      console.error('Failed to fetch offer:', err)
    } finally {
      loading.value = false
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
  }

  async function sendOffer(id: string) {
    const offer = await offersApi.sendOffer(id)
    const idx = offers.value.findIndex(o => o.id === id)
    if (idx !== -1) offers.value[idx] = offer
  }

  return {
    offers, current, loading, total, pendingOffers, acceptedOffers,
    fetchOffers, fetchOffer, createOffer, updateOffer, approveOffer, sendOffer,
  }
})
