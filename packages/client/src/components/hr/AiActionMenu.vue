<script setup lang="ts">
/**
 * AiActionMenu — M10 AI操作菜单组件
 *
 * 触发方式：右键菜单(contextmenu) / Ctrl+K 快捷键
 * 上下文感知：根据当前页面和选中实体动态显示操作
 * NDropdown 菜单 + 快捷搜索框
 * Emits: action-select
 */
import { ref, computed, onMounted, onUnmounted, watch, h } from 'vue'
import { useRoute } from 'vue-router'
import {
  NDropdown, NInput, NIcon, NEmpty, NScrollbar,
} from 'naive-ui'
import type { DropdownOption } from 'naive-ui'

// ── Props & Emits ───────────────────────────────────────────

interface Props {
  /** 当前页面上下文标识 */
  context?: 'candidate' | 'position' | 'interview' | 'offer' | 'resume' | 'dashboard' | 'matching'
  /** 选中实体的ID（可选） */
  entityId?: string
  /** 选中实体的名称（可选） */
  entityName?: string
}

const props = withDefaults(defineProps<Props>(), {
  context: 'dashboard',
})

const emit = defineEmits<{
  'action-select': [action: string, payload?: Record<string, unknown>]
}>()

// ── Types ───────────────────────────────────────────────────

interface AiAction {
  key: string
  label: string
  icon: string
  context: string[]
  description?: string
}

// ── Actions Registry ────────────────────────────────────────

const ALL_ACTIONS: AiAction[] = [
  // 候选人相关
  { key: 'candidate:profile', label: '生成候选人画像', icon: '👤', context: ['candidate'], description: '基于历史数据生成360°画像' },
  { key: 'candidate:match', label: '匹配岗位', icon: '🎯', context: ['candidate'], description: '为候选人推荐匹配岗位' },
  { key: 'candidate:activate', label: '激活候选人', icon: '💡', context: ['candidate'], description: '发送激活消息给沉默候选人' },
  { key: 'candidate:summary', label: '简历摘要', icon: '📝', context: ['candidate', 'resume'], description: 'AI生成简历要点摘要' },
  { key: 'candidate:compare', label: '对比分析', icon: '⚖️', context: ['candidate'], description: '与岗位要求对比分析' },

  // 岗位相关
  { key: 'position:generate-jd', label: '生成JD', icon: '📋', context: ['position'], description: 'AI生成岗位描述' },
  { key: 'position:recommend', label: '推荐候选人', icon: '👥', context: ['position'], description: '推荐匹配的候选人' },
  { key: 'position:analyze', label: '岗位分析', icon: '📊', context: ['position'], description: '分析岗位市场竞争力和招聘难度' },
  { key: 'position:benchmark', label: '薪资对标', icon: '💰', context: ['position'], description: '查看市场薪资对标数据' },

  // 面试相关
  { key: 'interview:checklist', label: '生成考察清单', icon: '✅', context: ['interview'], description: '基于岗位要求生成面试考察要点' },
  { key: 'interview:questions', label: '生成面试题目', icon: '❓', context: ['interview'], description: '生成针对性面试问题' },
  { key: 'interview:feedback', label: '生成反馈模板', icon: '💬', context: ['interview'], description: '生成面试评价反馈模板' },
  { key: 'interview:schedule', label: '智能排期', icon: '📅', context: ['interview'], description: '推荐面试时间段' },

  // Offer相关
  { key: 'offer:salary-advice', label: '薪资建议', icon: '💵', context: ['offer'], description: 'AI给出薪资范围建议' },
  { key: 'offer:negotiation', label: '谈判策略', icon: '🤝', context: ['offer'], description: '生成Offer谈判策略' },
  { key: 'offer:risks', label: '风险分析', icon: '⚠️', context: ['offer'], description: '分析Offer接受/拒绝风险' },

  // 通用
  { key: 'general:memory', label: '查看相关记忆', icon: '🧠', context: ['candidate', 'position', 'interview', 'offer', 'resume'], description: '查看AI对该实体的记忆' },
  { key: 'general:insights', label: 'AI洞察', icon: '💡', context: ['candidate', 'position', 'interview', 'offer', 'dashboard'], description: '查看AI洞察分析' },
  { key: 'general:history', label: '操作历史', icon: '📜', context: ['candidate', 'position', 'interview', 'offer'], description: '查看历史操作记录' },
]

// ── State ───────────────────────────────────────────────────

const route = useRoute()
const showDropdown = ref(false)
const dropdownX = ref(0)
const dropdownY = ref(0)
const searchQuery = ref('')

// ── Computed ────────────────────────────────────────────────

const currentContext = computed(() => {
  if (props.context !== 'dashboard') return props.context
  // Auto-detect from route
  const name = route.name as string
  if (name?.includes('candidate')) return 'candidate'
  if (name?.includes('position')) return 'position'
  if (name?.includes('interview')) return 'interview'
  if (name?.includes('offer')) return 'offer'
  if (name?.includes('resume')) return 'resume'
  if (name?.includes('matching')) return 'matching'
  return 'dashboard'
})

const contextActions = computed(() => {
  const ctx = currentContext.value
  if (ctx === 'dashboard' || ctx === 'matching') {
    // Show all actions for dashboard
    return ALL_ACTIONS
  }
  return ALL_ACTIONS.filter(a => a.context.includes(ctx))
})

