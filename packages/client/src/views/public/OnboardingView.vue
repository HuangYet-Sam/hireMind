<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard, NUpload, NButton, NList, NListItem, NSpace, NTag, NSpin, NEmpty,
  NDescriptions, NDescriptionsItem, useNotification,
} from 'naive-ui'
import type { UploadFileInfo } from 'naive-ui'
import { publicGet, publicPost } from '@/api/hr/public'

const route = useRoute()
const notification = useNotification()

const token = route.params.token as string
const loading = ref(true)
const expired = ref(false)
const uploading = ref(false)
const context = ref<any>(null)
const uploadedFiles = ref<{ name: string; status: string }[]>([])

const fileList = ref<UploadFileInfo[]>([])

async function loadContext() {
  loading.value = true
  try {
    context.value = await publicGet(`/onboarding/${token}`)
  } catch (e: any) {
    if (e?.message?.includes('401') || e?.message?.includes('expired') || e?.message?.includes('invalid')) {
      expired.value = true
    } else {
      notification.error({ title: '加载失败', content: '无法获取入职信息', duration: 3000 })
    }
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!fileList.value.length) {
    notification.warning({ title: '请先选择文件', duration: 2000 })
    return
  }
  uploading.value = true
  try {
    await publicPost(`/onboarding/${token}/submit`, {
      files: fileList.value.map((f) => f.name),
    })
    for (const f of fileList.value) {
      uploadedFiles.value.push({ name: f.name, status: '已上传' })
    }
    notification.success({ title: '上传成功', content: '入职材料已提交', duration: 3000 })
    fileList.value = []
  } catch {
    notification.error({ title: '上传失败', content: '请稍后重试', duration: 3000 })
  } finally {
    uploading.value = false
  }
}

onMounted(loadContext)
</script>

<template>
  <div style="max-width: 600px; margin: 80px auto; padding: 24px;">
    <NCard title="入职材料上传" :segmented="{ content: true }">
      <NSpin v-if="loading" style="display: block; padding: 60px 0;" />
      <NEmpty v-else-if="expired" description="链接已过期或无效">
        <template #extra>
          <p style="color: #999; font-size: 13px;">请联系HR获取新的链接</p>
        </template>
      </NEmpty>
      <template v-else>
        <NDescriptions v-if="context" bordered :column="1" size="small" style="margin-bottom: 16px;">
          <NDescriptionsItem label="候选人">{{ context.candidate_name ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="岗位">{{ context.position_title ?? '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="入职日期">{{ context.start_date ?? '-' }}</NDescriptionsItem>
        </NDescriptions>
        <p style="color: #666; margin-bottom: 16px;">
          请上传您的入职所需材料，包括身份证、学历证明、离职证明等。
        </p>

        <NUpload
          v-model:file-list="fileList"
          :max="10"
          multiple
          :default-upload="false"
        >
          <NButton>选择文件</NButton>
        </NUpload>

        <NSpace justify="end" style="margin-top: 16px;">
          <NButton type="primary" :loading="uploading" :disabled="!fileList.length" @click="handleUpload">
            提交材料
          </NButton>
        </NSpace>

        <div v-if="uploadedFiles.length" style="margin-top: 24px;">
          <h4>已上传文件</h4>
          <NList bordered size="small">
            <NListItem v-for="(f, idx) in uploadedFiles" :key="idx">
              <NSpace align="center">
                <span>{{ f.name }}</span>
                <NTag size="small" type="success">{{ f.status }}</NTag>
              </NSpace>
            </NListItem>
          </NList>
        </div>
      </template>
    </NCard>
  </div>
</template>
