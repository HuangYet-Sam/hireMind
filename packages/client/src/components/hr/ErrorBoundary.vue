<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { NResult, NButton } from 'naive-ui'

const hasError = ref(false)
const errorMsg = ref('')

onErrorCaptured((err) => {
  hasError.value = true
  errorMsg.value = err instanceof Error ? err.message : String(err)
  return false
})

function retry() {
  hasError.value = false
  errorMsg.value = ''
}
</script>

<template>
  <slot v-if="!hasError" />
  <NResult v-else status="error" title="页面加载出错" :description="errorMsg" style="padding: 48px 24px;">
    <template #footer>
      <NButton type="primary" @click="retry">重试</NButton>
    </template>
  </NResult>
</template>
