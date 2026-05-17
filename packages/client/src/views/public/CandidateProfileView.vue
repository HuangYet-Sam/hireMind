<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard, NForm, NFormItem, NInput, NButton, NSpace, NSpin, NEmpty,
  NDescriptions, NDescriptionsItem, useNotification,
} from 'naive-ui'
import { publicGet, publicPost } from '@/api/hr/public'

const route = useRoute()
const notification = useNotification()

const token = route.params.token as string
const loading = ref(true)
const expired = ref(false)
const saving = ref(false)
const profile = ref<any>(null)

const form = ref({
  name: '',
  phone: '',
  email: '',
  education: '',
  experience: '',
})

async function loadProfile() {
  loading.value = true
  try {
    const data = await publicGet(`/candidate/${token}/profile`)
    profile.value = data
    if (data) {
      form.value.name = data.name ?? ''
      form.value.phone = data.phone ?? ''
      form.value.email = data.email ?? ''
      form.value.education = data.education ?? ''
      form.value.experience = data.experience ?? ''
    }
  } catch (e: any) {
    if (e?.message?.includes('401') || e?.message?.includes('expired') || e?.message?.includes('invalid')) {
      expired.value = true
    } else {
      notification.error({ title: '加载失败', content: '无法获取候选人信息', duration: 3000 })
    }
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await publicPost(`/candidate/${token}/profile`, form.value)
    notification.success({ title: '保存成功', content: '您的信息已更新', duration: 3000 })
  } catch {
    notification.error({ title: '保存失败', content: '请稍后重试', duration: 3000 })
  } finally {
    saving.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div style="max-width: 600px; margin: 80px auto; padding: 24px;">
    <NCard title="候选人信息更新" :segmented="{ content: true }">
      <NSpin v-if="loading" style="display: block; padding: 60px 0;" />
      <NEmpty v-else-if="expired" description="链接已过期或无效">
        <template #extra>
          <p style="color: #999; font-size: 13px;">请联系HR获取新的链接</p>
        </template>
      </NEmpty>
      <template v-else>
        <NDescriptions v-if="profile" bordered :column="1" size="small" style="margin-bottom: 20px;">
          <NDescriptionsItem label="应聘岗位">{{ profile.position_title ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="当前状态">{{ profile.status ?? '-' }}</NDescriptionsItem>
        </NDescriptions>
        <NForm>
          <NFormItem label="姓名">
            <NInput v-model:value="form.name" placeholder="请输入姓名" />
          </NFormItem>
          <NFormItem label="手机号">
            <NInput v-model:value="form.phone" placeholder="请输入手机号" />
          </NFormItem>
          <NFormItem label="邮箱">
            <NInput v-model:value="form.email" placeholder="请输入邮箱" />
          </NFormItem>
          <NFormItem label="最高学历">
            <NInput v-model:value="form.education" placeholder="请输入最高学历" />
          </NFormItem>
          <NFormItem label="工作经历">
            <NInput
              v-model:value="form.experience"
              type="textarea"
              placeholder="请简要描述您的工作经历..."
              :rows="4"
            />
          </NFormItem>
          <NSpace justify="end">
            <NButton type="primary" :loading="saving" @click="handleSave">
              保存信息
            </NButton>
          </NSpace>
        </NForm>
      </template>
    </NCard>
  </div>
</template>
