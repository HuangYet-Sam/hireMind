<script setup lang="ts">
import { ref, computed } from 'vue'
import { NModal, NCard, NTabs, NTabPane, NTag, NSpin, NEmpty } from 'naive-ui'
import type { Resume } from '@/api/hr/resumes'

const props = defineProps<{
  show: boolean
  resume: Resume | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const activeTab = ref('parsed')
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="简历查看器"
    style="width: 700px; max-height: 80vh;"
    @update:show="emit('update:show', $event)"
  >
    <template v-if="resume">
      <div class="resume-header">
        <h3>{{ resume.filename }}</h3>
        <NTag v-if="resume.candidate_name" size="small">{{ resume.candidate_name }}</NTag>
      </div>

      <NTabs v-model:value="activeTab" type="line">
        <NTabPane name="parsed" tab="解析内容">
          <div v-if="resume.parsed_content" class="parsed-content" v-html="resume.parsed_content" />
          <NEmpty v-else description="解析内容为空" />
        </NTabPane>

        <NTabPane name="skills" tab="技能标签">
          <div class="tag-list">
            <NTag v-for="tag in resume.parsed_skills" :key="tag" size="small" style="margin: 4px;">{{ tag }}</NTag>
          </div>
        </NTabPane>

        <NTabPane name="ai" tab="AI分析">
          <div v-if="resume.ai_summary" class="ai-summary">{{ resume.ai_summary }}</div>
          <div class="tag-list" style="margin-top: 8px;">
            <NTag v-for="tag in resume.ai_tags" :key="tag" size="small" type="info" style="margin: 4px;">{{ tag }}</NTag>
          </div>
          <NEmpty v-if="!resume.ai_summary && !resume.ai_tags.length" description="暂无AI分析" />
        </NTabPane>
      </NTabs>
    </template>
    <NEmpty v-else description="未选择简历" />
  </NModal>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.resume-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 16px;
    color: $text-primary;
  }
}

.parsed-content {
  font-size: 14px;
  line-height: 1.6;
  color: $text-secondary;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
  background: $bg-secondary;
  border-radius: 6px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.ai-summary {
  font-size: 14px;
  line-height: 1.6;
  color: $text-secondary;
  padding: 12px;
  background: rgba(var(--accent-info-rgb), 0.06);
  border-radius: 6px;
  border-left: 3px solid var(--accent-info);
}
</style>
