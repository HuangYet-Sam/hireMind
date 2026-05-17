<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard, NDescriptions, NDescriptionsItem, NTag, NButton, NSpace, NSpin, NEmpty,
  NRadioGroup, NRadio, useNotification,
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

const canSubmit = computed(() => decision.value !== null)

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

onMounted(loadOffer)
</script>

<template>
  <div style="max-width: 600px; margin: 80px auto; padding: 24px;">
    <NCard title="候选人Offer回应" :segmented="{ content: true }">
      <NSpin v-if="loading" style="display: block; padding: 60px 0;" />
      <NEmpty v-else-if="expired" description="链接已过期或无效">
        <template #extra>
          <p style="color: #999; font-size: 13px;">请联系HR获取新的链接</p>
        </template>
      </NEmpty>
      <template v-else-if="offer">
        <NDescriptions bordered :column="1" size="small" style="margin-bottom: 24px;">
          <NDescriptionsItem label="岗位名称">{{ offer.position_title ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="薪资范围">
            {{ offer.salary_min && offer.salary_max ? `${offer.salary_min} - ${offer.salary_max}` : '-' }}
          </NDescriptionsItem>
          <NDescriptionsItem label="工作地点">{{ offer.location ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="入职日期">{{ offer.start_date ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="Offer状态">
            <NTag :type="offer.status === 'sent' ? 'info' : 'success'" size="small">{{ offer.status }}</NTag>
          </NDescriptionsItem>
        </NDescriptions>

        <div v-if="responded" style="text-align: center; padding: 20px 0;">
          <h3>{{ decision === 'accepted' ? '您已接受此Offer' : '您已拒绝此Offer' }}</h3>
          <p style="color: #999;">如有疑问请联系HR。</p>
        </div>
        <template v-else>
          <h4 style="margin-bottom: 12px;">您的决定</h4>
          <NRadioGroup v-model:value="decision">
            <NSpace vertical>
              <NRadio value="accepted">接受Offer</NRadio>
              <NRadio value="rejected">拒绝Offer</NRadio>
            </NSpace>
          </NRadioGroup>
          <NSpace justify="end" style="margin-top: 20px;">
            <NButton type="primary" :loading="submitting" :disabled="!canSubmit" @click="handleSubmit">
              确认提交
            </NButton>
          </NSpace>
        </template>
      </template>
    </NCard>
  </div>
</template>
