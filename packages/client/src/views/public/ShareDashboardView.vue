<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard, NSpin, NEmpty, NDescriptions, NDescriptionsItem, NTag, NProgress,
  NStatistic, NGrid, NGi, NDivider, useNotification,
} from 'naive-ui'
import { publicGet } from '@/api/hr/public'

const route = useRoute()
const notification = useNotification()

const token = route.params.token as string
const loading = ref(true)
const expired = ref(false)
const dashboard = ref<any>(null)

async function loadData() {
  loading.value = true
  try {
    dashboard.value = await publicGet(`/share/${token}/dashboard`)
  } catch (e: any) {
    if (e?.message?.includes('401') || e?.message?.includes('expired') || e?.message?.includes('invalid')) {
      expired.value = true
    } else {
      notification.error({ title: '加载失败', content: '无法获取看板数据', duration: 3000 })
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div style="max-width: 960px; margin: 40px auto; padding: 24px;">
    <NCard title="共享招聘看板" :segmented="{ content: true }">
      <NSpin v-if="loading" style="display: block; padding: 60px 0;" />
      <NEmpty v-else-if="expired" description="链接已过期或无效">
        <template #extra>
          <p style="color: #999; font-size: 13px;">请联系HR获取新的共享链接</p>
        </template>
      </NEmpty>
      <template v-else-if="dashboard">
        <NGrid :cols="4" :x-gap="16" :y-gap="16">
          <NGi>
            <NStatistic label="在招岗位" :value="dashboard.open_positions ?? '-'" />
          </NGi>
          <NGi>
            <NStatistic label="候选人总数" :value="dashboard.total_candidates ?? '-'" />
          </NGi>
          <NGi>
            <NStatistic label="本周面试" :value="dashboard.weekly_interviews ?? '-'" />
          </NGi>
          <NGi>
            <NStatistic label="待处理Offer" :value="dashboard.pending_offers ?? '-'" />
          </NGi>
        </NGrid>

        <NDivider />

        <div v-if="dashboard.positions?.length">
          <h4 style="margin-bottom: 12px;">岗位概览</h4>
          <NDescriptions v-for="pos in dashboard.positions" :key="pos.id" bordered :column="3" size="small" style="margin-bottom: 12px;">
            <NDescriptionsItem label="岗位名称">{{ pos.title }}</NDescriptionsItem>
            <NDescriptionsItem label="状态">
              <NTag :type="pos.status === 'open' ? 'success' : 'warning'" size="small">{{ pos.status }}</NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="招聘进度">
              <NProgress :percentage="pos.progress ?? 0" :height="16" />
            </NDescriptionsItem>
          </NDescriptions>
        </div>
      </template>
    </NCard>
  </div>
</template>
