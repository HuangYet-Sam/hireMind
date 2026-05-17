<script setup lang="ts">
import { useRoute } from 'vue-router'
import { NCard, NEmpty } from 'naive-ui'

const route = useRoute()
const token = route.params.token as string
</script>

<template>
  <div style="max-width: 600px; margin: 80px auto; padding: 24px;">
    <NCard title="Offer 回应">
      <NEmpty description="此功能将在后续版本开放 (Phase 2)">
        <template #extra>
          <p style="color: #999; font-size: 13px;">
            Token: {{ token }}
          </p>
        </template>
      </NEmpty>
    </NCard>
  </div>
</template>
