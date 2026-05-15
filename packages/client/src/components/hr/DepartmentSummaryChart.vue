<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { DepartmentSummary } from '@/api/hr/analytics'

use([PieChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  data: DepartmentSummary[]
  metric?: 'positions' | 'candidates'
}>()

const metric = computed(() => props.metric ?? 'positions')

const option = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)',
  },
  legend: {
    orient: 'vertical',
    right: 10,
    top: 'center',
    type: 'scroll',
  },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['40%', '50%'],
    avoidLabelOverlap: true,
    itemStyle: {
      borderRadius: 6,
      borderColor: '#fff',
      borderWidth: 2,
    },
    label: {
      show: true,
      formatter: '{b}\n{c}',
      fontSize: 12,
    },
    data: props.data.map(d => ({
      name: d.department,
      value: metric.value === 'positions' ? d.positions : d.candidates,
    })),
  }],
}))
</script>

<template>
  <VChart :option="option" autoresize style="height: 320px;" />
</template>
