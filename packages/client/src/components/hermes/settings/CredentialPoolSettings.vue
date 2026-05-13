<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NDataTable, NTag, NEmpty } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { fetchCredentialPool, type CredentialEntry } from '@/api/hermes/credentials'

const { t } = useI18n()
const pool = ref<Record<string, CredentialEntry[]>>({})
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    pool.value = await fetchCredentialPool()
  } catch {
    pool.value = {}
  } finally {
    loading.value = false
  }
})

const providers = computed(() => Object.entries(pool.value))

function statusType(status: string | null): 'success' | 'error' | 'warning' | 'default' {
  if (!status) return 'default'
  if (status === 'ok' || status === 'healthy') return 'success'
  if (status.startsWith('error') || status === 'failed') return 'error'
  return 'warning'
}

const columns = computed(() => [
  { title: t('settings.credentials.label'), key: 'label', width: 140 },
  { title: t('settings.credentials.authType'), key: 'auth_type', width: 100 },
  {
    title: t('settings.credentials.status'),
    key: 'last_status',
    width: 100,
    render(row: CredentialEntry) {
      return h(NTag, { size: 'small', type: statusType(row.last_status), round: true }, () => row.last_status || '—')
    },
  },
  {
    title: t('settings.credentials.key'),
    key: 'has_key',
    width: 70,
    render(row: CredentialEntry) {
      return h(NTag, { size: 'small', type: row.has_key ? 'success' : 'error', round: true }, () => row.has_key ? '✓' : '✗')
    },
  },
  { title: t('settings.credentials.error'), key: 'last_error_message', ellipsis: { tooltip: true } },
  { title: t('settings.credentials.requests'), key: 'request_count', width: 90 },
])

import { h } from 'vue'
</script>

<template>
  <section class="settings-section">
    <div v-if="providers.length === 0 && !loading" class="empty-section">
      <NEmpty :description="t('settings.credentials.noCredentials')" />
    </div>

    <div v-else class="credential-providers">
      <div v-for="[provider, entries] in providers" :key="provider" class="provider-section">
        <div class="provider-header">{{ provider }}</div>
        <NDataTable
          :columns="columns"
          :data="entries"
          :bordered="false"
          size="small"
          :row-key="(row: CredentialEntry) => row.id"
        />
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.settings-section {
  margin-top: 16px;
}

.empty-section {
  padding: 20px 0;
}

.credential-providers {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.provider-header {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8px;
  text-transform: capitalize;
}
</style>
