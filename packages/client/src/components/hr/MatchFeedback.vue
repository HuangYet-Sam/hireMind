<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NSpace, NRadioGroup, NRadioButton, NPopover, useMessage } from 'naive-ui'
import { hrPost } from '@/api/hr/client'

const props = defineProps<{
  matchId: string
}>()

const emit = defineEmits<{
  submitted: [feedback: { rating: 'positive' | 'negative'; reason?: string }]
}>()

const message = useMessage()
const rating = ref<'positive' | 'negative' | null>(null)
const reason = ref('')
const showReasonPicker = ref(false)
const submitting = ref(false)

const negativeReasons = [
  'Skills mismatch',
  'Experience gap',
  'Education mismatch',
  'Overqualified',
  'Underqualified',
  'Other',
]

const positiveReasons = [
  'Strong skill match',
  'Relevant experience',
  'Good culture fit',
  'Education aligned',
  'Other',
]

async function submitFeedback(selectedRating: 'positive' | 'negative') {
  submitting.value = true
  try {
    await hrPost(`/matching/${props.matchId}/feedback`, {
      rating: selectedRating,
      reason: reason.value || undefined,
    })
    rating.value = selectedRating
    showReasonPicker.value = false
    emit('submitted', { rating: selectedRating, reason: reason.value || undefined })
    message.success('Feedback submitted')
  } catch {
    message.error('Failed to submit feedback')
  } finally {
    submitting.value = false
  }
}

function handleThumbsUp() {
  if (rating.value === 'positive') return
  reason.value = ''
  showReasonPicker.value = true
}

function handleThumbsDown() {
  if (rating.value === 'negative') return
  reason.value = ''
  showReasonPicker.value = true
}

function confirmFeedback(selectedRating: 'positive' | 'negative') {
  submitFeedback(selectedRating)
}
</script>

<template>
  <div class="match-feedback">
    <NSpace align="center" :size="8">
      <span class="feedback-label">Match Feedback</span>
      <NButton
        size="tiny"
        :type="rating === 'positive' ? 'success' : 'default'"
        :disabled="!!rating"
        @click="handleThumbsUp"
      >
        👍
      </NButton>
      <NButton
        size="tiny"
        :type="rating === 'negative' ? 'error' : 'default'"
        :disabled="!!rating"
        @click="handleThumbsDown"
      >
        👎
      </NButton>
    </NSpace>

    <NPopover
      v-if="showReasonPicker && !rating"
      :show="showReasonPicker && !rating"
      placement="bottom"
      trigger="manual"
      :show-arrow="true"
    >
      <template #trigger>
        <span />
      </template>
      <div class="reason-picker">
        <p class="reason-title">Select a reason (optional)</p>
        <NRadioGroup v-model:value="reason" size="small">
          <NSpace vertical :size="4">
            <NRadioButton
              v-for="r in (showReasonPicker ? negativeReasons : positiveReasons)"
              :key="r"
              :value="r"
            >
              {{ r }}
            </NRadioButton>
          </NSpace>
        </NRadioGroup>
        <NSpace style="margin-top: 8px;">
          <NButton
            size="tiny"
            type="primary"
            :loading="submitting"
            @click="confirmFeedback(showReasonPicker ? 'negative' : 'positive')"
          >
            Submit
          </NButton>
          <NButton size="tiny" @click="showReasonPicker = false">Cancel</NButton>
        </NSpace>
      </div>
    </NPopover>

    <div v-if="rating" class="feedback-result">
      <span :class="['feedback-badge', rating]">
        {{ rating === 'positive' ? '👍 Approved' : '👎 Rejected' }}
      </span>
      <span v-if="reason" class="feedback-reason">{{ reason }}</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.match-feedback {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;

  .feedback-label {
    font-size: 13px;
    color: $text-muted;
  }

  .feedback-result {
    display: flex;
    align-items: center;
    gap: 8px;

    .feedback-badge {
      font-size: 12px;
      padding: 2px 8px;
      border-radius: $radius-sm;

      &.positive {
        background: rgba(46, 125, 50, 0.1);
        color: var(--success);
      }

      &.negative {
        background: rgba(198, 40, 40, 0.1);
        color: var(--error);
      }
    }

    .feedback-reason {
      font-size: 12px;
      color: $text-muted;
    }
  }
}

.reason-picker {
  min-width: 200px;

  .reason-title {
    font-size: 13px;
    font-weight: 600;
    margin: 0 0 8px;
    color: $text-primary;
  }
}
</style>
