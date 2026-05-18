<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NUpload, NButton, NSpace, NProgress, NIcon, NText, useMessage } from 'naive-ui'
import type { UploadFileInfo } from 'naive-ui'
import { uploadResume } from '@/api/hr/resumes'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'uploaded'): void
}>()

const message = useMessage()

const fileList = ref<UploadFileInfo[]>([])
const uploading = ref(false)
const uploadProgress = ref<Record<string, number>>({})
const uploadResults = ref<Record<string, 'success' | 'error'>>({})

const ACCEPTED_TYPES = '.pdf,.doc,.docx,.png,.jpg,.jpeg,.txt'
const MAX_FILE_SIZE = 10 * 1024 * 1024

function resetState() {
  fileList.value = []
  uploadProgress.value = {}
  uploadResults.value = {}
}

watch(() => props.show, (val) => {
  if (val) resetState()
})

function handleFileChange(options: { fileList: UploadFileInfo[] }) {
  fileList.value = options.fileList.filter((f) => {
    if (f.file && f.file.size > MAX_FILE_SIZE) {
      message.warning(`${f.file.name} 超过 10MB 限制`)
      return false
    }
    return true
  })
}

function removeFile(options: { file: UploadFileInfo; fileList: UploadFileInfo[] }) {
  fileList.value = options.fileList
}

async function handleUpload() {
  const files = fileList.value
    .filter((f) => f.file && uploadResults.value[f.id] !== 'success')
    .map((f) => f.file as File)

  if (files.length === 0) {
    message.warning('请选择文件')
    return
  }

  uploading.value = true
  let successCount = 0
  let failCount = 0

  for (const fileInfo of fileList.value) {
    const file = fileInfo.file
    if (!file || uploadResults.value[fileInfo.id] === 'success') continue

    uploadProgress.value[fileInfo.id] = 0

    try {
      uploadProgress.value[fileInfo.id] = 30
      await uploadResume(file)
      uploadProgress.value[fileInfo.id] = 100
      uploadResults.value[fileInfo.id] = 'success'
      successCount++
    } catch {
      uploadProgress.value[fileInfo.id] = 0
      uploadResults.value[fileInfo.id] = 'error'
      failCount++
    }
  }

  uploading.value = false

  if (successCount > 0) {
    message.success(`${successCount} 份简历上传成功`)
    emit('uploaded')
  }
  if (failCount > 0) {
    message.error(`${failCount} 份简历上传失败`)
  }
  if (successCount > 0 && failCount === 0) {
    emit('close')
  }
}

const overallProgress = ref(0)
</script>

<template>
  <NModal :show="props.show" preset="card" title="上传简历" style="max-width: 560px;" @update:show="(val: boolean) => { if (!val) emit('close') }">
    <NUpload
      multiple
      :max="10"
      :accept="ACCEPTED_TYPES"
      :default-upload="false"
      directory-dnd
      @change="handleFileChange"
      @remove="removeFile"
    >
      <NUpload.Dragger>
        <div class="upload-dragger">
          <div class="upload-icon-area">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <NText class="upload-text">点击或拖拽文件到此区域上传</NText>
          <NText depth="3" class="upload-hint">
            支持 PDF、Word(.doc/.docx)、图片(png/jpg)、TXT，单文件不超过 10MB
          </NText>
        </div>
      </NUpload.Dragger>
    </NUpload>

    <div v-if="fileList.length > 0" class="file-list">
      <div v-for="file in fileList" :key="file.id" class="file-item">
        <div class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">
            {{ file.file ? (file.file.size / 1024 / 1024).toFixed(2) + ' MB' : '' }}
          </span>
        </div>
        <NProgress
          v-if="uploadProgress[file.id] !== undefined && uploadProgress[file.id] > 0"
          type="line"
          :percentage="uploadProgress[file.id]"
          :status="uploadResults[file.id] === 'error' ? 'error' : 'success'"
          :show-indicator="false"
          style="width: 100%;"
        />
        <span v-if="uploadResults[file.id] === 'success'" class="status-ok">已上传</span>
        <span v-if="uploadResults[file.id] === 'error'" class="status-fail">失败</span>
      </div>
    </div>

    <template #action>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton
          type="primary"
          :loading="uploading"
          :disabled="fileList.length === 0"
          @click="handleUpload"
        >
          上传 ({{ fileList.filter(f => uploadResults[f.id] !== 'success').length }})
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.upload-dragger {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  gap: 8px;
}

.upload-icon-area {
  color: $text-secondary;
  margin-bottom: 4px;
}

.upload-text {
  font-size: 14px;
}

.upload-hint {
  font-size: 12px;
}

.file-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  padding: 8px 12px;
  border: 1px solid var(--border-light, #e0e0e0);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-name {
  font-size: 13px;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}

.file-size {
  font-size: 12px;
  color: $text-secondary;
}

.status-ok {
  font-size: 12px;
  color: #18a058;
}

.status-fail {
  font-size: 12px;
  color: #d03050;
}
</style>
