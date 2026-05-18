<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NSpace, NRadioGroup, NRadioButton, useMessage } from 'naive-ui'
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
const pendingRating = ref<'positive' | 'negative' | null>(null)
const submitting = ref(false)

const currentReasons = computed(() => {
  if (pendingRating.value === 'positive') {
    return ['Strong skill match', 'Relevant experience', 'Good culture fit', 'Education aligned', 'Other']
  }
  return ['Skills mismatch', 'Experience gap', 'Education mismatch', 'Overqualified', 'Underqualified', 'Other']
})

async function submitFeedback(selectedRating: 'positive' | 'negative') {
  submitting.value = true
  try {
    await hrPost(`/matching/${props.matchId}/feedback`, {
      rating: selectedRating,
      reason: reason.value || undefined,
    })
    rating.value = selectedRating
    pendingRating.value = null
    emit('submitted', { rating: selectedRating, reason: reason.value || undefined })
    message.success('Feedback submitted')
  } catch {
    message.error('Failed to submit feedback')
  } finally {
    submitting.value = false
  }
}

function handleThumbsUp() {
  if (rating.value) return
  reason.value = ''
  pendingRating.value = 'positive'
}

function handleThumbsDown() {
  if (rating.value) return
  reason.value = ''
  pendingRating.value = 'negative'
}

function confirmFeedback() {
  if (pendingRating.value) {
    submitFeedback(pendingRating.value)
  }
}

function cancelFeedback() {
  pendingRating.value = null
  reason.value = ''
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

    <div v-if="pendingRating && !rating" class="reason-picker">
      <p class="reason-title">Select a reason (optional)</p>
      <NRadioGroup v-model:value="reason" size="small">
        <NSpace vertical :size="4">
          <NRadioButton
            v-for="r in currentReasons"
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
          @click="confirmFeedback"
        >
          Submit
        </NButton>
        <NButton size="tiny" @click="cancelFeedback">Cancel</NButton>
      </NSpace>
    </div>

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
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;

  .feedback-label {
    font-size: 13px;
    color: $text-muted;
    line-height: 26px;
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
  padding: 8px 12px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  .reason-title {
    font-size: 13px;
    font-weight: 600;
    margin: 0 0 8px;
    color: $text-primary;
  }
}
</style>
