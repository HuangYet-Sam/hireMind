<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { SourceEffectiveness } from '@/api/hr/analytics'

use([BarChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  data: SourceEffectiveness[]
}>()

const option = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
  },
  legend: {
    data: ['总数', '已录用', '转化率'],
    bottom: 0,
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: 40,
    top: 20,
    containLabel: true,
  },
  xAxis: {
    type: 'value',
  },
  yAxis: {
    type: 'category',
    data: props.data.map(d => d.source),
  },
  series: [
    {
      name: '总数',
      type: 'bar',
      stack: 'total',
      data: props.data.map(d => d.total),
    },
    {
      name: '已录用',
      type: 'bar',
      stack: 'total',
      data: props.data.map(d => d.hired),
    },
    {
      name: '转化率',
      type: 'bar',
      data: props.data.map(d => Math.round(d.conversion_rate * 100)),
      barWidth: 12,
      itemStyle: { borderRadius: [0, 4, 4, 0] },
    },
  ],
}))
</script>

<template>
  <VChart :option="option" autoresize style="height: 320px;" />
</template>
