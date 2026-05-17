<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard, NForm, NFormItem, NInput, NButton, NRate, NSpace, NSpin, NEmpty,
  NDescriptions, NDescriptionsItem, useNotification,
} from 'naive-ui'
import { publicGet, publicPost } from '@/api/hr/public'

const route = useRoute()
const notification = useNotification()

const token = route.params.token as string
const loading = ref(true)
const expired = ref(false)
const submitting = ref(false)
const submitted = ref(false)
const context = ref<any>(null)

const form = ref({
  rating: 0,
  comment: '',
  interviewerFeedback: '',
})

async function loadContext() {
  loading.value = true
  try {
    context.value = await publicGet(`/feedback/${token}`)
  } catch (e: any) {
    if (e?.message?.includes('401') || e?.message?.includes('expired') || e?.message?.includes('invalid')) {
      expired.value = true
    } else {
      notification.error({ title: '加载失败', content: '无法获取反馈表单', duration: 3000 })
    }
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  submitting.value = true
  try {
    await publicPost(`/feedback/${token}`, form.value)
    notification.success({ title: '提交成功', content: '感谢您的反馈！', duration: 3000 })
    submitted.value = true
  } catch {
    notification.error({ title: '提交失败', content: '请稍后重试', duration: 3000 })
  } finally {
    submitting.value = false
  }
}

onMounted(loadContext)
</script>

<template>
  <div style="max-width: 600px; margin: 80px auto; padding: 24px;">
    <NCard title="面试反馈" :segmented="{ content: true }">
      <NSpin v-if="loading" style="display: block; padding: 60px 0;" />
      <NEmpty v-else-if="expired" description="链接已过期或无效">
        <template #extra>
          <p style="color: #999; font-size: 13px;">请联系HR获取新的反馈链接</p>
        </template>
      </NEmpty>
      <template v-else>
        <NDescriptions v-if="context" bordered :column="1" size="small" style="margin-bottom: 20px;">
          <NDescriptionsItem label="候选人">{{ context.candidate_name ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="岗位">{{ context.position_title ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="面试类型">{{ context.interview_type ?? '-' }}</NDescriptionsItem>
        </NDescriptions>
        <div v-if="submitted" style="text-align: center; padding: 40px 0;">
          <h3>感谢您的反馈！</h3>
          <p style="color: #999;">您的意见对我们非常重要。</p>
        </div>
        <NForm v-else>
          <NFormItem label="总体评分">
            <NRate v-model:value="form.rating" />
          </NFormItem>
          <NFormItem label="评价意见">
            <NInput
              v-model:value="form.comment"
              type="textarea"
              placeholder="请输入您对面试过程、面试官等方面的评价..."
              :rows="4"
            />
          </NFormItem>
          <NFormItem label="其他建议">
            <NInput
              v-model:value="form.interviewerFeedback"
              type="textarea"
              placeholder="任何其他建议或意见..."
              :rows="3"
            />
          </NFormItem>
          <NSpace justify="end">
            <NButton type="primary" :loading="submitting" @click="handleSubmit">
              提交反馈
            </NButton>
          </NSpace>
        </NForm>
      </template>
    </NCard>
  </div>
</template>