const filteredActions = computed(() => {
  if (!searchQuery.value) return contextActions.value
  const q = searchQuery.value.toLowerCase()
  return contextActions.value.filter(
    a => a.label.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q),
  )
})

const dropdownOptions = computed<DropdownOption[]>(() => {
  const ctx = currentContext.value
  const actions = filteredActions.value

  if (ctx === 'dashboard' || ctx === 'matching') {
    // Group by context
    const groups: Record<string, AiAction[]> = {}
    actions.forEach(a => {
      const group = a.context[0]
      if (!groups[group]) groups[group] = []
      groups[group].push(a)
    })

    const options: DropdownOption[] = []
    const groupLabels: Record<string, string> = {
      candidate: '👤 候选人',
      position: '📋 岗位',
      interview: '🎯 面试',
      offer: '📝 Offer',
      resume: '📄 简历',
    }

    Object.entries(groups).forEach(([group, items]) => {
      options.push({
        key: `group-${group}`,
        type: 'group',
        label: groupLabels[group] || group,
        children: items.map(item => ({
          key: item.key,
          label: item.label,
          icon: () => h('span', { style: 'font-size: 14px;' }, item.icon),
        })),
      })
    })

    return options
  }

  return actions.map(a => ({
    key: a.key,
    label: a.label,
    icon: () => h('span', { style: 'font-size: 14px;' }, a.icon),
  }))
})

// ── Keyboard Shortcut ───────────────────────────────────────

function handleKeydown(e: KeyboardEvent) {
  // Ctrl+K or Cmd+K
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    e.stopPropagation()
    openAtCenter()
  }
  // Escape to close
  if (e.key === 'Escape' && showDropdown.value) {
    showDropdown.value = false
    searchQuery.value = ''
  }
}

// ── Context Menu ────────────────────────────────────────────

function handleContextMenu(e: MouseEvent) {
  e.preventDefault()
  dropdownX.value = e.clientX
  dropdownY.value = e.clientY
  showDropdown.value = true
  searchQuery.value = ''
}

function openAtCenter() {
  dropdownX.value = window.innerWidth / 2 - 150
  dropdownY.value = window.innerHeight / 3
  showDropdown.value = true
  searchQuery.value = ''
}

function handleSelect(key: string) {
  const action = ALL_ACTIONS.find(a => a.key === key)
  if (!action) return

  const payload: Record<string, unknown> = {}
  if (props.entityId) payload.entityId = props.entityId
  if (props.entityName) payload.entityName = props.entityName

  emit('action-select', key, payload)
  showDropdown.value = false
  searchQuery.value = ''
}

function handleClickOutside() {
  showDropdown.value = false
  searchQuery.value = ''
}

// ── Lifecycle ───────────────────────────────────────────────

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// ── Expose for parent ───────────────────────────────────────

defineExpose({
  openAtCenter,
  handleContextMenu,
})
</script>

<template>
  <div class="ai-action-menu" @contextmenu="handleContextMenu">
    <!-- Slot for the content that should trigger context menu -->
    <slot />

    <!-- Keyboard shortcut hint -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showDropdown"
          class="ai-action-overlay"
          @click="handleClickOutside"
        >
          <div
            class="ai-action-dropdown"
            :style="{ left: `${dropdownX}px`, top: `${dropdownY}px` }"
            @click.stop
          >
            <!-- Search -->
            <div class="action-search">
              <NInput
                v-model:value="searchQuery"
                placeholder="搜索 AI 操作... (Esc 关闭)"
                size="small"
                autofocus
                clearable
              >
                <template #prefix>
                  <span style="font-size: 14px;">🔍</span>
                </template>
              </NInput>
            </div>

            <!-- Results -->
            <NScrollable style="max-height: 320px;">
              <div v-if="filteredActions.length" class="action-list">
                <div
                  v-for="action in filteredActions"
                  :key="action.key"
                  class="action-item"
                  @click="handleSelect(action.key)"
                >
                  <span class="action-icon">{{ action.icon }}</span>
                  <div class="action-info">
                    <div class="action-label">{{ action.label }}</div>
                    <div v-if="action.description" class="action-desc">{{ action.description }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="action-empty">
                <NEmpty description="无匹配操作" size="small" />
              </div>
            </NScrollable>

            <!-- Footer -->
            <div class="action-footer">
              <span>Ctrl+K 打开</span>
              <span>右键触发</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.ai-action-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.2);
}

.ai-action-dropdown {
  position: absolute;
  width: 380px;
  max-width: 90vw;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  animation: slideDown 0.15s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.action-search {
  padding: 12px;
  border-bottom: 1px solid $border-light;
}

.action-list {
  padding: 4px 0;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: rgba(var(--accent-primary-rgb), 0.06);
  }
}

.action-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.action-info {
  flex: 1;
  min-width: 0;
}

.action-label {
  font-size: 14px;
  font-weight: 500;
  color: $text-primary;
}

.action-desc {
  font-size: 12px;
  color: $text-muted;
  margin-top: 2px;
}

.action-empty {
  padding: 20px;
}

.action-footer {
  display: flex;
  justify-content: space-between;
  padding: 8px 14px;
  border-top: 1px solid $border-light;
  font-size: 11px;
  color: $text-muted;
}

// Transition
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
